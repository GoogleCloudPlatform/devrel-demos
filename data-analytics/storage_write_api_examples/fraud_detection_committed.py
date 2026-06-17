import time
import uuid
import sys
import random
from google.cloud import bigquery
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types
from google.protobuf import descriptor_pb2
from google.api_core.exceptions import NotFound, GoogleAPICallError
import schema_pb2

def configure_target(default_table):
    import argparse
    import os
    import google.auth

    parser = argparse.ArgumentParser(description="BigQuery Storage Write API - Committed Mode Demo")
    parser.add_argument("--project", help="GCP Project ID", default=os.getenv("GOOGLE_CLOUD_PROJECT"))
    parser.add_argument("--dataset", help="BigQuery Dataset ID", default="bq_storage_codelab")
    parser.add_argument("--table", help="BigQuery Table ID", default=default_table)
    args, _ = parser.parse_known_args()

    project_id = args.project
    dataset_id = args.dataset
    table_id = args.table

    if not project_id:
        try:
            _, default_project = google.auth.default()
            project_id = default_project
        except Exception:
            pass

    if sys.stdin.isatty():
        project_id = project_id or "YOUR_PROJECT_ID"
        while True:
            print(f"\n[!] Target Location Check:")
            print(f"    GCP Project: {project_id}")
            print(f"    BigQuery Dataset: {dataset_id}")
            print(f"    BigQuery Table: {table_id}")
            
            try:
                choice = input("\n[?] Proceed with these settings? [Y/n]: ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                print("\n[-] Configuration canceled.")
                sys.exit(1)
                
            if choice in ("", "y", "yes"):
                if project_id == "YOUR_PROJECT_ID" or not project_id:
                    print("[-] Error: GCP Project ID is required. Run with --project or set GOOGLE_CLOUD_PROJECT.")
                    sys.exit(1)
                return project_id, dataset_id, table_id
            
            try:
                user_project = input(f"Enter GCP Project ID [{project_id}]: ").strip()
                if user_project:
                    project_id = user_project
                    
                user_dataset = input(f"Enter Dataset ID [{dataset_id}]: ").strip()
                if user_dataset:
                    dataset_id = user_dataset
                    
                user_table = input(f"Enter Table ID [{table_id}]: ").strip()
                if user_table:
                    table_id = user_table
            except (KeyboardInterrupt, EOFError):
                print("\n[-] Configuration canceled.")
                sys.exit(1)
    else:
        if not project_id:
            print("[-] Error: GCP Project ID not specified. Set GOOGLE_CLOUD_PROJECT or pass --project.", file=sys.stderr)
            sys.exit(1)

    return project_id, dataset_id, table_id

def check_or_create_table(bq_client, dataset_id, table_id, expected_schema):
    dataset_ref = bq_client.dataset(dataset_id)
    try:
        bq_client.get_dataset(dataset_ref)
    except NotFound:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        bq_client.create_dataset(dataset)
        print(f"[+] Created dataset '{dataset_id}'.")

    table_ref = dataset_ref.table(table_id)
    try:
        table = bq_client.get_table(table_ref)
        existing_fields = {field.name: field.field_type for field in table.schema}
        for expected_field in expected_schema:
            if expected_field.name not in existing_fields:
                print(f"[-] Error: Table '{table_id}' already in use with a conflicting schema (missing field '{expected_field.name}').")
                sys.exit(1)
            if existing_fields[expected_field.name] != expected_field.field_type:
                print(f"[-] Error: Table '{table_id}' already in use with a conflicting schema (field '{expected_field.name}' type mismatch).")
                sys.exit(1)
        print(f"[+] Using existing table '{table_id}'.")
    except NotFound:
        table = bigquery.Table(table_ref, schema=expected_schema)
        bq_client.create_table(table)
        print(f"[+] Created table '{table_id}'.")

def generate_mock_transaction(seq):
    txn = schema_pb2.TransactionEvent()
    txn.transaction_id = str(uuid.uuid4())
    txn.card_number_hash = f"sha256_{uuid.uuid4().hex[:16]}"
    txn.amount = round(random.uniform(5.0, 2500.0), 2)
    txn.merchant_id = f"merch_{random.randint(1000, 9999)}"
    txn.timestamp = str(int(time.time() * 1000000))
    txn.fraud_risk_score = round(random.uniform(0.01, 0.99), 2)
    
    if txn.fraud_risk_score > 0.85:
        txn.alert_level = "CRITICAL"
    elif txn.fraud_risk_score > 0.60:
        txn.alert_level = "MEDIUM"
    else:
        txn.alert_level = "LOW"
        
    return txn

def run_committed_writer(project_id, dataset_id, table_id):
    client = bigquery_storage_v1.BigQueryWriteClient()
    parent = client.table_path(project_id, dataset_id, table_id)
    write_stream_path = f"{parent}/streams/_default"

    proto_descriptor = descriptor_pb2.DescriptorProto()
    schema_pb2.TransactionEvent.DESCRIPTOR.CopyToProto(proto_descriptor)

    def make_request(txn_bytes):
        proto_rows = types.ProtoRows(serialized_rows=[txn_bytes])
        proto_data = types.AppendRowsRequest.ProtoData(
            writer_schema=types.ProtoSchema(proto_descriptor=proto_descriptor),
            rows=proto_rows
        )
        return types.AppendRowsRequest(
            write_stream=write_stream_path,
            proto_rows=proto_data
        )

    from queue import Queue
    request_queue = Queue()

    def request_generator():
        while True:
            req = request_queue.get()
            if req is None:
                break
            yield req

    print("\n[*] Starting Committed Mode Stream (Default Stream)...")
    print("[*] Press Ctrl+C to terminate.")

    try:
        responses = client.append_rows(request_generator())
    except GoogleAPICallError as e:
        print(f"[-] Failed to establish write stream connection: {e}")
        return

    seq_offset = 0
    try:
        while True:
            txn = generate_mock_transaction(seq_offset)
            print(f"\n[+] Processing Transaction #{seq_offset}")
            print(f"    ID: {txn.transaction_id} | Risk Score: {txn.fraud_risk_score} | Level: {txn.alert_level}")

            request = make_request(txn.SerializeToString())
            request_queue.put(request)

            try:
                response = next(responses)
                if response.error.code != 0:
                    print(f"[-] Write Error: {response.error.message}")
                else:
                    print(f"[+] Successfully ingested transaction #{seq_offset}")
                    seq_offset += 1
            except StopIteration:
                print("[-] Stream connection closed by the server.")
                break
            except Exception as e:
                print(f"[-] Ingestion error on stream: {e}")
                break

            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[+] Stream runner terminated by user.")
    finally:
        request_queue.put(None)

if __name__ == "__main__":
    project_id, dataset_id, table_id = configure_target("transactions")

    expected_schema = [
        bigquery.SchemaField("transaction_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("card_number_hash", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("amount", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("merchant_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("timestamp", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("fraud_risk_score", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("alert_level", "STRING", mode="NULLABLE"),
    ]

    try:
        bq_client = bigquery.Client(project=project_id)
        check_or_create_table(bq_client, dataset_id, table_id, expected_schema)
        run_committed_writer(project_id, dataset_id, table_id)
    except Exception as e:
        print(f"\n[-] Unexpected execution error: {e}", file=sys.stderr)
        sys.exit(1)

