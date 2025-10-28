from google import genai
from google.genai import types
import os
import re
import requests
import google.auth
from flask import Flask, render_template, request, jsonify
from google.cloud import modelarmor_v1
from dotenv import load_dotenv
from google.api_core import exceptions
import base64
from werkzeug.utils import secure_filename
import mimetypes
import json
import traceback
import ast
import asyncio
import concurrent.futures
import hashlib
import time
from functools import lru_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()

app = Flask(__name__)

# --- Jinja2 Configuration for XSS Protection --
app.jinja_env.autoescape = True

project = os.getenv('GCP_PROJECT_ID')

# --- Authentication Token Cache ---
auth_token_cache = {}
TOKEN_TTL = 3300  # 55 minutes (tokens typically last 60 minutes)

def get_cached_auth_token():
    """Get cached authentication token or refresh if expired"""
    current_time = time.time()
    
    if 'token_data' in auth_token_cache:
        token, timestamp = auth_token_cache['token_data']
        if current_time - timestamp < TOKEN_TTL:
            return token
    
    # Token expired or doesn't exist, refresh it
    credentials, _ = google.auth.default()
    auth_req = google.auth.transport.requests.Request()
    credentials.refresh(auth_req)
    
    # Cache the new token
    auth_token_cache['token_data'] = (credentials.token, current_time)
    print(f"INFO: Authentication token refreshed and cached")
    
    return credentials.token

# Add allowed file extensions
ALLOWED_EXTENSIONS = {
    'pdf', 'docx', 'docm', 'dotx', 'dotm',
    'pptx', 'pptm', 'potx', 'pot',
    'xlsx', 'xlsm', 'xltx', 'xltm'
}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_byte_data_type(mime_type):
    """Convert MIME type to Model Armor byteDataType"""
    mime_to_type = {
        'application/pdf': 'PDF',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
        'application/msword': 'DOC',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'PPTX',
        'application/vnd.ms-powerpoint': 'PPT',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
        'application/vnd.ms-excel': 'XLS'
    }
    return mime_to_type.get(mime_type, 'PDF')

# --- Optimized HTTP Client ---
class OptimizedHTTPClient:
    def __init__(self):
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Configure adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

# Global HTTP client
http_client = OptimizedHTTPClient()

# --- Caching Layer ---
model_armor_cache = {}
template_cache = {}
file_cache = {}  # Cache for file base64 data
CACHE_TTL = 300  # 5 minutes

def get_cache_key(data, template_name, location):
    """Generate cache key for Model Armor results"""
    if isinstance(data, dict):  # File data
        content_hash = hashlib.md5(data['base64_data'][:1000].encode()).hexdigest()
        return f"file_{content_hash}_{template_name}_{location}"
    else:  # Text data
        content_hash = hashlib.md5(data.encode()).hexdigest()
        return f"text_{content_hash}_{template_name}_{location}"

def get_cached_result(cache_key):
    """Get cached result if still valid"""
    if cache_key in model_armor_cache:
        result, timestamp = model_armor_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            print(f"Cache hit for {cache_key[:20]}...")
            return result
        else:
            del model_armor_cache[cache_key]
    return None

def cache_result(cache_key, result):
    """Cache the result"""
    model_armor_cache[cache_key] = (result, time.time())
    # Clean old cache entries periodically
    if len(model_armor_cache) > 100:
        current_time = time.time()
        expired_keys = [k for k, (_, timestamp) in model_armor_cache.items() 
                       if current_time - timestamp > CACHE_TTL]
        for k in expired_keys:
            del model_armor_cache[k]

# --- Client Caching ---
model_armor_clients = {}
genai_clients = {}

def get_model_armor_client(location, endpoint):
    if location not in model_armor_clients:
        model_armor_clients[location] = modelarmor_v1.ModelArmorClient(
            transport="rest", client_options={"api_endpoint": endpoint}
        )
    return model_armor_clients[location]

def get_genai_client(location):
    if location not in genai_clients:
        genai_clients[location] = genai.Client(vertexai=True, project=project, location=location)
    return genai_clients[location]

def pre_initialize_clients():
    """Pre-initializes all necessary API clients to prevent cold start issues."""
    print("INFO: Pre-initializing all API clients...")
    
    # Pre-warm Model Armor clients
    for endpoint_info in model_armor_endpoints:
        try:
            get_model_armor_client(endpoint_info['location'], endpoint_info['endpoint'])
            print(f"  - Successfully initialized Model Armor client for {endpoint_info['location']}")
        except Exception as e:
            print(f"  - WARNING: Failed to initialize Model Armor client for {endpoint_info['location']}: {e}")
            
    # Pre-warm Generative AI clients
    unique_locations = {model.get('location', 'us-central1') for model in foundation_models}
    for location in unique_locations:
        try:
            get_genai_client(location)
            print(f"  - Successfully initialized GenAI client for {location}")
        except Exception as e:
            print(f"  - WARNING: Failed to initialize GenAI client for {location}: {e}")
    
    print("INFO: All API clients pre-initialization complete.")


model_armor_endpoints = [
    {"location": "us-central1", "endpoint": "modelarmor.us-central1.rep.googleapis.com", "display_name": "us-central1"},
    {"location": "us-east1", "endpoint": "modelarmor.us-east1.rep.googleapis.com", "display_name": "us-east1"},
    {"location": "europe-west4", "endpoint": "modelarmor.europe-west4.rep.googleapis.com", "display_name": "europe-west4"},
    {"location": "asia-southeast1", "endpoint": "modelarmor.asia-southeast1.rep.googleapis.com", "display_name": "asia-southeast1"},
]

generation_config = types.GenerateContentConfig(
    max_output_tokens=2048, temperature=0.2, top_p=0.95, response_modalities=["TEXT"],
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    ]
)

foundation_models = [
    {"name": "gemini-2.0-flash-001", "provider": "Google", "location": "global", "display_name": "gemini-2.0-flash-001"},
    {"name": "gemini-2.5-flash", "provider": "Google", "location": "global", "display_name": "gemini-2.5-flash"},
    {"name": "gemini-2.5-pro", "provider": "Google", "location": "global", "display_name": "gemini-2.5-pro"},
    {"name": "gemini-2.5-flash-lite-preview-06-17", "provider": "Google", "location": "global", "display_name": "gemini-2.5-flash-lite-preview-06-17"},
    {"name": "claude-sonnet-4", "provider": "Anthropic", "location": "us-east5", "display_name": "claude-sonnet-4"},
]

# --- Pre-initialize all clients on startup ---
pre_initialize_clients()

def _generate_with_sdk(prompt, model_info, system_instruction, file_data=None):
    """Original SDK approach - kept for fallback"""
    client_to_use = get_genai_client(model_info.get('location', 'us-central1'))
    parts = [{'text': prompt}]
    if file_data and model_info.get('provider') == 'Google':
        parts.append({
            'inline_data': {
                'mime_type': file_data['mime_type'],
                'data': file_data['base64_data']
            }
        })
    response = client_to_use.models.generate_content(
        model=model_info['name'],
        contents=[{'role': 'user', 'parts': parts}],
        config=generation_config
    )
    return response.text

def _generate_with_raw_predict(prompt, model_info, system_instruction, file_data=None):
    """Claude generation via Vertex AI rawPredict"""
    access_token = get_cached_auth_token()
    location = model_info['location']
    url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/locations/{location}/publishers/anthropic/models/{model_info['name']}:rawPredict"
    if file_data:
        prompt = f"{prompt}\n\nNote: A file ({file_data['filename']}) was uploaded but cannot be processed by this model."
    payload = {
        "anthropic_version": "vertex-2023-10-16",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json; charset=utf-8"}
    try:
        response = http_client.session.post(url, headers=headers, json=payload, timeout=(5, 30))
        response.raise_for_status()
        response_json = response.json()
        if 'content' in response_json and response_json['content']:
            return response_json['content'][0]['text']
        return f"Error: Could not parse Claude response. Full response: {response.text}"
    except requests.exceptions.RequestException as e:
        return f"Error: {e.response.status_code} - {e.response.text}" if hasattr(e, 'response') else f"Error making request: {e}"

def generate_model_response(prompt, model_info, system_instruction, file_data=None):
    """Original generation function using SDK"""
    provider = model_info.get('provider', 'Google')
    if provider == 'Anthropic':
        return _generate_with_raw_predict(prompt, model_info, system_instruction, file_data)
    else:
        return _generate_with_sdk(prompt, model_info, system_instruction, file_data)

def fetch_model_armor_templates(location, endpoint):
    # Check cache first
    cache_key = f"templates_{location}"
    if cache_key in template_cache:
        cached_data, timestamp = template_cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data
    
    local_prompt_templates, local_response_templates = [], []
    try:
        client = get_model_armor_client(location, endpoint)
        request = modelarmor_v1.ListTemplatesRequest(parent=f"projects/{project}/locations/{location}")
        page_result = client.list_templates(request=request)
        for template in page_result:
            template_info = {'name': template.name.split('/')[-1], 'display_name': template.name.split('/')[-1], 'location': location, 'last_updated': template.update_time.strftime('%Y-%m-%d %H:%M:%S UTC')}
            local_prompt_templates.append(template_info)
            local_response_templates.append(template_info)
        
        # Cache the result
        result = (local_prompt_templates, local_response_templates)
        template_cache[cache_key] = (result, time.time())
        return result
    except Exception as e:
        print(f"Error fetching templates from {location}: {e}")
        return [], []

def process_template_results(output_str):
    matches = re.finditer(r'key: "([^"]+)"[^}]*?match_state: MATCH_FOUND', output_str, re.DOTALL)
    return [match.group(1) for match in matches]

def process_rest_api_results(response_data):
    """Parses the JSON response from the Model Armor REST API to find all filters with a MATCH_FOUND state."""
    filter_results = []
    try:
        results = response_data.get('sanitizationResult', {}).get('filterResults', {})
        for filter_name, filter_data in results.items():
            json_str = json.dumps(filter_data, separators=(',', ':'))
            if '"matchState":"MATCH_FOUND"' in json_str:
                filter_results.append(filter_name)
    except Exception as e:
        print(f"Error processing REST API results: {e}")
    return filter_results

def check_sdp_transformation(output_str):
    """Extracts the transformed (redacted) text from a Model Armor sanitization result string."""
    try:
        match = re.search(r'deidentify_result\s*{[^}]*?text:\s*"((?:[^"\\]|\\.)*)"', output_str, re.DOTALL)
        if match:
            return ast.literal_eval(f'"{match.group(1)}"')
    except Exception as e:
        print(f"Error extracting SDP transformation from string: {e}")
    return None

def check_sdp_transformation_for_file(response_data):
    """Extracts the transformed (redacted) text from a Model Armor file sanitization JSON result."""
    try:
        deidentify_result = response_data.get('sanitizationResult', {}).get('filterResults', {}).get('sdp', {}).get('sdpFilterResult', {}).get('deidentifyResult', {})
        if deidentify_result.get('matchState') == 'MATCH_FOUND':
            return deidentify_result.get('data', {}).get('text')
    except Exception as e:
        print(f"Error extracting SDP transformation from file JSON: {e}")
    return None

def analyze_response_with_template(response_text, template_name, location, modelarmor_client, use_default_response):
    template_display_name = template_name
    try:
        model_response_data = modelarmor_v1.DataItem()
        model_response_data.text = response_text
        response_sanitize_request = modelarmor_v1.SanitizeModelResponseRequest(name=get_template_path(template_name, location), model_response_data=model_response_data)
        response_check = modelarmor_client.sanitize_model_response(request=response_sanitize_request)
        output_str = str(response_check)
        filter_results = process_template_results(output_str)

        sdp_text = check_sdp_transformation(output_str)
        has_sdp = 'sdp' in filter_results

        if sdp_text and has_sdp and not use_default_response:
            response_text = sdp_text

        details = "❌ Violations found:\n" + "\n".join(f"• {result}" for result in filter_results) if filter_results else "✅ No template violations found"
        return {'response_text': response_text, 'analysis': {'template': template_display_name, 'status': 'fail' if filter_results else 'pass', 'details': details, 'matches': bool(filter_results), 'filter_results': filter_results, 'raw_output': output_str}, 'has_violations': bool(filter_results), 'has_sdp': has_sdp}
    except Exception as e:
        print(f"Error in response analysis: {e}")
        return {'response_text': response_text, 'analysis': {'template': template_display_name, 'status': 'error', 'details': f'Error in Model Armor analysis: {e}', 'matches': False, 'raw_output': str(e)}, 'has_violations': False}

def get_template_path(template_name, location):
    return f"projects/{project}/locations/{location}/templates/{template_name}"

def create_text_data_item(text):
    data_item = modelarmor_v1.DataItem()
    data_item.text = text
    return data_item

def sanitize_file_prompt_with_rest_api_optimized(file_data_base64, mime_type, template_name, location, endpoint):
    """Optimized version with caching and connection reuse"""
    # Check cache first
    cache_key = get_cache_key({'base64_data': file_data_base64, 'mime_type': mime_type}, template_name, location)
    cached_result = get_cached_result(cache_key)
    if cached_result:
        return cached_result
    
    try:
        access_token = get_cached_auth_token()
        
        url = f"https://{endpoint}/v1alpha/projects/{project}/locations/{location}/templates/{template_name}:sanitizeUserPrompt"
        
        payload = {
            "userPromptData": {
                "byteItem": {
                    "byteDataType": get_byte_data_type(mime_type),
                    "byteData": file_data_base64
                }
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = http_client.session.post(url, headers=headers, json=payload, timeout=(5, 30))
        response.raise_for_status()
        result = response.json()
        
        # Cache the result
        cache_result(cache_key, result)
        return result
        
    except Exception as e:
        print(f"Error in optimized file sanitization: {e}")
        raise e

def sanitize_text_prompt_optimized(text, template_name, location, endpoint_info):
    """Optimized text prompt sanitization with caching"""
    # Check cache first
    cache_key = get_cache_key(text, template_name, location)
    cached_result = get_cached_result(cache_key)
    if cached_result:
        return cached_result
    
    try:
        modelarmor_client = get_model_armor_client(location, endpoint_info['endpoint'])
        prompt_data_item = create_text_data_item(text)
        prompt_sanitize_request = modelarmor_v1.SanitizeUserPromptRequest(
            name=get_template_path(template_name, location),
            user_prompt_data=prompt_data_item
        )
        prompt_check = modelarmor_client.sanitize_user_prompt(request=prompt_sanitize_request)
        result = str(prompt_check)
        
        # Cache the result
        cache_result(cache_key, result)
        return result
        
    except Exception as e:
        print(f"Error in optimized text sanitization: {e}")
        raise e

# --- Async Processing Functions ---
async def analyze_prompt_async(prompt, file_data, prompt_template, location, endpoint_info):
    """Async wrapper for prompt analysis"""
    loop = asyncio.get_event_loop()
    
    def run_analysis():
        if file_data:
            result = sanitize_file_prompt_with_rest_api_optimized(
                file_data['base64_data'], file_data['mime_type'], 
                prompt_template, location, endpoint_info['endpoint']
            )
            output_str = json.dumps(result, indent=2)
            filter_results = process_rest_api_results(result)
            sdp_transformed_text = check_sdp_transformation_for_file(result)
            return {
                'output_str': output_str,
                'filter_results': filter_results,
                'sdp_transformed_text': sdp_transformed_text,
                'is_file': True
            }
        else:
            result = sanitize_text_prompt_optimized(prompt, prompt_template, location, endpoint_info)
            filter_results = process_template_results(result)
            sdp_transformed_text = check_sdp_transformation(result)
            return {
                'output_str': result,
                'filter_results': filter_results,
                'sdp_transformed_text': sdp_transformed_text,
                'is_file': False
            }
    
    return await loop.run_in_executor(None, run_analysis)

async def generate_response_async(prompt, model_info, system_instruction, file_data):
    """Async wrapper for model generation"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_model_response, prompt, model_info, system_instruction, file_data)

async def analyze_response_async(response_text, response_template, location, endpoint_info, use_default_response):
    """Async wrapper for response analysis"""
    loop = asyncio.get_event_loop()
    
    def run_analysis():
        modelarmor_client = get_model_armor_client(location, endpoint_info['endpoint'])
        return analyze_response_with_template(response_text, response_template, location, modelarmor_client, use_default_response)
    
    return await loop.run_in_executor(None, run_analysis)

# START: CORRECTED SEQUENTIAL LOGIC WITH FILE HANDLING
async def process_chat_async(prompt, model_info, system_instruction, file_data, 
                           prompt_template, response_template, location, endpoint_info, 
                           use_default_response, default_response, prompt_text):
    """
    Process Model Armor and model generation sequentially, with special handling
    for redacted file content.
    """
    prompt_analysis = None
    prompt_has_violations = False
    
    # These will be the final inputs for the LLM call
    prompt_for_llm = prompt 
    file_data_for_llm = file_data

    # --- Step 1: Analyze the prompt/file FIRST ---
    if prompt_template:
        print("INFO: Analyzing prompt/file with Model Armor...")
        prompt_analysis_result = await analyze_prompt_async(prompt, file_data, prompt_template, location, endpoint_info)
        
        filter_results = prompt_analysis_result['filter_results']
        output_str = prompt_analysis_result['output_str']
        sdp_transformed_text = prompt_analysis_result.get('sdp_transformed_text')
        is_file_analysis = prompt_analysis_result.get('is_file', False)

        if filter_results:
            prompt_has_violations = True

        # *** START THE FIX for File vs. Text Redaction ***
        if is_file_analysis and sdp_transformed_text:
            # If a FILE was analyzed and redacted, we must construct a new text prompt
            # that combines the user's original question with the redacted file content.
            prompt_for_llm = f"{prompt}\n\n--- Redacted File Content ---\n{sdp_transformed_text}"
            
            # CRITICAL: We must now remove the original file data so it's not sent to the LLM.
            # The LLM will work with the redacted text we just added to the prompt.
            file_data_for_llm = None
            print("INFO: Constructed new prompt from redacted file content. Original file data will not be sent to LLM.")

        elif not is_file_analysis and sdp_transformed_text:
            # This is for the simple case where the user's TEXT prompt was redacted.
            prompt_for_llm = sdp_transformed_text
            print(f"INFO: Using redacted text prompt for LLM: '{sdp_transformed_text}'")
        # *** END THE FIX ***

        details = "❌ Violations found:\n" + "\n".join(f"• {result}" for result in filter_results) if filter_results else "✅ No template violations found"
        prompt_analysis = {
            'template': prompt_template, 'status': 'fail' if filter_results else 'pass',
            'details': details, 'matches': bool(filter_results),
            'filter_results': filter_results, 'raw_output': output_str
        }

    # If prompt had violations and we should use a default, we can stop here.
    if prompt_has_violations and use_default_response:
        print("INFO: Prompt violation found, using default response.")
        return {
            'response': default_response,
            'prompt_analysis': prompt_analysis,
            'response_analysis': None
        }

    # --- Step 2: Generate the model response using the corrected inputs ---
    print(f"INFO: Generating content with model '{model_info['name']}'.")
    model_response = await generate_response_async(prompt_for_llm, model_info, system_instruction, file_data_for_llm)
    
    # --- Step 3: Analyze the response (as before) ---
    response_analysis = None
    if response_template:
        print("INFO: Analyzing response with Model Armor...")
        response_result = await analyze_response_async(model_response, response_template, location, endpoint_info, use_default_response)
        response_analysis = response_result['analysis']
        if response_result['has_violations']:
            if use_default_response:
                print("INFO: Response violation found, using default response.")
                model_response = default_response
            else:
                # Use the redacted response if available
                model_response = response_result.get('response_text', model_response)
                print("INFO: Response violation found, using redacted response.")

    return {
        'response': model_response,
        'prompt_analysis': prompt_analysis,
        'response_analysis': response_analysis
    }
# END: CORRECTED SEQUENTIAL LOGIC WITH FILE HANDLING

@app.route('/')
def home():
    initial_location = model_armor_endpoints[0]['location']
    initial_endpoint = model_armor_endpoints[0]['endpoint']
    prompt_templates, response_templates = fetch_model_armor_templates(initial_location, initial_endpoint)
    return render_template('index.html', foundation_models=foundation_models, model_armor_endpoints=model_armor_endpoints, prompt_templates=prompt_templates, response_templates=response_templates)

@app.route('/templates/<location>')
def get_templates_for_location(location):
    endpoint_info = next((e for e in model_armor_endpoints if e["location"] == location), None)
    if not endpoint_info: 
        return jsonify({'error': 'Invalid location'}), 404
    prompt_templates, response_templates = fetch_model_armor_templates(location, endpoint_info['endpoint'])
    return jsonify({'prompt_templates': prompt_templates, 'response_templates': response_templates})

# --- START: MODIFIED ENDPOINT FOR PROMPT ANALYSIS (NOW HANDLES FILES) ---
@app.route('/analyze_prompt', methods=['POST'])
def analyze_prompt():
    """
    A dedicated endpoint to only run prompt analysis and return quickly.
    Handles both text and file prompts.
    """
    try:
        prompt_analysis = None
        filter_results = []
        output_str = ""

        # Handle file upload scenario
        if 'file' in request.files:
            file = request.files.get('file')
            prompt_template = request.form.get('promptTemplate')
            location = request.form.get('location')
            
            if not file or not prompt_template or not location:
                return jsonify({'error': 'Missing file, template, or location for analysis'}), 400
            
            endpoint_info = next((e for e in model_armor_endpoints if e["location"] == location), None)
            if not endpoint_info:
                return jsonify({'error': 'Invalid location for analysis'}), 400

            # Generate a cache key based on filename and file size
            file.seek(0, 2)  # Seek to end
            file_size = file.tell()
            file.seek(0)  # Seek back to start
            file_cache_key = f"{file.filename}_{file_size}"
            
            # Check if we have this file cached
            if file_cache_key in file_cache:
                cached_data, timestamp = file_cache[file_cache_key]
                if time.time() - timestamp < CACHE_TTL:
                    file_data_base64 = cached_data['base64_data']
                    mime_type = cached_data['mime_type']
                    print(f"INFO: Using cached file data for {file.filename}")
                else:
                    del file_cache[file_cache_key]
                    file_content = file.read()
                    file_data_base64 = base64.b64encode(file_content).decode('utf-8')
                    mime_type = mimetypes.guess_type(file.filename)[0]
                    file_cache[file_cache_key] = ({'base64_data': file_data_base64, 'mime_type': mime_type}, time.time())
            else:
                file_content = file.read()
                file_data_base64 = base64.b64encode(file_content).decode('utf-8')
                mime_type = mimetypes.guess_type(file.filename)[0]
                # Cache the file data
                file_cache[file_cache_key] = ({'base64_data': file_data_base64, 'mime_type': mime_type}, time.time())
                # Clean old cache entries if cache is too large
                if len(file_cache) > 50:
                    current_time = time.time()
                    expired_keys = [k for k, (_, timestamp) in file_cache.items()
                                   if current_time - timestamp > CACHE_TTL]
                    for k in expired_keys:
                        del file_cache[k]

            result = sanitize_file_prompt_with_rest_api_optimized(
                file_data_base64, mime_type, prompt_template, location, endpoint_info['endpoint']
            )
            output_str = json.dumps(result, indent=2)
            filter_results = process_rest_api_results(result)

        # Handle text-only scenario
        else:
            data = request.get_json()
            prompt = data.get('prompt', '')
            prompt_template = data.get('promptTemplate')
            location = data.get('location')

            if not prompt_template:
                return jsonify({'prompt_analysis': None}) # Nothing to do

            endpoint_info = next((e for e in model_armor_endpoints if e["location"] == location), None)
            if not endpoint_info:
                return jsonify({'error': 'Invalid location for analysis'}), 400
            
            output_str = sanitize_text_prompt_optimized(prompt, prompt_template, location, endpoint_info)
            filter_results = process_template_results(output_str)

        # Common response structure
        prompt_analysis = {
            'template': prompt_template,
            'status': 'fail' if filter_results else 'pass',
            'raw_output': output_str
        }
        
        return jsonify({'prompt_analysis': prompt_analysis})

    except Exception as e:
        error_message = f"An unexpected error occurred in prompt analysis: {str(e)}"
        print(f"ERROR in /analyze_prompt: {traceback.format_exc()}")
        return jsonify({
            'error': error_message,
            'prompt_analysis': {
                'template': request.form.get('promptTemplate') or request.get_json().get('promptTemplate'),
                'status': 'error',
                'raw_output': traceback.format_exc()
            }
        }), 500
# --- END: MODIFIED ENDPOINT ---


@app.route('/chat', methods=['POST'])
def chat():
    file_data = None
    is_file_upload = False

    if 'file' in request.files:
        file = request.files['file']
        prompt_text = request.form.get('prompt', '')
        model_name_from_ui = request.form.get('model')
        location = request.form.get('location', 'us-central1')
        prompt_template = request.form.get('promptTemplate')
        response_template = request.form.get('responseTemplate')
        default_response = request.form.get('defaultResponse')
        use_default_response = request.form.get('useDefaultResponse') == 'true'
        system_instruction = request.form.get('systemInstruction', '')
        
        # Generate a cache key based on filename and file size
        file.seek(0, 2)  # Seek to end
        file_size = file.tell()
        file.seek(0)  # Seek back to start
        file_cache_key = f"{file.filename}_{file_size}"
        
        # Check if we have this file cached
        if file_cache_key in file_cache:
            cached_data, timestamp = file_cache[file_cache_key]
            if time.time() - timestamp < CACHE_TTL:
                file_data_base64 = cached_data['base64_data']
                mime_type = cached_data['mime_type']
                print(f"INFO: Using cached file data for {file.filename}")
            else:
                del file_cache[file_cache_key]
                file_content = file.read()
                file_data_base64 = base64.b64encode(file_content).decode('utf-8')
                mime_type = mimetypes.guess_type(file.filename)[0]
                file_cache[file_cache_key] = ({'base64_data': file_data_base64, 'mime_type': mime_type}, time.time())
        else:
            file_content = file.read()
            file_data_base64 = base64.b64encode(file_content).decode('utf-8')
            mime_type = mimetypes.guess_type(file.filename)[0]
            # Cache the file data
            file_cache[file_cache_key] = ({'base64_data': file_data_base64, 'mime_type': mime_type}, time.time())
        
        file_data = {
            'base64_data': file_data_base64,
            'mime_type': mime_type,
            'filename': file.filename
        }
        prompt = prompt_text if prompt_text else f"Please analyze this document: {file.filename}"
        is_file_upload = True

    else:
        data = request.get_json()
        prompt = data.get('prompt')
        model_name_from_ui = data.get('model')
        location = data.get('location', 'us-central1')
        prompt_template = data.get('promptTemplate')
        response_template = data.get('responseTemplate')
        default_response = data.get('defaultResponse')
        use_default_response = data.get('useDefaultResponse', True)
        system_instruction = data.get('systemInstruction', '')
        prompt_text = prompt

    model_info = next((m for m in foundation_models if m.get("display_name") == model_name_from_ui or m["name"] == model_name_from_ui), None)
    if not model_info: 
        return jsonify({'error': 'Invalid model selected'}), 400

    endpoint_info = next((e for e in model_armor_endpoints if e["location"] == location), None)
    if not endpoint_info: 
        return jsonify({'error': 'Invalid location provided'}), 400

    try:
        # Always use Model Armor mode
        print("Using corrected sequential processing approach with Model Armor")
        
        # Use the corrected sequential processing approach with Model Armor
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(process_chat_async(
            prompt, model_info, system_instruction, file_data,
            prompt_template, response_template, location, endpoint_info,
            use_default_response, default_response, prompt_text
        ))
        
        loop.close()
        
        response_text = result['response']
        prompt_analysis = result['prompt_analysis']
        response_analysis = result['response_analysis']
        
        return jsonify({
            'response': response_text,
            'source': model_info.get('provider'),
            'model_armor': {
                'prompt_analysis': prompt_analysis,
                'response_analysis': response_analysis
            }
        })
        
    except Exception as e:
        error_message = f"An unexpected error occurred during chat processing: {str(e)}"
        print(f"ERROR in /chat: {traceback.format_exc()}")
        return jsonify({
            'error': error_message,
            'response': error_message,
            'source': 'System',
            'model_armor': {
                'prompt_analysis': {'status': 'error', 'raw_output': traceback.format_exc()},
                'response_analysis': {'status': 'error', 'raw_output': traceback.format_exc()}
            }
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)