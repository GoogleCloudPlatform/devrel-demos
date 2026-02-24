# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import subprocess
import threading
import uuid
import json
import time
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# In-memory storage for logs (Not suitable for production with multiple workers)
# Format: { 'deploy_id': {'logs': [], 'status': 'running'|'done'|'error'} }
deployments = {}

def run_billing_link(project_id, user_billing_name=None):
    """
    Attempts to find an open billing account and link the project to it.
    If user_billing_name is provided, looks for that specific name (partial match).
    Otherwise, defaults to looking for 'Google Cloud Platform Trial Billing Account'.
    Returns (success_bool, message).
    """
    try:
        # 1. List billing accounts
        cmd = ["gcloud", "billing", "accounts", "list", "--format=json", "--filter=open=true"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        accounts = json.loads(result.stdout)
        
        if not accounts:
            return False, "No open billing accounts found for this user."

        # 2. Determine Target Name
        target_account = None
        
        if user_billing_name and user_billing_name.strip():
            # User specified a name
            target_name = user_billing_name.strip()
            print(f"DEBUG: Searching for user-specified billing account containing: '{target_name}'")
        else:
            # Default behavior
            target_name = "Google Cloud Platform Trial Billing Account"
            print(f"DEBUG: Searching for default trial billing account: '{target_name}'")
        
        # 3. Search for the account
        for acct in accounts:
            # Exact match
            if acct.get('displayName') == target_name:
                target_account = acct
                break
        
        # 4. Handle Not Found
        if not target_account:
            return False, f"Error: Could not find a billing account matching '{target_name}'. Please check the name or ensure you have access."

        print(f"DEBUG: Found and selected Billing Account: {target_account.get('displayName')}")

        acct_id = target_account['name'].split('/')[-1] # format usually billingAccounts/ID
        acct_display = target_account.get('displayName', acct_id)

        # 5. Link project
        link_cmd = [
            "gcloud", "billing", "projects", "link", project_id,
            f"--billing-account={acct_id}"
        ]
        subprocess.run(link_cmd, capture_output=True, text=True, check=True)
        
        return True, f"Successfully linked project '{project_id}' to billing account '{acct_display}' ({acct_id})"
        
    except subprocess.CalledProcessError as e:
        return False, f"GCloud Error: {e.stderr}"
    except Exception as e:
        return False, str(e)

def generate_deployment_summary(project, region, cluster, instance):
    """Generate a structured summary with connection details and next steps."""
    summary = {
        "connection": {
            "project_id": project,
            "region": region,
            "cluster_name": cluster,
            "instance_name": instance,
            "database_user": "postgres",
            "database_port": "5432",
            "network": "easy-alloydb-vpc",
            "subnet": "easy-alloydb-subnet"
        },
        "commands": {
            "get_ip": f"gcloud alloydb instances describe {instance} \\\n  --cluster={cluster} \\\n  --region={region} \\\n  --format=\"get(ipAddress)\""
        }
    }
    return summary


def run_gcloud_script(deploy_id, project, region, password, cluster, instance):
    """Runs the shell script and streams output to global storage."""
    
    cmd = ['./create_alloydb.sh', project, region, password, cluster, instance]
    
    deployments[deploy_id]['logs'].append(f"Starting command: {' '.join(cmd)}\n")
    
    try:
        # Use Popen to capture stdout/stderr in real-time
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1  # Line buffered
        )

        # Read line by line
        for line in process.stdout:
            deployments[deploy_id]['logs'].append(line)
        
        process.wait()
        
        if process.returncode == 0:
            deployments[deploy_id]['status'] = 'done'
            deployments[deploy_id]['logs'].append("\nDeployment Complete. Check Console.\n")
            # Store the summary data for frontend
            deployments[deploy_id]['summary'] = generate_deployment_summary(project, region, cluster, instance)
        else:
            # Check if this is a "benign" error (resources already exist)
            log_text = ''.join(deployments[deploy_id]['logs']).lower()
            resources_exist = ('already exists' in log_text or 
                             'alreadyexists' in log_text or
                             'creating cluster...' in log_text)  # Progress indicates partial success
            
            if resources_exist:
                deployments[deploy_id]['status'] = 'error'  # Frontend handles this specially
                deployments[deploy_id]['logs'].append("\nNote: Some resources may already exist. Check console for details.\n")
                # Still provide the summary since resources are likely available
                deployments[deploy_id]['summary'] = generate_deployment_summary(project, region, cluster, instance)
            else:
                deployments[deploy_id]['status'] = 'error'
                deployments[deploy_id]['logs'].append(f"\nERROR: Script exited with code {process.returncode}\n")

    except Exception as e:
        deployments[deploy_id]['status'] = 'error'
        deployments[deploy_id]['logs'].append(f"\nEXCEPTION: {str(e)}\n")

@app.route('/')
def form():
    return render_template('index.html')

@app.route('/regions', methods=['GET'])
def get_regions():
    """Fetches list of available Google Cloud regions."""
    try:
        project_id = request.args.get('project_id')
        
        # We MUST have a project ID to fetch regions reliably
        if not project_id:
            return jsonify({'status': 'error', 'message': 'Project ID is missing. Please enter a Project ID first.'})

        # Explicitly pass --project flag to gcloud
        cmd = ["gcloud", "compute", "regions", "list", "--format=json", f"--project={project_id}"]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        regions_data = json.loads(result.stdout)
        
        # Extract name and sort
        regions = sorted([r['name'] for r in regions_data])
        
        return jsonify({'status': 'success', 'regions': regions})
    except subprocess.CalledProcessError as e:
        # Return the stderr from gcloud so we know why it failed (e.g. invalid project ID)
        return jsonify({'status': 'error', 'message': f"GCloud Error: {e.stderr}"})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/link-billing', methods=['POST'])
def link_billing():
    project_id = request.form.get('project_id')
    billing_name = request.form.get('billing_account_name') # Get optional input
    
    if not project_id:
        return jsonify({'status': 'error', 'message': 'Project ID is required'})

    success, msg = run_billing_link(project_id, billing_name)
    return jsonify({
        'status': 'success' if success else 'error',
        'message': msg
    })

@app.route('/deploy', methods=['POST'])
def deploy():
    # 1. Get data
    project_id = request.form.get('project_id')
    region = request.form.get('region')
    password = request.form.get('password')
    cluster_id = request.form.get('cluster_id')
    instance_id = request.form.get('instance_id')

    # 2. Create ID and Thread
    deploy_id = str(uuid.uuid4())
    deployments[deploy_id] = {'logs': [], 'status': 'running'}

    thread = threading.Thread(
        target=run_gcloud_script, 
        args=(deploy_id, project_id, region, password, cluster_id, instance_id)
    )
    thread.start()

    # 3. Return ID for polling
    return jsonify({'deployment_id': deploy_id})

@app.route('/logs/<deploy_id>')
def get_logs(deploy_id):
    if deploy_id not in deployments:
        return jsonify({'error': 'Not found'}), 404
    
    response = {
        'logs': deployments[deploy_id]['logs'],
        'status': deployments[deploy_id]['status']
    }
    
    # Include summary if available
    if 'summary' in deployments[deploy_id]:
        response['summary'] = deployments[deploy_id]['summary']
    
    return jsonify(response)

@app.route('/run-command', methods=['POST'])
def run_command():
    """Execute specific predefined commands and return the output."""
    command_type = request.form.get('command_type')
    
    # Get parameters
    project = request.form.get('project_id')
    region = request.form.get('region')
    cluster = request.form.get('cluster')
    instance = request.form.get('instance')
    
    try:
        if command_type == 'get_ip':
            # Get AlloyDB instance private IP
            cmd = [
                'gcloud', 'alloydb', 'instances', 'describe', instance,
                f'--cluster={cluster}',
                f'--region={region}',
                f'--project={project}',
                '--format=get(ipAddress)'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                ip = result.stdout.strip()
                return jsonify({
                    'status': 'success',
                    'output': ip,
                    'message': f'Private IP: {ip}'
                })
            else:
                return jsonify({
                    'status': 'error',
                    'output': result.stderr,
                    'message': 'Failed to get IP address'
                })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Unknown command type'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': 'Command timed out'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)
