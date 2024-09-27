import os
import time
import uuid

from google.cloud import bigquery
from google.cloud import firestore
from nicegui import app, run, ui
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
import pandas as pd
from sentence_transformers import SentenceTransformer
import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.evaluation import EvalTask, PointwiseMetric

# Define constants
# Instantiate OpenTelemetry
provider = TracerProvider()
processor = BatchSpanProcessor(ConsoleSpanExporter())
provider.add_span_processor(processor)

# Sets the global default tracer provider
trace.set_tracer_provider(provider)

# Creates a tracer from the global tracer provider
TRACER = trace.get_tracer("my.tracer.name")

PROJECT_ID = os.environ.get("PROJECT")
REGION = os.environ.get("REGION", "us-central1")

# Initialize VertexAI
vertexai.init(project=PROJECT_ID, location=REGION)

BIGQUERY_CLIENT = bigquery.Client(project=PROJECT_ID)
FIRESTORE_CLIENT = firestore.Client(project=PROJECT_ID, database="gemini-hackathon")
GEMINI_ENDPOINT = GenerativeModel("gemini-1.5-flash")
TRANSFORMER_MODEL = None


def get_embedding(prompt):
    global TRANSFORMER_MODEL

    if not TRANSFORMER_MODEL:
        TRANSFORMER_MODEL = SentenceTransformer("all-miniLM-L6-v2")
    embeddings = TRANSFORMER_MODEL.encode(prompt)
    return embeddings.tolist()


def make_gemini_prediction(prompt: str) -> str:
    try:
        return GEMINI_ENDPOINT.generate_content(prompt).text
    except Exception as e:
        print(e)
        raise()
    

def prompt_maker(input) -> tuple[str, str, str]:
    context = get_rag_context(input)
    version = os.environ.get("PROMPT_VERSION", "v20240926.1")
    ref = FIRESTORE_CLIENT.collection(f"prompts").document(document_id=version).get()
    prompt = ref.to_dict()["prompt"].format(input=input, context=context)
    return prompt, version
    

def write_to_database(client_id: str, data: dict):
    FIRESTORE_CLIENT.collection("requests").add(data, document_id=client_id)


def multiturn_quality(history, prompt, response):
    # Define a pointwise multi-turn chat quality metric 
    pointwise_chat_quality_metric_prompt = """Evaluate the AI's contribution to a meaningful conversation, considering coherence, fluency, groundedness, and conciseness.
    Review the chat history for context. Rate the response on a 1-5 scale, with explanations for each criterion and its overall impact.
    

    # Conversation History
    {history}

    # Current User Prompt
    {prompt}

    # AI-generated Response
    {response}
    """

    freeform_multi_turn_chat_quality_metric = PointwiseMetric(
        metric="multi_turn_chat_quality_metric",
        metric_prompt_template=pointwise_chat_quality_metric_prompt,
    )

    eval_dataset = pd.DataFrame(
        {
            "history": [history],
            "prompt": prompt,
            "response": response
        }
    )

    # Run evaluation using the defined metric
    eval_task = EvalTask(
        dataset=eval_dataset, 
        metrics=[freeform_multi_turn_chat_quality_metric],
    )

    result = eval_task.evaluate()

    return {
        "score": result.metrics_table["multi_turn_chat_quality_metric/score"].item(),
        "explanation": result.metrics_table["multi_turn_chat_quality_metric/explanation"].item(),
        "mean": result.summary_metrics["multi_turn_chat_quality_metric/mean"].item()
    }


def get_rag_context(input):
    embedding = get_embedding(input)

    query = f"""
        SELECT * 
        FROM `{PROJECT_ID}.rag_data.rag_data`
        WHERE id IN (
            SELECT s.base.id
            FROM VECTOR_SEARCH(
                TABLE `{PROJECT_ID}.rag_data.embeddings`,
                "embeddings", 
                (SELECT {embedding}),
                top_k => 5) as s);
    """
    print("waiting")
    rows = BIGQUERY_CLIENT.query_and_wait(query)
    print("waited")
    bodies = [row["body"] for row in rows]
    return " ### ".join(bodies)


@ui.page('/')
def index():
    async def update_prompt():
        print("prompt received")
        input_time = time.time()
        user_input = user_input_raw.value

        with chat_container:
            ui.chat_message(user_input, name='Me')
            
            print("spinner")
            spinner = ui.spinner('audio', size='lg', color='green')
            
            client_id = str(uuid.uuid4())
            request_id = f"{client_id}-{str(uuid.uuid4())[:8]}"
            
            prompt, prompt_version = await run.cpu_bound(prompt_maker, user_input)

            app.storage.client["count"] = app.storage.client.get("count", 0) + 1
            app.storage.client["history"] = app.storage.client.get("history", "") + "### User: " + prompt 

            with TRACER.start_as_current_span("child") as span:
                span.set_attribute(
                    "operation.count", app.storage.client["count"])
                span.set_attribute("prompt", user_input)
                span.set_attribute("prompt_id", prompt_version)
                span.set_attribute("client_id", client_id)
                span.set_attribute("request_id", request_id)

                request_time = time.time()
                
                response = await run.io_bound(make_gemini_prediction, prompt)
                # response = make_prediction(user_input)
                response_time = time.time()
                app.storage.client["history"] = app.storage.client.get("history") + "### Agent: " + response
                span.set_attribute("response", response)

            spinner.delete()

            ui.chat_message(response,
                    name='Robot',
                    stamp='now',
                    avatar='https://robohash.org/ui',) \
                    .style('font-family: Comic Sans, sans-serif; font-size: 16px;')
        
            query = {
                "request_id": request_id,
                "prompt": user_input,
                "response": response,
                "input_time": input_time,
                "request_time": request_time,
                "response_time": response_time,
                "prompt_version": prompt_version
            }
            print(f"Count: {app.storage.client['count']}")
            write_to_database(client_id, query)
            # print(multiturn_quality(
            #     app.storage.client.get("history"),
            #     prompt,
            #     response
            # ))
    
    ui.markdown("<h2>Welcome to predictions bot!</h2>")
    with ui.row().classes('flex flex-col h-screen'):
        chat_container = ui.column().classes('w-full max-w-3xl mx-auto my-6')
    
    with ui.footer().classes('bg-black'), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            user_input_raw = ui.input("Prompt").on('keydown.enter', update_prompt) \
                .props('rounded outlined input-class=mx-3').classes('flex-grow')


ui.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), storage_secret="1234", dark=True)