import os
import requests
import base64

# The starting URL for the GitHub API, pointing to the 'specs' directory.
API_URL = "https://api.github.com/repos/osquery/osquery/contents/specs"

# The local directory where the .table files will be saved.
OUTPUT_DIR = "schema"

# Your GitHub Personal Access Token (PAT)
# Read from an environment variable for security
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

def get_headers():
    """Returns headers for the GitHub API request."""
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def download_files(api_url, output_dir):
    """
    Recursively downloads .table files from the osquery GitHub repository.

    Args:
        api_url: The GitHub API URL to fetch the contents from.
        output_dir: The local directory to save the files in.
    """
    response = requests.get(api_url, headers=get_headers())
    response.raise_for_status()  # Raise an exception for bad status codes
    contents = response.json()

    for item in contents:
        if item['type'] == 'file' and item['name'].endswith('.table'):
            print(f"Downloading {item['path']}...")
            # Get the content of the file
            file_response = requests.get(item['url'], headers=get_headers())
            file_response.raise_for_status() # Raise an exception for bad status codes
            file_data = file_response.json()

            # Decode the base64 content
            if 'content' in file_data:
                file_content = base64.b64decode(file_data['content'])
                
                # Ensure the local directory structure exists
                local_path_dir = os.path.join(output_dir, os.path.dirname(item['path']))
                os.makedirs(local_path_dir, exist_ok=True)
                
                # Save the file
                file_path = os.path.join(output_dir, item['path'])
                with open(file_path, 'wb') as f:
                    f.write(file_content)
            else:
                print(f"Warning: Could not find content for {item['path']}")


        elif item['type'] == 'dir':
            # If it's a directory, recursively call this function
            download_files(item['url'], output_dir)

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    if not GITHUB_TOKEN:
        print("Error: The GITHUB_TOKEN environment variable is not set.")
        print("Please create a GitHub Personal Access Token and set it to proceed.")
        print("See: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token")
        exit(1)

    print("Starting download of osquery .table schema files...")
    try:
        download_files(API_URL, OUTPUT_DIR) # Start with the root of the output dir
        print("\nDownload complete.")
        print(f"All .table files have been saved to the '{os.path.abspath(OUTPUT_DIR)}' directory.")
    except requests.exceptions.RequestException as e:
        print(f"\nAn error occurred: {e}")
        print("Please check your internet connection and ensure the GitHub repository is accessible.")
        if "rate limit" in str(e).lower():
            print("You've likely hit the GitHub API rate limit. Please ensure your GITHUB_TOKEN is valid.")