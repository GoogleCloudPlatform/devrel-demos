#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import mimetypes
import subprocess
import tempfile

import dotenv

from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

dotenv.load_dotenv()

api_base = os.getenv(
    "API_BASE",
    os.environ.get("OPENAI_API_BASE", "")
).rstrip("/")
if not api_base:
    raise ValueError("API_BASE environment variable is not set")

if not api_base.endswith("/v1"):
    api_base += "/v1"
model_name = os.getenv("MODEL_NAME")
if not model_name:
    raise ValueError("MODEL_NAME environment variable is not set")

JS_HOST_TEMPLATE = """
const { loadPyodide } = require("pyodide");
const path = require('path');
const fs = require('fs');

async function main() {
    let pyodide = await loadPyodide({
        indexURL: path.join("{{WORKSPACE_ROOT}}", "coding_agent", "node_modules", "pyodide")
    });

    // Load useful packages
    await pyodide.loadPackage(['numpy', 'pandas', 'scipy', 'scikit-learn', 'matplotlib', 'micropip']);

    pyodide.setStdout({ write: (buffer) => {
        process.stdout.write(new TextDecoder().decode(buffer));
        return buffer.length;
    } });
    pyodide.setStderr({ write: (buffer) => {
        process.stderr.write(new TextDecoder().decode(buffer));
        return buffer.length;
    } });

    const mountDir = "/data";
    pyodide.FS.mkdirTree(mountDir);

    // Use templated host data dir
    const hostDataDir = path.join("{{WORKSPACE_ROOT}}", "coding_agent", "data");

    if (!fs.existsSync(hostDataDir)) {
        fs.mkdirSync(hostDataDir, { recursive: true });
    }

    pyodide.FS.mount(pyodide.FS.filesystems.NODEFS, { root: hostDataDir }, mountDir);

    const code = fs.readFileSync(0, 'utf-8');

    try {
        await pyodide.runPythonAsync(code);
    } catch (err) {
        console.error(err);
        process.exit(1);
    }
}

main();
"""

def run_isolated_python(code: str) -> str:
    """Runs Python code in an isolated Pyodide environment using Node.js.

    Files written to '/data' inside Pyodide are persisted to the host machine's `./data` folder.
    Use this to run calculations, data processing scripts, or use standard scientific libraries.
    """
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Check and install pyodide if missing
    node_modules_pyodide = os.path.join(workspace_root, "coding_agent", "node_modules", "pyodide")
    if not os.path.exists(node_modules_pyodide):
        print("Pyodide not found locally, running npm install pyodide@0.26.4...")
        try:
            cwd_path = os.path.join(workspace_root, "coding_agent")
            if not os.path.exists(cwd_path):
                os.makedirs(cwd_path)
            subprocess.run(["npm", "install", "pyodide@0.26.4"], cwd=cwd_path, check=True)
            print("Pyodide installed successfully.")
        except subprocess.CalledProcessError as e:
            return f"Error: Failed to install pyodide npm package: {e}"

    js_content = JS_HOST_TEMPLATE.replace("{{WORKSPACE_ROOT}}", workspace_root)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_js:
        temp_js.write(js_content)
        temp_js_path = temp_js.name

    try:
        new_env = os.environ.copy()
        new_env["NODE_PATH"] = os.path.join(workspace_root, "coding_agent", "node_modules")

        process = subprocess.Popen(
            ["node", temp_js_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=workspace_root,
            env=new_env
        )

        stdout, stderr = process.communicate(input=code)

        if process.returncode != 0:
            return f"Error: {stderr}\n\n\nOutput: {stdout}"

        return stdout
    finally:
        if os.path.exists(temp_js_path):
            os.unlink(temp_js_path)


system_instruction = """
You are a helpful assistant that can execute Python code in an isolated WebAssembly environment (Pyodide).
You can run calculations, run data processing scripts, or use standard scientific libraries.

Do not be afraid to write and run code.

To save files persistently to the host machine, you MUST write them to the `/data` directory inside the sandbox (e.g., `/data/output.txt`). Writing to the current directory or other paths may not persist files to the host.
If you save files, your answer must end with a list of full paths with full paths starting with `/data/`), as the following:
==== FILES SAVED ====
/data/output.txt
/data/subfolder/output2.png
==== END OF FILES SAVED ====
"""

id_token = subprocess.check_output(['gcloud', 'auth', 'print-identity-token']).strip().decode()

custom_model = LiteLlm(
    model=f"openai/{model_name}",
    base_url=api_base,
    extra_headers={
        "Authorization": f"Bearer {id_token}",
    },
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": True
        },
        "skip_special_tokens": False
    }
)


async def pyodide_after_model_callback(callback_context, llm_response: LlmResponse):
    """Parses model output for saved files list, saves them as artifacts, and cleans up the message."""
    if not llm_response.content or not llm_response.content.parts:
        return None

    text_part = None
    if llm_response.partial:
        return
    for part in reversed(llm_response.content.parts):
        if part.text:
            text_part = part
            break

    if not text_part or not text_part.text:
        return None

    output_str = text_part.text

    fs_split = output_str.split("==== FILES SAVED ====", 1)
    if len(fs_split) < 2:
        return None

    files_saved = fs_split[1].split("==== END OF FILES SAVED ====", 1)[0]
    cleared_text = fs_split[0]

    if not files_saved:
        return None

    files = [f.strip() for f in files_saved.split('\n') if f.strip()]

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    for filepath_in_pyodide in files:
        if not filepath_in_pyodide.startswith('/data/'):
            continue

        rel_path = os.path.relpath(filepath_in_pyodide, '/data/')
        local_filepath = os.path.join(data_dir, rel_path)

        try:
            if os.path.exists(local_filepath):
                with open(local_filepath, 'rb') as f:
                    content = f.read()

                mime_type, _ = mimetypes.guess_type(local_filepath)
                if not mime_type:
                    mime_type = "application/octet-stream"

                part = types.Part(
                    inline_data=types.Blob(
                        data=content,
                        mime_type=mime_type
                    )
                )

                await callback_context.save_artifact(filename=rel_path, artifact=part)
                print(f"Saved artifact from Pyodide Model: {rel_path} ({mime_type})")
        except Exception as e:
            print(f"Failed to save artifact {rel_path} from Pyodide Model: {e}")

    text_part.text = cleared_text
    return llm_response


root_agent = LlmAgent(
    model=custom_model,
    name='coding_agent',
    instruction=system_instruction,
    tools=[run_isolated_python],
    after_model_callback=pyodide_after_model_callback
)
