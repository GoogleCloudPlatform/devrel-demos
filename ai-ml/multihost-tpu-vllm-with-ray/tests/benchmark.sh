#!/bin/bash -x
#
python3 -m vllm.entrypoints.cli.main bench serve \
  --base-url http://34.162.252.218:8000/v1 \
  --backend openai-chat \
  --endpoint /chat/completions \
  --model /models/qwen3-30b-weights \
  --tokenizer ../qwen3-30b-weights \
  --dataset-name random \
  --num-prompts 200 \
  --request-rate 12
