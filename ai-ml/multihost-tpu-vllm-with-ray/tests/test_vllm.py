import argparse
import openai
import sys

def main():
    parser = argparse.ArgumentParser(description="Test vLLM API on TPU cluster")
    parser.add_argument("ip", help="The IP address of the vLLM server")
    parser.add_argument("--port", default="8000", help="The port number (default: 8000)")
    parser.add_argument("--model", default="/models/qwen3-30b-weights", help="Model path used in vLLM")
    
    args = parser.parse_args()

    # Initialize the client with the provided IP and Port
    base_url = f"http://{args.ip}:{args.port}/v1"
    print(f"Connecting to: {base_url}...")

    client = openai.OpenAI(base_url=base_url, api_key="tpu-demo")

    try:
        response = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": "Write a haiku about high-performance computing on TPUs."}],
            temperature=0.7
        )
        print("\n--- Response from Qwen3 ---")
        print(response.choices[0].message.content)
        print("---------------------------\n")
    except Exception as e:
        print(f"Error connecting to vLLM: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
