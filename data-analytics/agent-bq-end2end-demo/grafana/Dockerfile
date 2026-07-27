FROM grafana/grafana-oss:latest

USER root

# Install dependencies (curl, python3, and bash are required for the gcloud CLI installer)
RUN apk add --no-cache curl python3 bash tar

# Install Google Cloud CLI (gcloud) programmatically
RUN curl -sSL https://sdk.cloud.google.com | bash -s -- --disable-prompts --install-dir=/opt

# Add gcloud CLI to system PATH
ENV PATH="/opt/google-cloud-sdk/bin:${PATH}"

# Create standard home directory config paths and ensure grafana user owns them
RUN mkdir -p /home/grafana/.config/gcloud && \
    chown -R 472:472 /home/grafana && \
    chown -R 472:472 /opt/google-cloud-sdk

USER grafana
