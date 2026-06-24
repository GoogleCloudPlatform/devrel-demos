#!/usr/bin/env bash
# ==============================================================================
#  Step 3: 03_deploy_disagg_mesh.sh - Deploy Prefill and Decode disaggregated Mesh
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "===================================================="
echo " Deploying Prefill (${PREFILL_REPLICAS}) and Decode (${DECODE_REPLICAS}) TPU Mesh..."
echo " Namespace: ${NAMESPACE}"
echo " Model: ${SERVED_MODEL_NAME}"
echo "===================================================="

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

# Recreate namespace
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Create Kubernetes Service Account and annotate for GCP GSA Workload Identity
echo "Configuring GCS Fuse Service Account and Workload Identity annotations..."
kubectl create serviceaccount gcs-fuse-ksa -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
kubectl annotate serviceaccount gcs-fuse-ksa -n ${NAMESPACE} iam.gke.io/gcp-service-account=gemma-gcs-gsa@dx-supercomputer-testing.iam.gserviceaccount.com --overwrite


# Deploy GKE DRA ResourceClaimTemplate for networking
cat <<EOF | kubectl apply -n ${NAMESPACE} -f -
apiVersion: resource.k8s.io/v1
kind: ResourceClaimTemplate
metadata:
  name: tpu-netdev-claim-template
spec:
  spec:
    devices:
      requests:
      - name: req-netdev
        exactly:
          deviceClassName: netdev.google.com
EOF

# Base64-encoded uncorrupted patch script payload
PATCH_PAYLOAD="aW1wb3J0IHN5cywgdHlwZXMsIHJlLCB0cmFjZWJhY2sKaWYgX19uYW1lX18gPT0gJ19fbWFpbl9fJzoKICAgIHRyeToKICAgICAgICBpbXBvcnQgdmxsbS5jb25maWcudmxsbQogICAgICAgIHRhcmdldF9maWxlID0gdmxsbS5jb25maWcudmxsbS5fX2ZpbGVfXwogICAgICAgIHdpdGggb3Blbih0YXJnZXRfZmlsZSwgJ3InKSBhcyBmOgogICAgICAgICAgICBjb2RlID0gZi5yZWFkKCkKICAgICAgICBjb2RlID0gcmUuc3ViKHInYXNzZXJ0XHMrc2VsZlwuc2NoZWR1bGVyX2NvbmZpZ1wubG9uZ19wcmVmaWxsX3Rva2VuX3RocmVzaG9sZFxzKj49Ki4qJywgJ3Bhc3MnLCBjb2RlKQogICAgICAgIGNvZGUgPSByZS5zdWIocidhc3NlcnRccytub3RccytzZWxmXC5zY2hlZHVsZXJfY29uZmlnXC5kaXNhYmxlX2NodW5rZWRfbW1faW5wdXRccyosXHMqXCgnLCAnaWYgRmFsc2U6ICgnLCBjb2RlKQogICAgICAgIG1vZCA9IHN5cy5tb2R1bGVzWyJ2bGxtLmNvbmZpZy52bGxtIl0KICAgICAgICBleGVjKGNvZGUsIG1vZC5fX2RpY3RfXykKICAgICAgICBmcm9tIHZsbG0uZW50cnlwb2ludHMuY2xpLm1haW4gaW1wb3J0IG1haW4KICAgICAgICBtYWluKCkKICAgIGV4Y2VwdCBFeGNlcHRpb24gYXMgZToKICAgICAgICBwcmludCgiPSIqODAsIGZpbGU9c3lzLnN0ZGVycikKICAgICAgICBwcmludCgiQ09NUElMRVIgQ1JBU0ggRVhDRVBUSU9OOiIsIGZpbGU9c3lzLnN0ZGVycikKICAgICAgICBwcmludCgiPSIqODAsIGZpbGU9c3lzLnN0ZGVycikKICAgIHRyYWNlYmFjay5wcmludF9leGMoZmlsZT1zeXMuc3RkZXJyKQogICAgcHJpbnQoIj0iKjgwLCBmaWxlPXN5cy5zdGRlcnIpCiAgICBzeXMuZXhpdCgxKQ=="

# 1. Deploy PREFILL Cluster (ROLE: kv_producer)
echo "Deploying Prefill cluster (${PREFILL_REPLICAS} replicas)..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-prefill
  namespace: ${NAMESPACE}
spec:
  strategy:
    type: Recreate
  replicas: ${PREFILL_REPLICAS}
  selector:
    matchLabels:
      app: vllm-prefill
  template:
    metadata:
      labels:
        app: vllm-prefill
      annotations:
        gke-gcsfuse/volumes: "true"
    spec:
      serviceAccountName: gcs-fuse-ksa
      nodeSelector:
        cloud.google.com/gke-tpu-accelerator: tpu7x
        cloud.google.com/gke-tpu-topology: 2x2x1
        gke.networks.io/accelerator-network-profile: auto
      resourceClaims:
      - name: netdev-interface
        resourceClaimTemplateName: tpu-netdev-claim-template
      containers:
      - name: vllm-prefill
        image: vllm/vllm-tpu:gemma4
        imagePullPolicy: Always
        command:
        - "bash"
        - "-c"
        - |
          KV_CONFIG="{\"kv_connector\":\"TPUConnector\", \"kv_connector_module_path\" : \"tpu_inference.distributed.tpu_connector\", \"kv_role\":\"kv_producer\", \"kv_ip\" : \"\$POD_IP\"}"
          echo "KV_CONFIG=\$KV_CONFIG"
          echo '${PATCH_PAYLOAD}' | base64 -d > /tmp/patch_vllm.py
          python3 /tmp/patch_vllm.py serve /data --port 8200 --served-model-name '${SERVED_MODEL_NAME}' --tensor-parallel-size 4 --max-model-len 4096 --gpu-memory-utilization 0.80 --load-format runai_streamer --dtype bfloat16 --enforce-eager --mamba-cache-mode none --long-prefill-token-threshold 0 --max-num-batched-tokens 8192 --enable-chunked-prefill --enable-prefix-caching --kv-transfer-config "\${KV_CONFIG}" --trust-remote-code
        env:
        - name: HF_TOKEN
          value: "${HF_TOKEN}"
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: TPU_SIDE_CHANNEL_PORT
          value: "9600"
        - name: TPU_KV_TRANSFER_PORT
          value: "9100"
        - name: VLLM_ENGINE_ITERATION_TIMEOUT_S
          value: "60"
        ports:
        - containerPort: 8200
          name: vllm
        - containerPort: 9100
          name: tpu-kv
        - containerPort: 9600
          name: tpu-coord
        resources:
          requests:
            google.com/tpu: 4
          limits:
            google.com/tpu: 4
          claims:
          - name: netdev-interface
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
  name: vllm-prefill-service
  namespace: ${NAMESPACE}
spec:
  clusterIP: None
  selector:
    app: vllm-prefill
  ports:
  - name: http
    protocol: TCP
    port: 8200
    targetPort: 8200
  - name: tpu-kv
    protocol: TCP
    port: 9100
    targetPort: 9100
  - name: tpu-coord
    protocol: TCP
    port: 9600
    targetPort: 9600
EOF

# 2. Deploy DECODE Cluster (ROLE: kv_consumer)
echo "Deploying Decode cluster (${DECODE_REPLICAS} replicas)..."
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-decode
  namespace: ${NAMESPACE}
spec:
  strategy:
    type: Recreate
  replicas: ${DECODE_REPLICAS}
  selector:
    matchLabels:
      app: vllm-decode
  template:
    metadata:
      labels:
        app: vllm-decode
      annotations:
        gke-gcsfuse/volumes: "true"
    spec:
      serviceAccountName: gcs-fuse-ksa
      nodeSelector:
        cloud.google.com/gke-tpu-accelerator: tpu7x
        cloud.google.com/gke-tpu-topology: 2x2x1
        gke.networks.io/accelerator-network-profile: auto
      resourceClaims:
      - name: netdev-interface
        resourceClaimTemplateName: tpu-netdev-claim-template
      containers:
      - name: vllm-decode
        image: vllm/vllm-tpu:gemma4
        imagePullPolicy: Always
        command:
        - "bash"
        - "-c"
        - |
          KV_CONFIG="{\"kv_connector\":\"TPUConnector\", \"kv_connector_module_path\" : \"tpu_inference.distributed.tpu_connector\", \"kv_role\":\"kv_consumer\", \"kv_ip\" : \"\$POD_IP\"}"
          echo "KV_CONFIG=\$KV_CONFIG"
          echo '${PATCH_PAYLOAD}' | base64 -d > /tmp/patch_vllm.py
          python3 /tmp/patch_vllm.py serve /data --port 8200 --served-model-name '${SERVED_MODEL_NAME}' --tensor-parallel-size 4 --max-model-len 4096 --gpu-memory-utilization 0.90 --load-format runai_streamer --dtype bfloat16 --enforce-eager --mamba-cache-mode none --long-prefill-token-threshold 0 --max-num-seqs 128 --enable-prefix-caching --kv-transfer-config "\${KV_CONFIG}" --trust-remote-code
        env:
        - name: HF_TOKEN
          value: "${HF_TOKEN}"
        - name: POD_IP
          valueFrom:
            fieldRef:
              fieldPath: status.podIP
        - name: TPU_SIDE_CHANNEL_PORT
          value: "9600"
        - name: TPU_KV_TRANSFER_PORT
          value: "9100"
        - name: VLLM_ENGINE_ITERATION_TIMEOUT_S
          value: "60"
        ports:
        - containerPort: 8200
          name: vllm
        - containerPort: 9100
          name: tpu-kv
        - containerPort: 9600
          name: tpu-coord
        resources:
          requests:
            google.com/tpu: 4
          limits:
            google.com/tpu: 4
          claims:
          - name: netdev-interface
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
  name: vllm-decode-service
  namespace: ${NAMESPACE}
spec:
  clusterIP: None
  selector:
    app: vllm-decode
  ports:
  - name: http
    protocol: TCP
    port: 8200
    targetPort: 8200
  - name: tpu-kv
    protocol: TCP
    port: 9100
    targetPort: 9100
  - name: tpu-coord
    protocol: TCP
    port: 9600
    targetPort: 9600
EOF

echo "===================================================="
echo " Prefill and Decode Disaggregated Mesh successfully deployed!"
echo "===================================================="
