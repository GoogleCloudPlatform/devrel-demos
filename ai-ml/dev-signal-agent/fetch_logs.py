from google.cloud import logging

def search_logs(project_id, service_name, search_terms):
    client = logging.Client(project=project_id)
    
    # Filter for all logs from that service
    filter_str = f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service_name}"'
    
    print(f"Searching logs for: {search_terms}")
    
    # List entries
    entries = client.list_entries(filter_=filter_str, order_by=logging.DESCENDING, max_results=200)
    
    severity_map = {
        "DEBUG": 10,
        "INFO": 20,
        "NOTICE": 25,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
        "ALERT": 60,
        "EMERGENCY": 70
    }
    
    for entry in entries:
        timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        severity = entry.severity
        payload = entry.payload
        
        text = str(payload)
        found = any(term.lower() in text.lower() for term in search_terms)
        
        # entry.severity is a string
        severity_value = severity_map.get(severity, 0)
        
        if found or severity_value >= 40: # ERROR and above
            print(f"--- {timestamp} {severity} ---")
            # If it's a dict, try to print nicely
            if isinstance(payload, dict):
                print(payload.get('message', payload.get('text', str(payload))))
                if 'python_stacktrace' in payload:
                    print("\nSTACKTRACE:\n" + payload['python_stacktrace'])
            else:
                print(text)

if __name__ == "__main__":
    search_logs("shir-training", "dev-signal", ["reddit", "banana", "found", "context", "error", "mcp", "invalid"])
