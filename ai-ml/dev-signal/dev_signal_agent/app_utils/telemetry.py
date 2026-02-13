import os
import logging

def setup_telemetry():
    """Configures OpenTelemetry to export logs to Google Cloud."""
    bucket = os.environ.get("LOGS_BUCKET_NAME")
    if bucket:
        # These specific environment variables tell the ADK to hook into OpenTelemetry
        # and send the data to the specified GCS bucket or Cloud Trace.
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
        os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_UPLOAD_BASE_PATH", f"gs://{bucket}/completions")
    return bucket

