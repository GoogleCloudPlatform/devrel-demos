# Use the official vLLM OpenAI-compatible image as the base
FROM vllm/vllm-openai:latest

# Set environment variables
ENV MODEL_ID="google/gemma-3-27b-it"
ENV BASE_MODEL_PATH="/models/gemma-3-27b"
ENV LORA_PATH="/models/gemma-3-pet-adapter"
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV VLLM_CACHE_ROOT="/root/.cache/vllm"

# Build argument for HF_TOKEN and PROJECT_ID
ARG HF_TOKEN
ARG PROJECT_ID

# Install HF Transfer, huggingface_hub, and GCP SDK
RUN python3 -m pip install huggingface_hub[hf_transfer] google-cloud-storage

# Pre-create cache directory and COPY the pre-compiled kernels
RUN mkdir -p ${VLLM_CACHE_ROOT}/torch_compile_cache
COPY torch_compile_cache ${VLLM_CACHE_ROOT}/torch_compile_cache

# Download the base Gemma 3 27B IT model (BF16)
RUN mkdir -p ${BASE_MODEL_PATH} && \
    hf download ${MODEL_ID} --local-dir ${BASE_MODEL_PATH} --token ${HF_TOKEN}

# Download the fine-tuned adapter weights from GCS
COPY download_weights.py .
RUN python3 download_weights.py \
    --bucket shir-training-gemma3-finetuning-eu \
    --prefix gemma3-finetuned \
    --output ${LORA_PATH} \
    --project ${PROJECT_ID}

# Expose the default Cloud Run port
EXPOSE 8080

# Run vLLM with LoRA enabled
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD [ \
    "--model", "/models/gemma-3-27b", \
    "--enable-lora", \
    "--lora-modules", "pet-analyzer=/models/gemma-3-pet-adapter", \
    "--load-format", "runai_streamer", \
    "--gpu-memory-utilization", "0.80", \
    "--max-model-len", "8192", \
    "--trust-remote-code", \
    "--port", "8080" \
]
