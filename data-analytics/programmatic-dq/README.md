# Programmatic Data Quality with Dataplex and Generative AI - Sample Code

This repository contains the sample code and supporting files for the [Programmatic Data Quality with Dataplex and Generative AI](https://codelabs.developers.google.com/programmatic-dq) codelab.

Please follow the codelab for detailed instructions on how to set up your environment and use these files.

## Files in this repository

*   `1_run_dataplex_scans.py`: A Python script that programmatically creates and runs Dataplex data profile scans for the Materialized Views.
*   `2_dq_profile_save.py`: A Python script that finds the latest successful profile scan and saves the results to a local JSON file (`dq_profile_results.json`) to be used as input for the Gemini CLI.
*   `mv_ga4_user_session_flat.sql`: The SQL template for creating the flattened user session materialized view.
*   `mv_ga4_ecommerce_transactions.sql`: The SQL template for creating the flattened e-commerce transactions materialized view.
*   `mv_ga4_ecommerce_items.sql`: The SQL template for creating the flattened e-commerce items materialized view.
*   `sample_rule.yaml`: An example of a Dataplex-compliant data quality rule file, used for reference when prompting the AI.