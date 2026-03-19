#!/bin/bash -x

# Configuration
API_IP="34.162.252.218"
MODEL="/models/qwen3-30b-weights"
TOKENIZER="../qwen3-30b-weights"
DATASET="./ShareGPT_V3_unfiltered_cleaned_split.json"
NUM_PROMPTS=100
REQUEST_RATE=4  # Start with 4, then try 'inf' to see the difference

python3 -m vllm.entrypoints.cli.main bench serve \
    --base-url "http://${API_IP}:8000/v1" \
    --backend openai-chat \
    --endpoint /chat/completions \
    --model "$MODEL" \
    --tokenizer "$TOKENIZER" \
    --dataset-name sharegpt \
    --dataset-path "$DATASET" \
    --num-prompts "$NUM_PROMPTS" \
    --request-rate "$REQUEST_RATE" \
    --trust-remote-code \
    --temperature 0
