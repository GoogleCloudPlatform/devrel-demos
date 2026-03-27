#!/bin/bash
# 04 - Script to construct and submit the execution job via Ray Job Submit

. ./env.sh

if [ -z "$HF_TOKEN" ]; then
    echo "Error: Hugging Face Token (HF_TOKEN) is not set in env.sh."
    exit 1
fi

WANDB_ENABLED="True"
if [ -z "$WANDB_API_KEY" ]; then
    echo "Warning: WANDB_API_KEY not provided. Disabling WandB logging."
    WANDB_ENABLED="False"
fi

RUN_ID="test1"
WORKLOAD="nemo-rl-grpo-${RUN_ID}"
MAX_STEPS=20
NUM_GENERATIONS=8

echo "Configuration (GPU KubeRay Submission):"
echo "  Cluster: $CLUSTER_NAME"
echo "  Nodes: $NUM_NODES"
echo "  Workload Name: $WORKLOAD"

# =========================================================================
# DYNAMIC FILE GENERATION 
# =========================================================================
echo "Generating execution script..."

# The Launch Command File
cat << EOF > run_nemo_rl.sh
#!/bin/bash
set -ex

# Override job runtime conflicts (NeMo-RL passes os.environ to ray.init)
export RAY_OVERRIDE_JOB_RUNTIME_ENV=1

echo "--- Running on Ray Cluster ---"
cd /opt/nemo-rl

# Ensure directories exist on the high-speed Lustre drive
mkdir -p /lustre/huggingface_cache
mkdir -p /lustre/nemo_rl_qwen_72b_ds_cp

echo "Launching NeMo-RL GRPO training..."
uv run python examples/run_grpo_math.py \\
  --config examples/configs/grpo_math_70B_megatron.yaml \\
  policy.model_name='Qwen/Qwen2.5-72B-Instruct' \\
  policy.megatron_cfg.converter_type='Qwen2ForCausalLM' \\
  logger.wandb_enabled=${WANDB_ENABLED} \\
  cluster.num_nodes=${NUM_NODES} \\
  cluster.gpus_per_node=${GPUS_PER_NODE} \\
  logger.wandb.name='${WORKLOAD}' \\
  grpo.max_num_steps=${MAX_STEPS} \\
  grpo.num_generations_per_prompt=${NUM_GENERATIONS} \\
  grpo.num_prompts_per_step=32 \\
  policy.train_global_batch_size=256 \\
  checkpointing.enabled=True \\
  checkpointing.save_period=2 \\
  checkpointing.keep_top_k=2 \\
  checkpointing.metric_name=null \\
  checkpointing.checkpoint_dir=/lustre/nemo_rl_qwen_72b_ds_cp/${WORKLOAD} \\
  data.dataset_name='DeepScaler'
EOF
chmod +x run_nemo_rl.sh

# =========================================================================

echo "Connecting to KubeRay cluster to find Ray Head Service..."
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID} > /dev/null 2>&1

RAY_HEAD_SVC=$(kubectl get svc -l ray.io/node-type=head -n default -o jsonpath='{.items[0].metadata.name}')

if [ -z "$RAY_HEAD_SVC" ]; then
    echo "Error: Could not find Ray Head service. Ensure cluster is up."
    exit 1
fi

OCCUPIED_PID=$(lsof -t -i :8265 2>/dev/null)
if [ ! -z "$OCCUPIED_PID" ]; then
    kill -9 $OCCUPIED_PID 2>/dev/null || sudo kill -9 $OCCUPIED_PID 2>/dev/null
    sleep 2
fi

echo "Establishing port-forward to Ray Dashboard..."
kubectl port-forward -n default svc/$RAY_HEAD_SVC 8265:8265 > /dev/null 2>&1 &
PF_PID=$!
sleep 5

export RAY_ADDRESS="http://127.0.0.1:8265"

# Setup runtime environment JSON
RUNTIME_ENV_FILE="/tmp/ray_runtime_env_nemo.json"
cat <<EOF > "${RUNTIME_ENV_FILE}"
{
  "env_vars": {
    "HF_TOKEN": "${HF_TOKEN}",
    "WANDB_API_KEY": "${WANDB_API_KEY}",
    "HF_HOME": "/lustre/huggingface_cache",
    "GLOO_SOCKET_IFNAME": "eth0",
    "NCCL_SOCKET_IFNAME": "eth0"
  }
}
EOF

echo "Submitting NeMo-RL job to Ray Head Node..."
ray job submit \
    --submission-id "${WORKLOAD}" \
    --working-dir . \
    --runtime-env "${RUNTIME_ENV_FILE}" \
    -- bash run_nemo_rl.sh

SUBMIT_STATUS=$?
kill $PF_PID

if [ $SUBMIT_STATUS -eq 0 ]; then
    echo "Workload submitted! Use 'ray job logs -f ${WORKLOAD}' to track progress."
else
    echo "Workload submission failed."
fi
