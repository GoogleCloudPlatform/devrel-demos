import os
import sys
import json
from google.cloud import dataplex_v1
from google.api_core.exceptions import NotFound
from google.protobuf.json_format import MessageToDict

# --- Configuration ---
# The Materialized View to analyze is fixed for this step.
TARGET_VIEW = "mv_ga4_user_session_flat"
OUTPUT_FILENAME = "dq_profile_results.json"


def save_to_json_file(content: dict, filename: str):
    """Saves the given dictionary content to a JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            # Use indent=2 for a readable, "pretty-printed" JSON file.
            json.dump(content, f, indent=2, ensure_ascii=False)
        print(f"\n[SUCCESS] Profile results were saved to '{filename}'.")
    except (IOError, TypeError) as e:
        print(f"[ERROR] An error occurred while saving the file: {e}")


def get_latest_successful_job(
    client: dataplex_v1.DataScanServiceClient,
    project_id: str,
    location: str,
    data_scan_id: str
) -> dataplex_v1.DataScanJob | None:
    """Finds and returns the most recently succeeded job for a given data scan."""
    scan_path = client.data_scan_path(project_id, location, data_scan_id)
    print(f"\n[INFO] Looking for the latest successful job for scan '{data_scan_id}'...")

    try:
        # List all jobs for the specified scan, which are ordered most-recent first.
        jobs_pager = client.list_data_scan_jobs(parent=scan_path)

        # Iterate through jobs to find the first one that succeeded.
        for job in jobs_pager:
            if job.state == dataplex_v1.DataScanJob.State.SUCCEEDED:
                return job

        # If no successful job is found after checking all pages.
        return None
    except NotFound:
        print(f"[WARN] No scan history found for '{data_scan_id}'.")
        return None


def main():
    """Main execution function."""
    # --- Load configuration from environment variables ---
    PROJECT_ID = os.environ.get("PROJECT_ID")
    LOCATION = os.environ.get("LOCATION")

    if not all([PROJECT_ID, LOCATION]):
        print("[ERROR] Required environment variables PROJECT_ID or LOCATION are not set.")
        sys.exit(1)

    print(f"[INFO] Using Project: {PROJECT_ID}, Location: {LOCATION}")
    print(f"--- Starting Profile Retrieval for: {TARGET_VIEW} ---")

    # Construct the data_scan_id based on the target view name.
    data_scan_id = f"profile-scan-{TARGET_VIEW.replace('_', '-')}"

    # 1. Initialize Dataplex client and get the latest successful job.
    client = dataplex_v1.DataScanServiceClient()
    latest_job = get_latest_successful_job(client, PROJECT_ID, LOCATION, data_scan_id)

    if not latest_job:
        print(f"\n[ERROR] No successful job record was found for '{data_scan_id}'.")
        print("Please ensure the 'run_dataplex_scans.py' script has completed successfully.")
        return

    job_id_short = latest_job.name.split('/')[-1]
    print(f"[SUCCESS] Found the latest successful job: '{job_id_short}'.")

    # 2. Fetch the full, detailed profile result for the job.
    print(f"[INFO] Retrieving detailed profile results for job '{job_id_short}'...")
    try:
        request = dataplex_v1.GetDataScanJobRequest(
            name=latest_job.name,
            view=dataplex_v1.GetDataScanJobRequest.DataScanJobView.FULL,
        )
        job_with_full_results = client.get_data_scan_job(request=request)
    except Exception as e:
        print(f"[ERROR] Failed to retrieve detailed job results: {e}")
        return

    # 3. Convert the profile result to a dictionary and save it to a JSON file.
    if job_with_full_results.data_profile_result:
        profile_dict = MessageToDict(job_with_full_results.data_profile_result._pb)
        save_to_json_file(profile_dict, OUTPUT_FILENAME)
    else:
        print("[WARN] The job completed, but no data profile result was found within it.")

    print("\n[INFO] Script finished successfully.")


if __name__ == "__main__":
    main()
