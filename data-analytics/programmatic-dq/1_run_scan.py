import os
import sys
import time
from google.cloud import dataplex_v1
from google.api_core.exceptions import AlreadyExists


def create_and_run_scan(
    client: dataplex_v1.DataScanServiceClient,
    project_id: str,
    location: str,
    data_scan_id: str,
    target_resource: str,
) -> dataplex_v1.DataScanJob | None:
    """
    Creates and runs a single data profile scan.
    Returns the executed Job object without waiting for completion.
    """
    parent = client.data_scan_path(project_id, location, data_scan_id).rsplit('/', 2)[0]
    scan_path = client.data_scan_path(project_id, location, data_scan_id)

    # 1. Create Data Scan (skips if it already exists)
    try:
        data_scan = dataplex_v1.DataScan()
        data_scan.data.resource = target_resource
        data_scan.data_profile_spec = dataplex_v1.DataProfileSpec()

        print(f"[INFO] Creating data scan '{data_scan_id}'...")
        client.create_data_scan(
            parent=parent,
            data_scan=data_scan,
            data_scan_id=data_scan_id
        ).result()  # Wait for creation to complete
        print(f"[SUCCESS] Data scan '{data_scan_id}' created.")
    except AlreadyExists:
        print(f"[INFO] Data scan '{data_scan_id}' already exists. Skipping creation.")
    except Exception as e:
        print(f"[ERROR] Error creating data scan '{data_scan_id}': {e}")
        return None

    # 2. Run Data Scan
    try:
        print(f"[INFO] Running data scan '{data_scan_id}'...")
        run_response = client.run_data_scan(name=scan_path)
        print(f"[SUCCESS] Job started for '{data_scan_id}'. Job ID: {run_response.job.name.split('/')[-1]}")
        return run_response.job
    except Exception as e:
        print(f"[ERROR] Error running data scan '{data_scan_id}': {e}")
        return None


def main():
    """Main execution function"""
    # --- Load configuration from environment variables ---
    PROJECT_ID = os.environ.get("PROJECT_ID")
    LOCATION = os.environ.get("LOCATION")
    DATASET_ID = os.environ.get("DATASET_ID")

    if not all([PROJECT_ID, LOCATION, DATASET_ID]):
        print("[ERROR] One or more required environment variables are not set.")
        print("Please ensure PROJECT_ID, LOCATION, and DATASET_ID are exported in your shell.")
        sys.exit(1)

    print(f"[INFO] Using Project: {PROJECT_ID}, Location: {LOCATION}, Dataset: {DATASET_ID}")

    # List of Materialized Views to profile
    TARGET_VIEWS = [
        "mv_ga4_user_session_flat",
        "mv_ga4_ecommerce_transactions",
        "mv_ga4_ecommerce_items"
    ]
    # ----------------------------------------------------

    client = dataplex_v1.DataScanServiceClient()
    running_jobs = []

    # 1. Create and run jobs for all target views
    print("\n--- Starting Data Profiling Job Creation and Execution ---")
    for view_name in TARGET_VIEWS:
        data_scan_id = f"profile-scan-{view_name.replace('_', '-')}"
        target_resource = f"//bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/{DATASET_ID}/tables/{view_name}"

        job = create_and_run_scan(client, PROJECT_ID, LOCATION, data_scan_id, target_resource)
        if job:
            running_jobs.append(job)
    print("-------------------------------------------------------\n")

    if not running_jobs:
        print("[ERROR] No jobs were started. Exiting.")
        return

    # 2. Poll for all jobs to complete
    print("--- Monitoring job completion status (checking every 30 seconds) ---")
    completed_jobs = {}

    while running_jobs:
        jobs_to_poll_next = []

        print(f"\n[STATUS] Checking status for {len(running_jobs)} running jobs...")

        for job in running_jobs:
            job_id_short = job.name.split('/')[-1][:13] 
            try:
                updated_job = client.get_data_scan_job(name=job.name)
                state = updated_job.state

                if state in (dataplex_v1.DataScanJob.State.RUNNING, dataplex_v1.DataScanJob.State.PENDING, dataplex_v1.DataScanJob.State.CANCELING):
                    print(f"  - Job {job_id_short}... Status: {state.name}")
                    jobs_to_poll_next.append(updated_job) 
                else:
                    print(f"  - Job {job_id_short}... Status: {state.name} (Complete)")
                    completed_jobs[job.name] = updated_job

            except Exception as e:
                print(f"[ERROR] Could not check status for job {job_id_short}: {e}")

        running_jobs = jobs_to_poll_next

        if running_jobs:
            time.sleep(30)

    # 3. Print final results
    print("\n--------------------------------------------------")
    print("[SUCCESS] All data profiling jobs have completed.")
    print("\nFinal Job Status Summary:")
    for job_name, job in completed_jobs.items():
        job_id_short = job_name.split('/')[-1][:13]
        print(f"  - Job {job_id_short}: {job.state.name}")
        if job.state == dataplex_v1.DataScanJob.State.FAILED:
            print(f"    - Failure Message: {job.message}")

    print("\nNext step: Analyze the profile results and generate quality rules.")


if __name__ == "__main__":
    main()
