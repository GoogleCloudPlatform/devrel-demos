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

"""Client for calling the deployed pitch-generator agent on Cloud Run via A2A protocol."""

import argparse
import asyncio
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from a2a.client import Client, ClientConfig, ClientFactory
from a2a.types import Message, Part, Role, SendMessageRequest, Task, TaskState
from dotenv import load_dotenv


@dataclass
class PitchResult:
    """Structured result returned by the pitch-generator agent."""

    task_id: str
    status: str
    concept: str | None = None
    copy: str | None = None
    art_direction: str | None = None
    image_filename: str | None = None
    image_bytes: bytes | None = None
    raw_task: Task | None = None


class PitchGeneratorClient:
    """Client for interacting with pitch-generator over A2A protocol using a2a-sdk."""

    def __init__(self, service_url: str, timeout: float = 300.0):
        self.service_url = service_url.rstrip("/")
        self.endpoint = f"{self.service_url}/a2a/pitch_generator"
        self.timeout = timeout

    def _get_id_token(self) -> str:
        """Fetch Google Cloud identity token for authenticating to Cloud Run."""
        try:
            cmd = ["gcloud", "auth", "print-identity-token", "-q"]
            return subprocess.check_output(cmd, stderr=subprocess.PIPE).decode().strip()
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        try:
            import google.auth.transport.requests
            import google.oauth2.id_token

            auth_req = google.auth.transport.requests.Request()
            return google.oauth2.id_token.fetch_id_token(auth_req, self.service_url)
        except Exception as e:
            raise RuntimeError(
                f"Could not obtain Google Cloud identity token to authenticate to {self.service_url}. "
                "Ensure you are logged into gcloud (`gcloud auth login`) or set the ID_TOKEN environment variable."
            ) from e

    async def _create_a2a_client(self, token: str) -> tuple[Client, httpx.AsyncClient]:
        headers = None
        if token:
            headers = {"Authorization": f"Bearer {token}"}
        async_client = httpx.AsyncClient(headers=headers, timeout=self.timeout)
        config = ClientConfig(streaming=False, httpx_client=async_client)
        factory = ClientFactory(config=config)
        client = await factory.create_from_url(
            self.endpoint,
            resolver_http_kwargs={"headers": headers},
        )
        return client, async_client

    async def _send_and_get_task(self, client: Client, request: SendMessageRequest) -> Task:
        task: Task | None = None
        async for resp in client.send_message(request):
            if resp.HasField("task"):
                task = resp.task
        if not task:
            raise RuntimeError("Agent did not return a task in response")
        return task

    def _parse_pitch_result(self, task: Task) -> PitchResult:
        state_name = TaskState.Name(task.status.state)

        if task.status.state == TaskState.TASK_STATE_FAILED:
            err_text = "".join(p.text for p in task.status.message.parts if p.text)
            raise RuntimeError(f"Agent task failed: {err_text}")

        concept = None
        copy_text = None
        art_direction = None
        image_bytes = None
        image_filename = None

        for artifact in task.artifacts:
            for p in artifact.parts:
                if p.text and p.text.startswith("CONCEPT\n"):
                    sections = p.text.split("\n\n")
                    for s in sections:
                        if s.startswith("CONCEPT\n"):
                            concept = s.removeprefix("CONCEPT\n").strip()
                        elif s.startswith("COPY\n"):
                            copy_text = s.removeprefix("COPY\n").strip()
                        elif s.startswith("ART DIRECTION\n"):
                            art_direction = s.removeprefix("ART DIRECTION\n").strip()

                if p.raw and p.media_type.startswith("image/"):
                    image_bytes = p.raw
                    image_filename = artifact.name or "key_visual.jpg"

        return PitchResult(
            task_id=task.id,
            status=state_name,
            concept=concept,
            copy=copy_text,
            art_direction=art_direction,
            image_filename=image_filename,
            image_bytes=image_bytes,
            raw_task=task,
        )

    async def generate_pitch_async(self, prompt: str, auto_approve: bool = False) -> PitchResult:
        """Send a prompt to pitch-generator using a2a-sdk primitives and return result."""
        token = self._get_id_token() if self.service_url.startswith("https") else None
        client, async_client = await self._create_a2a_client(token)

        try:
            initial_req = SendMessageRequest(
                message=Message(
                    message_id=f"msg-{uuid.uuid4().hex[:8]}",
                    role=Role.ROLE_USER,
                    parts=[Part(text=prompt)],
                )
            )

            task = await self._send_and_get_task(client, initial_req)

            # Handle Human-in-the-Loop approval loop
            while task.status.state == TaskState.TASK_STATE_INPUT_REQUIRED:
                parts = task.status.message.parts

                draft_concept = None
                for artifact in task.artifacts:
                    for p in artifact.parts:
                        if p.text:
                            draft_concept = p.text
                            break

                interrupt_id = None
                prompt_text = "Please approve the campaign concept (yes/no):"

                for p in parts:
                    data_dict = dict(p.data.struct_value.fields)
                    if "name" in data_dict and data_dict["name"].string_value == "adk_request_input":
                        interrupt_id = data_dict.get("id", "").string_value if hasattr(data_dict.get("id", ""), "string_value") else ""
                        args_val = data_dict.get("args")
                        if args_val and hasattr(args_val, "struct_value"):
                            msg_val = args_val.struct_value.fields.get("message")
                            if msg_val and hasattr(msg_val, "string_value"):
                                prompt_text = msg_val.string_value
                        break

                print("\n=== HUMAN APPROVAL REQUIRED ===")
                if draft_concept:
                    print(f"\n[DRAFT CONCEPT]\n{draft_concept}\n")

                if auto_approve:
                    print(f"{prompt_text} -> Auto-approving with 'yes'")
                    user_response = "yes"
                else:
                    user_response = input(f"{prompt_text} ").strip()

                approval_part = Part()
                approval_part.data.struct_value.update({
                    "name": "adk_request_input",
                    "id": interrupt_id or str(uuid.uuid4()),
                    "response": {"result": user_response},
                })
                approval_part.metadata["adk_type"] = "function_response"

                resume_req = SendMessageRequest(
                    message=Message(
                        message_id=f"msg-{uuid.uuid4().hex[:8]}",
                        role=Role.ROLE_USER,
                        task_id=task.id,
                        context_id=task.context_id,
                        parts=[approval_part],
                    )
                )

                print("\nSubmitting approval response to agent...")
                task = await self._send_and_get_task(client, resume_req)

            return self._parse_pitch_result(task)

        finally:
            await async_client.aclose()

    def generate_pitch(self, prompt: str, auto_approve: bool = False) -> PitchResult:
        """Synchronous wrapper for generate_pitch_async."""
        return asyncio.run(self.generate_pitch_async(prompt, auto_approve=auto_approve))


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Call the deployed pitch-generator agent via A2A."
    )
    parser.add_argument(
        "prompt",
        nargs="?",
        default="cat on a bike",
        help="Campaign concept prompt (default: 'cat on a bike')",
    )
    parser.add_argument(
        "--save-image",
        type=Path,
        default=None,
        help="Path to save the generated key visual image (e.g., ./pitch.jpg)",
    )
    parser.add_argument(
        "-y",
        "--auto-approve",
        action="store_true",
        help="Automatically approve input requests with 'yes'",
    )
    args = parser.parse_args()

    try:
        service_url = os.getenv("PITCH_GENERATOR_URL")
        if not service_url:
            service_url = (
            subprocess.check_output(
                [
                    "gcloud",
                    "run",
                    "services",
                    "describe",
                    "pitch-generator",
                    "--region",
                    os.getenv("GOOGLE_CLOUD_REGION", os.getenv("REGION")),
                    "--format",
                    "value(status.url)",
                    "--project",
                    os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID")),
                ]
            ).decode().strip()
        )
    except Exception as e:
        raise RuntimeError("Could not fetch service URL from Cloud Run") from e

    print(f"Connecting to pitch-generator at: {service_url}")
    print(f"Prompt: {args.prompt!r}\n")

    client = PitchGeneratorClient(service_url=service_url)
    result = client.generate_pitch(args.prompt, auto_approve=args.auto_approve)

    print("=== CAMPAIGN PITCH ===")
    if result.concept:
        print(f"\n[CONCEPT]\n{result.concept}")
    if result.copy:
        print(f"\n[COPY]\n{result.copy}")
    if result.art_direction:
        print(f"\n[ART DIRECTION]\n{result.art_direction}")

    if result.image_bytes:
        print(
            f"\n[KEY VISUAL]\n{result.image_filename or 'image'} ({len(result.image_bytes):,} bytes)"
        )
        if args.save_image:
            args.save_image.write_bytes(result.image_bytes)
            print(f"Saved key visual image to: {args.save_image}")


if __name__ == "__main__":
    main()
