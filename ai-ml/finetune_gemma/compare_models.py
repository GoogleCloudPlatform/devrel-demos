import os
import base64
import json
import requests
import subprocess

def get_id_token(url):
    """Get identity token for authentication."""
    cmd = ["gcloud", "auth", "print-identity-token"]
    return subprocess.check_output(cmd).decode("utf-8").strip()

def download_from_gcs(gcs_path, local_path):
    """Download file from GCS."""
    cmd = ["gcloud", "storage", "cp", gcs_path, local_path]
    subprocess.run(cmd, check=True, capture_output=True)

def encode_image(image_path):
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def call_model(url, token, model_id, messages):
    """Call the vLLM API."""
    endpoint = f"{url.rstrip('/')}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 512,
        "temperature": 0
    }
    try:
        response = requests.post(endpoint, headers=headers, json=data)
        if response.status_code != 200:
            return f"Error: {response.status_code} - {response.text}"
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Request failed: {e}"

def main():
    # Both models are on the same test service
    service_url = "https://gemma-3-finetuned-test-400520706792.europe-west4.run.app"
    
    # We'll use a mix of breeds, including some potentially tricky ones.
    images = [
        "gs://cats-and-dogs-w4/images/Bengal_1.jpg",
        "gs://cats-and-dogs-w4/images/pug_1.jpg",
        "gs://cats-and-dogs-w4/images/saint_bernard_1.jpg",
        "gs://cats-and-dogs-w4/images/keeshond_1.jpg",
        "gs://cats-and-dogs-w4/images/Sphynx_1.jpg",
        "gs://cats-and-dogs-w4/images/staffordshire_bull_terrier_1.jpg",
        "gs://cats-and-dogs-w4/images/Bombay_1.jpg"
    ]
    
    token = get_id_token(service_url)
    
    prompt = """Please analyze this pet image and provide the following details:
1. **Breed Identification**: What breed(s) is this pet?
2. **Species**: Is it a dog or a cat?
3. **Key Characteristics**: Describe its physical features (coat, size, color).
4. **General Temperament**: What is this breed known for?
5. **Care Advice**: Provide 2-3 specific care tips for this breed.

Finally, provide a very short "Title" for this analysis in the format: "TITLE: [Animal] [Breed]" (e.g., TITLE: Dog Golden Retriever)."""

    for gcs_path in images:
        filename = gcs_path.split("/")[-1]
        local_path = f"/tmp/{filename}"
        
        print(f"\n{'='*80}")
        print(f"Analyzing: {filename}")
        print(f"{'='*80}")
        
        try:
            download_from_gcs(gcs_path, local_path)
            b64_image = encode_image(local_path)
            
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }
            ]
            
            print("\n--- BASE MODEL (/mnt/models/google/gemma-4-31b-it) ---")
            # We must use the exact model string the vLLM engine knows
            base_res = call_model(service_url, token, "/mnt/models/google/gemma-4-31b-it", messages)
            print(base_res)
            
            print("\n--- FINE-TUNED MODEL (pet-analyzer) ---")
            ft_res = call_model(service_url, token, "pet-analyzer", messages)
            print(ft_res)
            
            os.remove(local_path)
        except Exception as e:
            print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    main()
