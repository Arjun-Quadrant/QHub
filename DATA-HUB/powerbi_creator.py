from msal import PublicClientApplication
import requests
import json
import time
import sys
import base64
import os
import re
import time
from . import config

# 🔹 Microsoft Fabric Credentials
CLIENT_ID = config.client_id
CLIENT_SECRET = config.client_secret
TENANT_ID = config.tenant_id
WORKSPACE_ID = config.workspace_id
AUTHORITY = "https://login.microsoftonline.com/common"
FABRIC_SCOPE = ["https://api.fabric.microsoft.com/.default"]
SHAREPOINT_SCOPE = ["https://arjunnarendra1gmail.sharepoint.com/.default"]
EXCEL_FILE = "tableau_metadata.xlsx"

def get_fabric_access_token():
    """Authenticate and get an access token for Fabric API"""
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    result = app.acquire_token_interactive(scopes=FABRIC_SCOPE)
    return result["access_token"]

def get_sharepoint_access_token():
    """Authenticate and get an access token for SharePoint API"""
    app = PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    result = app.acquire_token_interactive(scopes=SHAREPOINT_SCOPE)
    return result["access_token"]

def encode_to_base_64(path):
     with open(path, 'rb') as binary_file:
        binary_file_data = binary_file.read()
        base64_encoded_data = base64.b64encode(binary_file_data)
        base64_output = base64_encoded_data.decode('utf-8')
        return base64_output
     
def switch_to_connection_reference(path, semantic_model_id, semantic_model_name, workspace_name):
    with open(path, 'r+') as file:
        content = file.read()
        file.truncate(0)
        json_data = json.loads(content)
        json_data["datasetReference"]["byPath"] = None
        json_data["datasetReference"]["byConnection"] = {
        "connectionString": f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_name};Initial Catalog={semantic_model_name};Integrated Security=ClaimsToken",
        "pbiServiceModelId": None,
        "pbiModelVirtualServerName": "sobe_wowvirtualserver",
        "pbiModelDatabaseName": f"{semantic_model_id}",
        "connectionType": "pbiServiceXmlaStyleLive",
        "name": "EntityDataSource"
        }
        file.seek(0)
        file.write(json.dumps(json_data))

def append_all_files(parts, pattern, base_dir=".", dataset_id=None, dataset_name=None, workspace_name=None):
    """
    Appends the relative path of every file found under base_dir
    to the list 'parts'. The paths are relative to base_dir and use
    forward slashes as separators.
    
    :param parts: List to which file paths will be appended.
    :param base_dir: Directory from which to start the search (default: current directory).
    """
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            file_full_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_full_path, base_dir)
            # Replace Windows backslashes with forward slashes
            relative_path = relative_path.replace("\\", "/")
            if pattern.search(relative_path):
                if "definition.pbir" in relative_path:
                    switch_to_connection_reference(relative_path, dataset_id, dataset_name, workspace_name=workspace_name)
                parts.append({
                "path": relative_path, 
                "payload": encode_to_base_64(relative_path),
                "payloadType": "InlineBase64"
                })

def create_dataset_payload():
    dataset_payload = {}
    dataset_payload["displayName"] = "Netflix Data New 4"
    dataset_payload["description"] = "Data on Netflix movies"
    parts = []
    regexp = re.compile(r"definition/|definition.pbism|diagramLayout.json|.platform")
    append_all_files(parts, regexp)
    dataset_payload["definition"] = {"parts": []}
    dataset_payload["definition"]["parts"] = parts
    return dataset_payload

def create_report_payload(dataset_id, dataset_name, workspace_name):
    report_payload = {}
    report_payload["displayName"] = "Netflix Report New 4"
    report_payload["description"] = "Report on Netflix movies"
    parts = []
    regexp = re.compile(r"CustomVisuals/|StaticResources/|definition.pbir|definition/|semanticModelDiagramLayout.json|mobileState.json")
    append_all_files(parts, regexp, dataset_id=dataset_id, dataset_name=dataset_name, workspace_name=workspace_name)
    report_payload["definition"] = {"parts": []}
    report_payload["definition"]["parts"] = parts
    return report_payload

def wait_for_resource_creation(post_url, post_headers, post_payload, poll_interval=2, max_attempts=10):
    # Make the initial POST request
    response = requests.post(url=post_url, headers=post_headers, json=post_payload)
    
    if response.status_code != 202:
        raise Exception(f"Unexpected status code: {response.status_code}")
    
    # Extract the URL for polling from the Location header (or response body)
    status_url = response.headers.get('Location')
    if not status_url:
        raise Exception("No Location header found in the 202 response.")
    
    # Poll the status URL until the resource is created
    for attempt in range(max_attempts):
        time.sleep(poll_interval)
        status_response = requests.get(status_url, headers=post_headers)
        if status_response.json()["status"] == "Succeeded":
            response = requests.get(f"{status_url}/result", headers=post_headers)
            return response.json()
    raise Exception("Resource creation did not complete in time.")

def create_semantic_model(token):
    """Create a Fabric semantic model"""
    
    url = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/semanticModels"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    semantic_model_folder = r"C:\Users\arjun\Quadrant\tableau_to_power_bi_project\Repos\QHub\DATA-HUB\Power BI\Sales Report Project\Sales.SemanticModel"
    os.chdir(semantic_model_folder)
    dataset_payload = create_dataset_payload()
    response = wait_for_resource_creation(url, headers, dataset_payload)
    return response

def get_connection_id_for_semantic_model(token, semantic_model_id):
    """List all connections that the user has permission for"""

    url = f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{semantic_model_id}/datasources"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    connections = requests.get(url, headers=headers)
    connection_info = connections.json()["value"][0]
    return connection_info["datasourceId"], connection_info["gatewayId"]

def update_connection(token, connection_id, gateway_id):
    """Update the connection"""

    url = f"https://api.powerbi.com/v1.0/myorg/gateways/{gateway_id}/datasources/{connection_id}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    token = get_sharepoint_access_token()

    payload = {
        "credentialDetails": {
            "credentialType": "OAuth2",
            "credentials": f"{{\"credentialData\":[{{\"name\":\"accessToken\", \"value\":\"{token}\"}}]}}",
            "encryptedConnection": "Encrypted",
            "encryptionAlgorithm": "None",
            "privacyLevel": "Organizational"
        }
    }
    requests.patch(url, headers=headers, json=payload)

def get_workspace_name(token):
    """Get the workspace name"""

    url = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, headers=headers)
    return response.json()["displayName"]

def create_report(token, dataset_id, dataset_name, workspace_name):
    """Create a Fabric report"""

    url = f"https://api.fabric.microsoft.com/v1/workspaces/{WORKSPACE_ID}/reports"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    report_folder = r"C:\Users\arjun\Quadrant\tableau_to_power_bi_project\Repos\QHub\DATA-HUB\Power BI\Sales Report Project\Sales.Report"
    os.chdir(report_folder)
    report_payload = create_report_payload(dataset_id, dataset_name, workspace_name)
    requests.post(url, headers=headers, json=report_payload)

def refresh_data(semantic_model_id):
    """Refresh data"""

    url = f"https://api.powerbi.com/v1.0/myorg/datasets/{semantic_model_id}/refreshes"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    payload = {
        "notifyOption": "NoNotification"
    }

    response = requests.post(url, headers=headers, json=payload)
    
if __name__ == "__main__":
    token = get_fabric_access_token()
    semantic_model_info = create_semantic_model(token)
    semantic_model_id = semantic_model_info["id"]
    semantic_model_name = semantic_model_info["displayName"]
    connection_id, gateway_id = get_connection_id_for_semantic_model(token, semantic_model_id)
    connection_info = update_connection(token, connection_id, gateway_id)
    workspace_name = get_workspace_name(token)
    create_report(token, semantic_model_id, semantic_model_name, workspace_name)
    refresh_data(semantic_model_id)