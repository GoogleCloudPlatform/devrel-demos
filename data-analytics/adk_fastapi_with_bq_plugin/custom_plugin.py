import os
from google.adk.plugins.bigquery_agent_analytics_plugin import BigQueryAgentAnalyticsPlugin

class CustomBigQueryPlugin(BigQueryAgentAnalyticsPlugin):
    def __init__(self, *args, **kwargs):
        # Retrieve parameters from OS environment variables with sensible defaults
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
        dataset_id = os.getenv("BQ_DATASET_ID", "your_dataset_id")
        table_id = os.getenv("BQ_TABLE_ID", "your_table_id")

        super().__init__(
            project_id=project_id,
            dataset_id=dataset_id,
            table_id=table_id
        )
