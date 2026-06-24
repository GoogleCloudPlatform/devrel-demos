---
id: high-performance-distributed-rl-sandbox
summary: This lab demonstrates how to securely evaluate untrusted, LLM-generated code during a Reinforcement Learning training loop using GKE Agent Sandboxes (gVisor) and Ray.
authors: Drew Brown
categories: GKE, Vertex AI, RL, AI
tags: GKE, Agent Sandbox, gVisor, Ray, TRL, GRPO
feedback_link: https://github.com/googlecodelabs/feedback/issues/new?title=[high-performance-distributed-rl-sandbox]:&labels[]=content-platform&labels[]=cloud
analytics_account: UA-66226300-1
keywords: docType:Codelab,skill:Advanced,language:Python,category:Cloud,category:AiAndMachineLearning,product:GoogleKubernetesEngine,product:VertexAi

---

# High-Performance Distributed RL on GKE Standard: The Complete Guide

## Introduction

This lab details how to build, provision, and execute a high-performance distributed Reinforcement Learning (RL) training loop on **GKE Standard** with **GKE Agent Sandboxes (gVisor)**, using the **Group Relative Policy Optimization (GRPO)** algorithm with the `trl` library.

The goal is to demonstrate how to securely evaluate untrusted, LLM-generated code during an RL training loop. We achieve this by decoupling the orchestration plane (Ray) from the execution plane (GKE Agent Sandboxes).

### The Technical Challenge of RL Code Evaluation

When training LLM agents using Reinforcement Learning (e.g., training a model to write code by evaluating its output on unit tests), the training loop must execute thousands of untrusted, LLM-generated Python scripts in parallel. This introduces critical challenges:

1. **The Pod Churn Bottleneck:** Traditional evaluation frameworks spin up a fresh Docker container per task. Doing this dynamically for hundreds of parallel rollouts during an RL training loop causes severe load on the Kubernetes control plane. The latency makes high-frequency RL training impossible.
2. **The Security Risk:** Running arbitrary, LLM-generated code inside standard container runtimes shares the host OS kernel. A single escape vulnerability can compromise your nodes.
3. **IAM Token Theft:** LLM-generated code running inside a Kubernetes pod can query the cloud provider's metadata server to steal node IAM service account tokens.

### The Solution: Decoupled Orchestration & Execution

This architecture **decouples orchestration from execution**:

* **The Orchestrator (Ray):** A distributed Ray cluster manages the RL training loop and distributes rollout generation.
* **The Execution Plane (GKE Agent Sandbox):** Instead of creating Kubernetes pods dynamically, Ray workers make simple HTTP calls to a dedicated **Sandbox Router**. The router instantly assigns the worker an isolated, pre-warmed container running under **gVisor (GKE Sandbox)**.
* **Sub-Second Latency:** Because sandboxes are pre-warmed in a managed `SandboxWarmPool` and managed via a high-speed HTTP gateway, environment creation drops to **under 200ms**, completely bypassing the Kubernetes control plane.

### Lab Objectives

In this codelab, you will learn:
* The architectural challenges and solutions for evaluating untrusted code in RL loops.
* How to build custom sandbox images for efficient rollouts.
* How to configure and use GKE Agent Sandboxes and SandboxWarmPools.
* How to securely isolate sandboxes to prevent IAM token theft.
* How to run a basic RL training job with SweBench and TRL using Ray to decouple orchestration from execution.

## Cluster Creation & Prerequisites

Before proceeding, you need a GKE cluster with a high-performance GPU node pool and the Ray Operator installed to manage the training workload. 

### Environment Variables

First, set the environment variables that will be used throughout this codelab. The commands below use sensible defaults, but you can change them as needed to match your specific Google Cloud environment:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export REGION="us-west3"
export ZONE="us-west3-a"
export REPO_NAME="rl-sandbox-repo"
```

Create an Artifact Registry repository to hold the custom container images:

```bash
gcloud artifacts repositories create $REPO_NAME \
    --repository-format=docker \
    --location=$REGION \
    --description="Repository for RL Sandbox images"
```

### Cluster Configuration

For a complete walkthrough on provisioning a GKE cluster optimized for AI workloads (including GPUDirect RDMA network wiring), follow the official documentation:
[Create a GKE AI Hypercompute Custom Cluster](https://docs.cloud.google.com/ai-hypercomputer/docs/create/gke-ai-hypercompute-custom#create-cluster)

**Crucial Prerequisite:** When creating your cluster or a specific execution node pool, ensure you pass the `--enable-agent-sandbox` and `--sandbox type=gvisor` flags to install the required Custom Resource Definitions (CRDs) for the Sandbox warm pools.

Assuming your cluster, GPUs, and Ray Operator are running, everything below details how to configure the execution plane and run the RL loop.

## Build Custom Images

A crucial aspect of running high-performance RL is baking dependencies into your images. We need two distinct images: one for the GPU workers running the model, and one for the isolated sandboxes running the untrusted evaluation code.

### 1. Build the GPU Worker Image

The Ray GPU worker needs libraries to run the language model and orchestrate the training loop. We build this image on top of the official vLLM image so it supports the latest GPUs and has PyTorch/CUDA pre-installed.

Run the following command to create `Dockerfile.gpu_worker`:
```bash
cat << 'EOF' > Dockerfile.gpu_worker
# ==============================================================================
# Base Image: Use the official vLLM production image. 
# This image comes pre-baked with PyTorch 2.11, CUDA 13.0, and vLLM.
# It supports sm_100 Blackwell GPUs natively!
# ==============================================================================
FROM vllm/vllm-openai:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    numactl \
    libnuma-dev \
    wget \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Ray, TRL, and Sandbox tools
# TRL does not require compiling flash_attn from source.
RUN pip install --no-cache-dir \
    "ray[default]==2.55.1" \
    "numpy<2.0" \
    gymnasium>=0.28.1 \
    k8s-agent-sandbox>=0.4.6 \
    trl transformers packaging ninja cachetools accelerate datasets peft
EOF
```

Build and push the image to your Artifact Registry repository:

```bash
export WORKER_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ray-gpu-worker:v1"
docker build -f Dockerfile.gpu_worker -t $WORKER_REPO .
docker push $WORKER_REPO
```

### 2. Build the CPU Head Image

The Ray head node only orchestrates the cluster and does not run the heavy GPU training models. To avoid a massive image pull bottleneck (typically 15GB+) on your standard CPU nodes, we build a lightweight, CPU-only image for the head node. This image contains Ray and the required Python libraries, but excludes heavy GPU libraries like CUDA and vLLM.

Run the following command to create `Dockerfile.head`:

```bash
cat << 'EOF' > Dockerfile.head
# ==============================================================================
# Base Image: Use the official Python slim image for the exact patch version.
# This aligns the Python version (3.12.13) with the GPU worker node.
# ==============================================================================
FROM python:3.12.13-slim

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Ray, TRL, and Sandbox tools (CPU versions where applicable)
# We install torch CPU first to avoid pulling the 2GB+ CUDA torch package.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    "ray[default]==2.55.1" \
    "numpy<2.0" \
    gymnasium>=0.28.1 \
    k8s-agent-sandbox>=0.4.6 \
    trl transformers packaging ninja cachetools accelerate datasets peft

# Create a 'ray' user to run the container securely and match Ray conventions
RUN useradd -ms /bin/bash ray
USER ray
WORKDIR /home/ray
EOF
```

Build and push the image:

```bash
export HEAD_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ray-head:v1"
docker build -f Dockerfile.head -t $HEAD_REPO .
docker push $HEAD_REPO
```

### 3. Build the Sandbox Image

The sandbox needs the specific dependencies for the task we are evaluating so that runtime installation is instantaneous. For this codelab, we will use an issue from the `django/django` repository in SWE-bench. We will pre-clone the repository and pre-build the python environments so our model scripts don't waste time downloading them in the RL loop.

Run the following command to create `Dockerfile.sandbox`:

```bash
cat << 'EOF' > Dockerfile.sandbox
# Use a stable Debian-based Miniconda image
FROM condaforge/miniforge3:latest

# 1. Install essential system libraries (including sqlite3 for Django tests)
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Set up the /workspace directory and grant ownership to the pre-existing non-root 'ubuntu' user (UID 1000)
RUN mkdir -p /workspace \
    && chown -R 1000:1000 /workspace

# 3. Switch to the non-root user
USER ubuntu
WORKDIR /workspace

# 4. Pre-configure Git globally so the agent can run git commands
RUN git config --global user.email "agent@gke-sandbox.local" \
    && git config --global user.name "Agent"

# 5. Pre-clone the repository as the non-root user
RUN git clone https://github.com/django/django.git .

# 6. Pre-build Conda environments and pre-cache common dependencies
# We do NOT run "pip install -e ." here to avoid Python version conflicts with the main branch.
# Instead, we pre-install the heavy dependencies so that runtime installation is instantaneous.
RUN conda create -y -n django-py39 python=3.9 \
    && conda run -n django-py39 pip install --no-cache-dir asgiref sqlparse tzdata pytest pytest-django

RUN conda create -y -n django-py310 python=3.10 \
    && conda run -n django-py310 pip install --no-cache-dir asgiref sqlparse tzdata pytest pytest-django

# --- Add Agent Server ---
# We use a multi-stage build to copy the agent server from the official python-runtime-sandbox image
COPY --from=registry.k8s.io/agent-sandbox/python-runtime-sandbox:v0.1.0 /app /opt/sandbox-agent
USER root
RUN chown -R 1000:1000 /opt/sandbox-agent \
    && /opt/conda/bin/pip install --no-cache-dir -r /opt/sandbox-agent/requirements.txt \
    && sed -i 's|"/app"|"/workspace"|g' /opt/sandbox-agent/main.py
USER ubuntu
# ------------------------

# Prepend the django-py39 conda environment bin to PATH for commands executed inside the container
ENV PATH=/home/ubuntu/.conda/envs/django-py39/bin:$PATH

# Keep the container alive and run the agent server using the system Python
CMD ["/opt/conda/bin/python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8888", "--log-level", "trace", "--app-dir", "/opt/sandbox-agent"]
EOF
```

Build and push the image:

```bash
export SANDBOX_REPO="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/django-sandbox:v1"
docker build -f Dockerfile.sandbox -t $SANDBOX_REPO .
docker push $SANDBOX_REPO
```

## Configure Orchestration and Execution

Now we deploy the Ray cluster for orchestration and the Sandbox resources for execution.

### 1. Ray Cluster Configuration

Deploy a RayCluster custom resource. Note that your cluster's available resources (like memory, CPU, or GPU type) may differ. Adjust the `resources` requests and limits accordingly.

Run the following command to create `raycluster.yaml`. This uses `cat << EOF` to automatically substitute your environment variables into the manifest:

```bash
cat << EOF > raycluster.yaml
apiVersion: ray.io/v1
kind: RayCluster
metadata:
  name: grpo-cluster
  namespace: default
spec:
  rayVersion: "2.55.1"
  headGroupSpec:
    rayStartParams:
      dashboard-host: "0.0.0.0"
    template:
      spec:
        containers:
        - name: ray-head
          image: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ray-head:v1
          ports:
          - containerPort: 6379
            name: gcs-server
          - containerPort: 8265
            name: dashboard
          - containerPort: 10001
            name: client
          resources:
            limits:
              cpu: "2"
              memory: "8Gi"
            requests:
              cpu: "2"
              memory: "8Gi"
  workerGroupSpecs:
  - groupName: gpu-group
    replicas: 1
    minReplicas: 1
    maxReplicas: 1
    rayStartParams: {}
    template:
      spec:
        containers:
        - name: ray-worker
          image: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/ray-gpu-worker:v1
          resources:
            limits:
              cpu: "12"
              memory: "120Gi"
              nvidia.com/gpu: "1"
            requests:
              cpu: "12"
              memory: "120Gi"
              nvidia.com/gpu: "1"
EOF
```

Apply it:
```bash
kubectl apply -f raycluster.yaml
```

Verify that the cluster is created and running (this may take a few minutes):
```bash
kubectl get raycluster
```

Expected output:
```console
NAME       DESIRED WORKERS   AVAILABLE WORKERS   CPUS   MEMORY   GPUS   STATUS   AGE
rl-cluster   1                 1                                            ready    2m
```

### 2. SandboxRouter Configuration

The SandboxRouter acts as a high-speed HTTP gateway, fielding requests from Ray workers and bridging them instantly to available gVisor pods, bypassing the slower Kubernetes API server pod lifecycle.

Run the following command to create `sandbox_router.yaml`:

```bash
cat << 'EOF' > sandbox_router.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: default
  name: sandbox-claim-manager
rules:
- apiGroups: ["extensions.agents.x-k8s.io"]
  resources: ["sandboxclaims"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["agents.x-k8s.io"]
  resources: ["sandboxes"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: sandbox-claim-manager-binding
  namespace: default
subjects:
- kind: ServiceAccount
  name: default
  namespace: default
roleRef:
  kind: Role
  name: sandbox-claim-manager
  apiGroup: rbac.authorization.k8s.io
---
apiVersion: v1
kind: Service
metadata:
  name: sandbox-router
  namespace: default
spec:
  type: ClusterIP
  selector:
    app: sandbox-router
  ports:
  - name: http
    protocol: TCP
    port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sandbox-router-deployment
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: sandbox-router
  template:
    metadata:
      labels:
        app: sandbox-router
    spec:
      containers:
      - name: router
        image: us-central1-docker.pkg.dev/k8s-staging-images/agent-sandbox/sandbox-router:latest-main
        ports:
        - containerPort: 8080
        env:
        - name: ALLOW_UNAUTHENTICATED_ROUTER
          value: "true"
EOF
```

Apply it:
```bash
kubectl apply -f sandbox_router.yaml
```

Verify the deployment is running:
```bash
kubectl get deployment sandbox-router-deployment
```

Expected output:
```console
NAME                        READY   UP-TO-DATE   AVAILABLE   AGE
sandbox-router-deployment   2/2     2            2           1m
```

### 3. SandboxTemplate and WarmPool Configuration

GKE Agent Sandbox allows instant assignment of isolated, pre-warmed containers using the Sandbox Router. We define a `SandboxTemplate` and a `SandboxWarmPool` to keep pods ready.

Run the following command to create `sandbox_warmpool.yaml` with your environment variables:

```bash
cat << EOF > sandbox_warmpool.yaml
apiVersion: extensions.agents.x-k8s.io/v1alpha1
kind: SandboxTemplate
metadata:
  name: swe-bench-django
  namespace: default
spec:
  podTemplate:
    spec:
      runtimeClassName: gvisor
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      nodeSelector:
        sandbox.gke.io/runtime: gvisor
      tolerations:
      - key: sandbox.gke.io/runtime
        operator: Equal
        value: gvisor
        effect: NoSchedule
      containers:
      - name: sandbox
        image: ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/django-sandbox:v1
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
        resources:
          requests:
            cpu: "2"
            memory: "4Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
---
apiVersion: extensions.agents.x-k8s.io/v1alpha1
kind: SandboxWarmPool
metadata:
  name: swe-bench-django-warmpool
  namespace: default
spec:
  replicas: 10
  sandboxTemplateRef:
    name: swe-bench-django
EOF
```

Apply it:
```bash
kubectl apply -f sandbox_warmpool.yaml
```

Verify the SandboxWarmPool is initialized:
```bash
kubectl get sandboxwarmpool
```

Expected output:
```console
NAME                        READY   AGE
swe-bench-django-warmpool   10      1m
```

### 4. Security Isolation

A NetworkPolicy strictly isolates sandboxes, preventing egress to the GCP Metadata Server, thus preventing IAM token theft.

Run the following command to create `network_policy.yaml`:

```bash
cat << 'EOF' > network_policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: block-metadata-egress
  namespace: default
spec:
  podSelector:
    matchLabels:
      sandbox.gke.io/runtime: gvisor
  policyTypes:
  - Egress
  egress:
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 169.254.169.254/32
EOF
```

Apply the policy:

```bash
kubectl apply -f network_policy.yaml
```

Verify the NetworkPolicy was created:
```bash
kubectl get networkpolicy
```

Expected output:
```console
NAME                 POD-SELECTOR     AGE
block-metadata-egress             sandbox.gke.io/runtime=gvisor     1m
```

## Basic RL Job with SweBench and TRL

Once the cluster and sandboxes are prepared, we can run a GRPO training loop. We will use the `trl` library to orchestrate the GRPO algorithm, and ray remote functions to evaluate the generated code inside the isolated sandboxes.

To make the execution fast for this codelab, we will filter down to a single Django issue. The routing logic below shows how you would select different warmpools for different repositories, which is useful when expanding to the full SWE-bench dataset.

### The Training Script

Run the following command to create `train_trl.py`:

````bash
cat << 'EOF' > train_trl.py
import ray
from k8s_agent_sandbox import SandboxClient
from k8s_agent_sandbox.models import SandboxDirectConnectionConfig
from trl import GRPOConfig, GRPOTrainer
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
import urllib.request
import re

ray.init(ignore_reinit_error=True)

# 1. Define the Ray remote evaluation function
@ray.remote
def evaluate_rollout(code, prompt_data):
    client = SandboxClient(connection_config=SandboxDirectConnectionConfig(api_url="http://sandbox-router.default.svc.cluster.local:8080"))
    
    # Claim a pre-warmed sandbox instantly based on the repo
    repo = prompt_data.get("repo")
    
    # In a full system, you'd route to different warmpools based on repo
    # Here we default to django for our single task
    sandbox = client.create_sandbox(
        template="swe-bench-django",
        warmpool="swe-bench-django-warmpool",
        sandbox_ready_timeout=600
    )
    
    try:
        # Check if the code is correctly formatted
        bash_match = re.search(r"```bash\n(.*?)\n```", code, re.DOTALL)
        if not bash_match:
            return 0.0
            
        script = bash_match.group(1)

        # In a real environment, we would apply the base commit and install here
        # For simplicity, we just execute the script
        import shlex
        script_cmd = f"bash -c {shlex.quote(script)}"
        result = sandbox.commands.run(script_cmd, timeout=60)
        
        # Calculate continuous reward based on test passage ratio
        if result.exit_code == 0:
            return 1.0
        
        # Very simple heuristic reward
        return 0.1
        
    finally:
        # Clean up and release the sandbox back to the pool
        client.delete_sandbox(sandbox.claim_name)

# 2. Define the Reward Function for TRL
def sandbox_reward_func(prompts, completions, **kwargs):
    # Dispatch evaluation to Ray cluster
    futures = [
        evaluate_rollout.remote(completion, {
            "repo": kwargs.get('repo', [])[i] if 'repo' in kwargs else None,
            "base_commit": kwargs.get('base_commit', [])[i] if 'base_commit' in kwargs else None
        }) for i, completion in enumerate(completions)
    ]
    
    # Block and wait for all sandbox evaluations to complete
    rewards = ray.get(futures)
    return rewards

# 3. Setup GRPO Trainer
@ray.remote(num_gpus=1, num_cpus=8)
def train():
    # Load dataset
    dataset = load_dataset("princeton-nlp/SWE-bench_Lite", split="test")
    # Filter to our selected target issue
    dataset = dataset.filter(lambda x: x["instance_id"] == "django__django-15388")
    
    def format_dataset(example):
        files = re.findall(r'^\+\+\+ b/(.+)$', example["patch"], re.MULTILINE)
        target_file = files[0] if files else ""
        
        file_content = ""
        if target_file:
            try:
                github_repo = example["repo"]
                url = f"https://raw.githubusercontent.com/{github_repo}/{example['base_commit']}/{target_file}"
                with urllib.request.urlopen(url) as response:
                    file_content = response.read().decode('utf-8')
            except Exception as e:
                pass
                
        prompt = f"""You are an expert software engineer.
You are given a GitHub issue and the content of the file that contains the bug.
Write an executable bash script that will modify the target file to fix the bug (e.g. using cat << 'EOF' > {target_file} or inline python edits).
Wrap your bash script in ```bash ... ``` tags. Do not output raw python code directly.

Target File: {target_file}

Original File Content:
```python
{file_content}
```

Issue:
{example['problem_statement']}
"""
        return {
            "prompt": prompt,
            "repo": example["repo"],
            "instance_id": example["instance_id"],
            "base_commit": example["base_commit"],
        }
        
    dataset = dataset.map(format_dataset)

    model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    training_args = GRPOConfig(
        output_dir="outputs",
        learning_rate=5e-6,
        max_steps=50,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
    )

    trainer = GRPOTrainer(
        model=model_name,
        processing_class=tokenizer,
        reward_funcs=[sandbox_reward_func],
        args=training_args,
        train_dataset=dataset,
    )

    print("Starting GRPO training with GKE Agent Sandboxes...")
    trainer.train()

def main():
    print("Submitting training job to GPU worker...")
    ray.get(train.remote())

if __name__ == "__main__":
    main()
EOF
````

### Submit the Job to the Cluster

First, port-forward to the Ray Head dashboard and submit the training job from your local machine:

```bash
kubectl port-forward service/grpo-cluster-head-svc 8265:8265 &

ray job submit \
  --address http://localhost:8265 \
  --runtime-env-json '{"working_dir": "."}' \
  -- python train_trl.py
```

### Monitor the Run

You can monitor the progress of your run:

* **Ray Dashboard:** Open `http://localhost:8265` in your browser.
* **Sandbox Claims:** Watch GKE dynamically claim and release sandboxes under gVisor:
  ```bash
  watch -n 1 "kubectl get sandboxclaims,sandboxes,pods"
  ```

## Conclusion

Congratulations! You have successfully configured and executed a high-performance distributed RL training loop securely on GKE Standard using GKE Agent Sandboxes.
