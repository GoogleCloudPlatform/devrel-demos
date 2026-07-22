#!/usr/bin/env bash
# ==============================================================================
#  Step 3.5: 04_deploy_envoy_router.sh - Deploy high-compute Envoy targeting Prefill Cluster
# ==============================================================================
set -e

if [ ! -f "./env.sh" ]; then
    echo "Error: env.sh not found. Please run 01_setup_env.sh first."
    exit 1
fi
. ./env.sh

echo "===================================================="
echo " Deploying high-compute Envoy load balancer on GKE..."
echo " Targeting Prefill Service: http://vllm-prefill-service:8200"
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

# 1. Recreate static Envoy config file targeting Prefill service
cat <<EOF > envoy.yaml
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address:
        address: 0.0.0.0
        port_value: 8000
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          route_config:
            name: local_route
            virtual_hosts:
            - name: local_service
              domains: ["*"]
              routes:
              - match:
                  prefix: "/"
                route:
                  cluster: gemma_serving_cluster
                  timeout: 300s
                  hash_policy:
                  - header:
                      header_name: "X-Session-Id"
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: gemma_serving_cluster
    connect_timeout: 5s
    type: STRICT_DNS
    lb_policy: RING_HASH
    ring_hash_lb_config:
      minimum_ring_size: 1024
    dns_lookup_family: V4_ONLY
    load_assignment:
      cluster_name: gemma_serving_cluster
      endpoints:
      - lb_endpoints:
        - endpoint:
            address:
              socket_address:
                address: vllm-prefill-service.disagg-serving.svc.cluster.local
                port_value: 8200
EOF

# 2. Recreate ConfigMap inside GKE
kubectl delete configmap envoy-config -n "${NAMESPACE}" --ignore-not-found || true
kubectl create configmap envoy-config --from-file=envoy.yaml=envoy.yaml -n "${NAMESPACE}"

# 3. Deploy Envoy Pod allocated up to 7 CPUs strictly on CPU node pool VM
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: vllm-router-service
  namespace: ${NAMESPACE}
  labels:
    app: envoy-router
spec:
  type: ClusterIP
  selector:
    app: envoy-router
  ports:
  - name: http
    port: 8000
    targetPort: 8000
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: envoy-router
  namespace: ${NAMESPACE}
  labels:
    app: envoy-router
spec:
  replicas: 1
  selector:
    matchLabels:
      app: envoy-router
  template:
    metadata:
      labels:
        app: envoy-router
    spec:
      nodeSelector:
        cloud.google.com/gke-nodepool: default-pool
      containers:
      - name: envoy
        image: envoyproxy/envoy:v1.30.1
        imagePullPolicy: IfNotPresent
        command:
        - envoy
        - -c
        - /etc/envoy/envoy.yaml
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: "0.5"
            memory: "1Gi"
          limits:
            cpu: "3.5"
            memory: "4Gi"
        volumeMounts:
        - name: config-volume
          mountPath: /etc/envoy
      volumes:
      - name: config-volume
        configMap:
          name: envoy-config
EOF

echo "===================================================="
echo " Envoy Load Balancer successfully deployed!"
echo "===================================================="
