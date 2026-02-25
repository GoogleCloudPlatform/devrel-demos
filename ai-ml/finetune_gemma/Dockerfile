# syntax=docker/dockerfile:1.4
FROM nvidia/cuda:12.8.0-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/local/cuda/targets/x86_64-linux/lib:${LD_LIBRARY_PATH}
ENV BNB_CUDA_VERSION=128
ENV PIP_NO_CACHE_DIR=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-dev \
        build-essential \
        git \
        libjpeg-dev \
        libpng-dev \
        libgomp1 \
        libgl1 \
        libglx-mesa0 && \
    rm -rf /var/lib/apt/lists/*

# Copy uv binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy only requirements first
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN uv venv ${VIRTUAL_ENV} && \
    uv pip install \
        --index-strategy unsafe-best-match \
        --index-url https://download.pytorch.org/whl/cu128 \
        --extra-index-url https://pypi.org/simple \
        -r requirements.txt

# Workaround for bitsandbytes/triton compatibility on Blackwell/CUDA 12.8
# Fixes: ModuleNotFoundError: No module named 'triton.ops'
RUN TritonPath=$(python3 -c "import triton; print(triton.__path__[0])") && \
    mkdir -p "$TritonPath/ops" && \
    touch "$TritonPath/ops/__init__.py" && \
    echo "def early_config_prune(*args, **kwargs): return []" > "$TritonPath/ops/matmul_perf_model.py" && \
    echo "def estimate_matmul_time(*args, **kwargs): return 0.1" >> "$TritonPath/ops/matmul_perf_model.py"

# Ensure bitsandbytes finds a compatible CUDA binary for 12.8
RUN BnbPath=$(python3 -c "import bitsandbytes as bnb; print(bnb.__path__[0])") && \
    if [ ! -f "$BnbPath/libbitsandbytes_cuda128.so" ]; then \
        ln -s "$BnbPath/libbitsandbytes_cuda121.so" "$BnbPath/libbitsandbytes_cuda128.so" || true; \
    fi

# Copy code last (most frequently changed)
COPY finetune_and_evaluate.py .

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/tmp/huggingface
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache
ENV TORCH_HOME=/tmp/torch_cache
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN mkdir -p /tmp/huggingface /tmp/transformers_cache /tmp/torch_cache /tmp/gemma3-finetuned && \
    chmod -R 777 /tmp

ENTRYPOINT ["python3", "/app/finetune_and_evaluate.py"]
CMD ["--device", "cuda", "--train-size", "1000", "--eval-size", "200", "--model-id", "google/gemma-3-4b-it"]

