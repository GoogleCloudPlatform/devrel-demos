# Use the official vLLM OpenAI-compatible image as the base
FROM vllm/vllm-openai:latest

# Set environment variables
ENV MODEL_ID="google/gemma-3-27b-it"
ENV MODEL_PATH="/models/gemma-3-27b"
ENV HF_HUB_ENABLE_HF_TRANSFER=1
ENV VLLM_CACHE_ROOT="/root/.cache/vllm"

# Build argument for HF_TOKEN
ARG HF_TOKEN

# Install HF Transfer and huggingface_hub
RUN python3 -m pip install huggingface_hub[hf_transfer]

# Pre-create cache directory and COPY the pre-compiled kernels
RUN mkdir -p ${VLLM_CACHE_ROOT}/torch_compile_cache
COPY torch_compile_cache ${VLLM_CACHE_ROOT}/torch_compile_cache

# Download the standard Gemma 3 27B IT model (BF16)
# This model is ~54GB and will fit comfortably on the RTX 6000 (96GB VRAM)
RUN mkdir -p ${MODEL_PATH} && \
    hf download ${MODEL_ID} --local-dir ${MODEL_PATH} --token ${HF_TOKEN}

# Expose the default Cloud Run port
EXPOSE 8080

# Run vLLM with the requested configuration
ENTRYPOINT ["python3", "-m", "vllm.entrypoints.openai.api_server"]
CMD [ \
    "--model", "/models/gemma-3-27b", \
    "--load-format", "runai_streamer", \
    "--gpu-memory-utilization", "0.85", \
    "--tensor-parallel-size", "1", \
    "--max-model-len", "16384", \
    "--trust-remote-code", \
    "--port", "8080" \
]
