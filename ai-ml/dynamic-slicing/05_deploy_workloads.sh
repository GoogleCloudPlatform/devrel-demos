#!/usr/bin/env bash
# ==============================================================================
#  Step 5: 05_deploy_workloads.sh - Deploy Serving and Tuning Workloads
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

# Setup kubectl context wrapper
kubectl() {
  if [ -n "$SERVER" ]; then
    if [ -n "$TOKEN" ]; then
      command kubectl --token="$TOKEN" --server="$SERVER" --insecure-skip-tls-verify=true "$@"
    else
      command kubectl --server="$SERVER" --insecure-skip-tls-verify=true "$@"
    fi
  else
    command kubectl "$@"
  fi
}

echo "===================================================="
# Force a newline
echo " Deploying Workloads to Kueue..."
echo " Namespace: ${NAMESPACE}"
echo "===================================================="

# Create Service Account if not exists (should be created by 04, but double check)
kubectl create serviceaccount gcs-fuse-ksa -n "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
# Note: Annotation should have been done in setup, but we keep it here for reference
# kubectl annotate serviceaccount gcs-fuse-ksa -n ${NAMESPACE} iam.gke.io/gcp-service-account=YOUR_GSA@YOUR_PROJECT.iam.gserviceaccount.com --overwrite

# ------------------------------------------------------------------------------
#  Workload 1: Gemma-3-27B Serving (vLLM on JobSet, 4x4x4 topology, 64 chips)
# ------------------------------------------------------------------------------
echo "Deploying Workload 1: Gemma-3 serving (64 chips)..."
cat <<EOF | kubectl apply -n "${NAMESPACE}" -f -
apiVersion: jobset.x-k8s.io/v1alpha2
kind: JobSet
metadata:
  name: gemma3-serving
  labels:
    kueue.x-k8s.io/queue-name: lq
spec:
  replicatedJobs:
  - name: vllm
    replicas: 1
    template:
      spec:
        parallelism: 16
        completions: 16
        backoffLimit: 0
        template:
          metadata:
            labels:
              app: gemma3-serving
            annotations:
              cloud.google.com/gke-tpu-slice-topology: "4x4x4"
              gke-gcsfuse/volumes: "true"
          spec:
            serviceAccountName: gcs-fuse-ksa
            nodeSelector:
              cloud.google.com/gke-tpu-accelerator: tpu7x
            tolerations:
            - key: "google.com/tpu"
              operator: "Equal"
              value: "present"
              effect: "NoSchedule"
            containers:
            - name: vllm-worker
              image: vllm/vllm-tpu:gemma4
              imagePullPolicy: IfNotPresent
              command:
              - bash
              - -c
              - |
                RANK=\$JOB_COMPLETION_INDEX
                HEAD_NODE="gemma3-serving-vllm-0-0.gemma3-serving-vllm"
                
                if [ "\$RANK" -eq 0 ]; then
                  echo "Starting Ray Head on Rank 0..."
                  ray start --head --port=6379 --block &
                  
                  # Wait for Ray port to open
                  python3 -c "
                  import socket, time
                  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                  while True:
                      try:
                          s.connect(('127.0.0.1', 6379))
                          break
                      except:
                          time.sleep(1)
                  "
                  echo "Ray Head started. Starting vLLM..."
                  
                  vllm serve ${GEMMA3_MODEL_PATH} \
                    --host 0.0.0.0 \
                    --port 8000 \
                    --tensor-parallel-size 64 \
                    --trust-remote-code
                else
                  echo "Starting Ray Worker on Rank \$RANK..."
                  # Wait for head node to be reachable on port 6379
                  python3 -c "
                  import socket, time
                  while True:
                      try:
                          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                          s.connect((''\${HEAD_NODE}'', 6379))
                          s.close()
                          break
                      except Exception as e:
                          print('Waiting for head...', e)
                          time.sleep(2)
                  "
                  ray start --address="\${HEAD_NODE}:6379" --block
                fi
              env:
              - name: HF_TOKEN
                value: "${HF_TOKEN}"
              resources:
                requests:
                  google.com/tpu: 4
                limits:
                  google.com/tpu: 4
              ports:
              - containerPort: 8000
                name: http
              volumeMounts:
              - name: gcs-fuse-volume
                mountPath: /data
            volumes:
            - name: gcs-fuse-volume
              csi:
                driver: gcsfuse.csi.storage.gke.io
                volumeAttributes:
                  bucketName: ${GCS_BUCKET_NAME}
                  mountOptions: "implicit-dirs,file-cache:max-size-mb:-1"
---
apiVersion: v1
kind: Service
metadata:
  name: gemma3-serving-api
  namespace: ${NAMESPACE}
spec:
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  selector:
    jobset.x-k8s.io/jobset-name: gemma3-serving
    jobset.x-k8s.io/replicatedjob-name: vllm
    jobset.x-k8s.io/pod-index: "0"
EOF

# ------------------------------------------------------------------------------
#  Workload 2: Gemma-2-9B Fine-Tuning (MaxText on JobSet, 4x4x4 topology, 64 chips)
# ------------------------------------------------------------------------------
echo "Deploying Workload 2: Gemma-2 fine-tuning benchmark (64 chips)..."
cat <<EOF | kubectl apply -n "${NAMESPACE}" -f -
apiVersion: jobset.x-k8s.io/v1alpha2
kind: JobSet
metadata:
  name: gemma2-tuning
  labels:
    kueue.x-k8s.io/queue-name: lq
spec:
  replicatedJobs:
  - name: maxtext
    replicas: 1
    template:
      spec:
        parallelism: 16
        completions: 16
        backoffLimit: 0
        template:
          metadata:
            labels:
              app: gemma2-tuning
            annotations:
              cloud.google.com/gke-tpu-slice-topology: "4x4x4"
          spec:
            serviceAccountName: gcs-fuse-ksa
            nodeSelector:
              cloud.google.com/gke-tpu-accelerator: tpu7x
            tolerations:
            - key: "google.com/tpu"
              operator: "Equal"
              value: "present"
              effect: "NoSchedule"
            containers:
            - name: maxtext
              image: gcr.io/tpu-prod-env-multipod/maxtext:latest
              imagePullPolicy: IfNotPresent
              command:
              - bash
              - -c
              - |
                # MaxText automatically uses PJRT configured by GKE
                python3 MaxText/train.py MaxText/configs/base.yml \
                  model_name=gemma2-9b \
                  dataset_type=synthetic \
                  steps=100 \
                  per_device_train_batch_size=1 \
                  run_name=gemma2-9b-demo \
                  ici_fsdp_parallelism=16 \
                  base_output_directory=gs://${GCS_BUCKET_NAME}/maxtext-output \
                  checkpoint_period=0
              resources:
                requests:
                  google.com/tpu: 4
                limits:
                  google.com/tpu: 4
EOF

# ------------------------------------------------------------------------------
#  Workload 3: Llama-3-70B Serving (vLLM on JobSet, 4x4x8 topology, 128 chips)
# ------------------------------------------------------------------------------
echo "Deploying Workload 3: Llama-3 serving (128 chips, Super Slicing)..."
cat <<EOF | kubectl apply -n "${NAMESPACE}" -f -
apiVersion: jobset.x-k8s.io/v1alpha2
kind: JobSet
metadata:
  name: llama3-serving
  labels:
    kueue.x-k8s.io/queue-name: lq
spec:
  replicatedJobs:
  - name: vllm
    replicas: 1
    template:
      spec:
        parallelism: 32
        completions: 32
        backoffLimit: 0
        template:
          metadata:
            labels:
              app: llama3-serving
            annotations:
              cloud.google.com/gke-tpu-slice-topology: "4x4x8"
              gke-gcsfuse/volumes: "true"
          spec:
            serviceAccountName: gcs-fuse-ksa
            nodeSelector:
              cloud.google.com/gke-tpu-accelerator: tpu7x
            tolerations:
            - key: "google.com/tpu"
              operator: "Equal"
              value: "present"
              effect: "NoSchedule"
            containers:
            - name: vllm-worker
              image: vllm/vllm-tpu:gemma4 # Using same image, assuming llama support
              imagePullPolicy: IfNotPresent
              command:
              - bash
              - -c
              - |
                RANK=\$JOB_COMPLETION_INDEX
                HEAD_NODE="llama3-serving-vllm-0-0.llama3-serving-vllm"
                
                if [ "\$RANK" -eq 0 ]; then
                  echo "Starting Ray Head on Rank 0..."
                  ray start --head --port=6379 --block &
                  
                  # Wait for Ray port to open
                  python3 -c "
                  import socket, time
                  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                  while True:
                      try:
                          s.connect(('127.0.0.1', 6379))
                          break
                      except:
                          time.sleep(1)
                  "
                  echo "Ray Head started. Starting vLLM..."
                  
                  vllm serve ${LLAMA3_MODEL_PATH} \
                    --host 0.0.0.0 \
                    --port 8000 \
                    --tensor-parallel-size 128 \
                    --trust-remote-code
                else
                  echo "Starting Ray Worker on Rank \$RANK..."
                  # Wait for head node to be reachable on port 6379
                  python3 -c "
                  import socket, time
                  while True:
                      try:
                          s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                          s.connect((''\${HEAD_NODE}'', 6379))
                          s.close()
                          break
                      except Exception as e:
                          print('Waiting for head...', e)
                          time.sleep(2)
                  "
                  ray start --address="\${HEAD_NODE}:6379" --block
                fi
              env:
              - name: HF_TOKEN
                value: "${HF_TOKEN}"
              resources:
                requests:
                  google.com/tpu: 4
                limits:
                  google.com/tpu: 4
              ports:
              - containerPort: 8000
                name: http
              volumeMounts:
              - name: gcs-fuse-volume
                mountPath: /data
            volumes:
            - name: gcs-fuse-volume
              csi:
                driver: gcsfuse.csi.storage.gke.io
                volumeAttributes:
                  bucketName: ${GCS_BUCKET_NAME}
                  mountOptions: "implicit-dirs,file-cache:max-size-mb:-1"
---
apiVersion: v1
kind: Service
metadata:
  name: llama3-serving-api
  namespace: ${NAMESPACE}
spec:
  ports:
  - name: http
    port: 8000
    targetPort: 8000
  selector:
    jobset.x-k8s.io/jobset-name: llama3-serving
    jobset.x-k8s.io/replicatedjob-name: vllm
    jobset.x-k8s.io/pod-index: "0"
EOF

echo "===================================================="
# Force a newline
echo " All workloads submitted to Kueue!"
echo " Use 'kubectl get workloads -n ${NAMESPACE}' to monitor."
echo "===================================================="
