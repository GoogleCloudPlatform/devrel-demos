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

    parser = argparse.ArgumentParser(description="BigQuery Storage Write API - Pending Mode Demo")
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

def generate_adjustments(warehouse, batch_id, count):
    adjustments = []
    skus = ["SKU-100-RED", "SKU-200-BLU", "SKU-300-GRN", "SKU-400-BLK"]
    for _ in range(count):
        adj = schema_pb2.InventoryAdjustment()
        adj.adjustment_id = str(uuid.uuid4())
        adj.warehouse_id = warehouse
        adj.item_sku = random.choice(skus)
        adj.quantity_changed = random.randint(-50, 100)
        adj.batch_id = batch_id
        adj.timestamp = str(int(time.time() * 1000000))
        adj.operator_id = f"user_{random.randint(10, 99)}"
        adjustments.append(adj)
    return adjustments

def run_inventory_reconciliation(project_id, dataset_id, table_id):
    client = bigquery_storage_v1.BigQueryWriteClient()
    parent = client.table_path(project_id, dataset_id, table_id)

    try:
        write_stream = types.WriteStream()
        write_stream.type_ = types.WriteStream.Type.PENDING
        created_stream = client.create_write_stream(parent=parent, write_stream=write_stream)
        stream_name = created_stream.name
        print(f"\n[+] Established PENDING write stream: {stream_name}")
    except GoogleAPICallError as e:
        print(f"[-] Failed to create write stream: {e}")
        return

    proto_descriptor = descriptor_pb2.DescriptorProto()
    schema_pb2.InventoryAdjustment.DESCRIPTOR.CopyToProto(proto_descriptor)

    batch_id = f"batch_reconcile_{uuid.uuid4().hex[:8]}"
    east_records = generate_adjustments("Warehouse-East", batch_id, 4)
    west_records = generate_adjustments("Warehouse-West", batch_id, 4)

    def make_request(records, offset):
        proto_rows = types.ProtoRows(
            serialized_rows=[r.SerializeToString() for r in records]
        )
        proto_data = types.AppendRowsRequest.ProtoData(
            writer_schema=types.ProtoSchema(proto_descriptor=proto_descriptor),
            rows=proto_rows
        )
        return types.AppendRowsRequest(
            write_stream=stream_name,
            proto_rows=proto_data,
            offset=offset
        )

    request_east = make_request(east_records, 0)
    request_west = make_request(west_records, len(east_records))

    def request_generator():
        yield request_east
        yield request_west

    print(f"[*] Appending records over persistent stream...")
    
    try:
        responses = client.append_rows(request_generator())
        responses_iter = iter(responses)
        
        # Process East response
        east_res = next(responses_iter)
        if east_res.error.code != 0:
            print(f"[-] East Append Error: {east_res.error.message}")
            return
        print(f"[+] East batch written. Next offset: {east_res.append_result.offset + len(east_records)}")

        # Process West response
        west_res = next(responses_iter)
        if west_res.error.code != 0:
            print(f"[-] West Append Error: {west_res.error.message}")
            return
        print(f"[+] West batch written. Current total rows: {len(east_records) + len(west_records)}")

    except StopIteration:
        print("[-] Stream connection closed prematurely by the server.")
        return
    except Exception as e:
        print(f"[-] Ingestion error on stream: {e}")
        return

    print("[*] Finalizing pending stream...")
    try:
        finalize_req = types.FinalizeWriteStreamRequest(name=stream_name)
        finalize_res = client.finalize_write_stream(request=finalize_req)
        print(f"[+] Stream finalized. Rows in stream buffer: {finalize_res.row_count}")

        print("[*] Committing transaction batch...")
        commit_res = client.batch_commit_write_streams(
            request={
                "parent": parent,
                "write_streams": [stream_name]
            }
        )
        
        if commit_res.stream_errors:
            for err in commit_res.stream_errors:
                print(f"[-] Commit Error: {err.error_status.message}")
                sys.exit(1)
        else:
            print("[+] Transaction committed successfully! Inventory adjustment batch is queryable.")
    except GoogleAPICallError as e:
        print(f"[-] Finalize/Commit failed: {e}")

if __name__ == "__main__":
    project_id, dataset_id, table_id = configure_target("inventory")

    expected_schema = [
        bigquery.SchemaField("adjustment_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("warehouse_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("item_sku", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("quantity_changed", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("batch_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("timestamp", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("operator_id", "STRING", mode="NULLABLE"),
    ]

    try:
        bq_client = bigquery.Client(project=project_id)
        check_or_create_table(bq_client, dataset_id, table_id, expected_schema)
        run_inventory_reconciliation(project_id, dataset_id, table_id)
    except Exception as e:
        print(f"\n[-] Unexpected execution error: {e}", file=sys.stderr)
        sys.exit(1)

