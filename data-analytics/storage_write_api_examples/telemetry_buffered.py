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

    parser = argparse.ArgumentParser(description="BigQuery Storage Write API - Buffered Mode Demo")
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

def generate_telemetry(vin, offset):
    tel = schema_pb2.VehicleTelemetry()
    tel.telemetry_id = str(uuid.uuid4())
    tel.vehicle_vin = vin
    tel.speed_mph = round(random.uniform(25.0, 75.0), 1)
    tel.latitude = 37.7749 + (offset * 0.0001)
    tel.longitude = -122.4194 - (offset * 0.0001)
    tel.timestamp = str(int(time.time() * 1000000))
    tel.safety_trigger_active = random.random() < 0.05
    
    if tel.safety_trigger_active:
        tel.G_force = round(random.uniform(1.8, 3.5), 2)
    else:
        tel.G_force = round(random.uniform(0.1, 0.8), 2)
        
    return tel

def run_telemetry_stream(project_id, dataset_id, table_id):
    client = bigquery_storage_v1.BigQueryWriteClient()
    parent = client.table_path(project_id, dataset_id, table_id)

    try:
        write_stream = types.WriteStream()
        write_stream.type_ = types.WriteStream.Type.BUFFERED
        created_stream = client.create_write_stream(parent=parent, write_stream=write_stream)
        stream_name = created_stream.name
        print(f"\n[+] Created BUFFERED write stream: {stream_name}")
    except GoogleAPICallError as e:
        print(f"[-] Failed to create write stream: {e}")
        return

    proto_descriptor = descriptor_pb2.DescriptorProto()
    schema_pb2.VehicleTelemetry.DESCRIPTOR.CopyToProto(proto_descriptor)

    def make_request(telemetry_bytes, offset):
        proto_rows = types.ProtoRows(serialized_rows=[telemetry_bytes])
        proto_data = types.AppendRowsRequest.ProtoData(
            writer_schema=types.ProtoSchema(proto_descriptor=proto_descriptor),
            rows=proto_rows
        )
        return types.AppendRowsRequest(
            write_stream=stream_name,
            proto_rows=proto_data,
            offset=offset
        )

    from queue import Queue
    request_queue = Queue()

    def request_generator():
        while True:
            req = request_queue.get()
            if req is None:
                break
            yield req

    vin = f"1FM5K8GC{random.randint(10000, 99999)}"
    print(f"[*] Ingesting telemetry for vehicle: {vin}")
    print("[*] Press Ctrl+C to terminate.")

    try:
        responses = client.append_rows(request_generator())
    except GoogleAPICallError as e:
        print(f"[-] Failed to establish write stream connection: {e}")
        return

    current_offset = 0
    last_flushed_offset = -1

    try:
        while True:
            tel = generate_telemetry(vin, current_offset)
            request = make_request(tel.SerializeToString(), current_offset)
            request_queue.put(request)
                
            try:
                response = next(responses)
                if response.error.code != 0:
                    print(f"[-] Write Error: {response.error.message}")
                    return
            except StopIteration:
                print("[-] Stream connection closed by the server.")
                break
            except Exception as e:
                print(f"[-] Ingestion error on stream: {e}")
                break

            current_offset += 1
            print(f"[*] Buffered row {current_offset} (Not yet queryable)")

            if tel.safety_trigger_active:
                print(f"\n[!] SAFETY TRIGGER ACTIVE (G-force: {tel.G_force})!")
                print(f"[*] FORCING IMMEDIATE EMERGENCY FLUSH up to offset: {current_offset - 1}")
                try:
                    flush_req = types.FlushRowsRequest(
                        write_stream=stream_name,
                        offset=current_offset - 1
                    )
                    client.flush_rows(request=flush_req)
                    print(f"[+] Emergency flush completed. Flushed rows {last_flushed_offset + 1} to {current_offset - 1}. Telemetry data is live!")
                    last_flushed_offset = current_offset - 1
                except GoogleAPICallError as e:
                    print(f"[-] Emergency flush failed: {e}")
            elif current_offset % 10 == 0:
                print(f"\n[*] Batch limit reached. Flushing up to offset: {current_offset - 1}")
                try:
                    flush_req = types.FlushRowsRequest(
                        write_stream=stream_name,
                        offset=current_offset - 1
                    )
                    client.flush_rows(request=flush_req)
                    print(f"[+] Batch flush completed. Flushed rows {last_flushed_offset + 1} to {current_offset - 1}.")
                    last_flushed_offset = current_offset - 1
                except GoogleAPICallError as e:
                    print(f"[-] Batch flush failed: {e}")

            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[+] Stream runner terminated by user.")
    finally:
        if current_offset - 1 > last_flushed_offset:
            print(f"\n[*] Flushing remaining {current_offset - 1 - last_flushed_offset} buffered rows...")
            try:
                flush_req = types.FlushRowsRequest(
                    write_stream=stream_name,
                    offset=current_offset - 1
                )
                client.flush_rows(request=flush_req)
                print(f"[+] Final flush completed successfully. Flushed remaining rows {last_flushed_offset + 1} to {current_offset - 1}.")
            except Exception as e:
                print(f"[-] Final flush failed: {e}")
        request_queue.put(None)

if __name__ == "__main__":
    project_id, dataset_id, table_id = configure_target("telemetry")

    expected_schema = [
        bigquery.SchemaField("telemetry_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("vehicle_vin", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("speed_mph", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("latitude", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("longitude", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("timestamp", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("safety_trigger_active", "BOOLEAN", mode="REQUIRED"),
        bigquery.SchemaField("G_force", "FLOAT", mode="NULLABLE"),
    ]

    try:
        bq_client = bigquery.Client(project=project_id)
        check_or_create_table(bq_client, dataset_id, table_id, expected_schema)
        run_telemetry_stream(project_id, dataset_id, table_id)
    except Exception as e:
        print(f"\n[-] Unexpected execution error: {e}", file=sys.stderr)
        sys.exit(1)

