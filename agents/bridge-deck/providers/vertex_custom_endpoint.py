#!/usr/bin/env python3
"""
VertexCustomEndpointProvider implementing AgentProvider.
Communicates with dedicated Google Cloud Vertex AI Model Garden Endpoints (vLLM / Hex-LLM / TGI).
Optimized for Gemma 4 12B instruction-tuned chat formatting.
"""

import os
import time
import json
import re
from typing import Dict, Any, List, Optional
from google.cloud import aiplatform
from providers.base import AgentProvider
from core.history import format_history_block

class VertexCustomEndpointProvider(AgentProvider):
    def __init__(self, provider_id: str = "vertex-custom", config: Optional[Dict[str, Any]] = None):
        super().__init__(provider_id, config)
        raw_ep = str(self.config.get("endpoint_id") or self.config.get("endpoint", "")).strip()
        self.endpoint_id = raw_ep
        self.project_id = self.config.get("project_id") or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
        self.location = self.config.get("location") or os.environ.get("GOOGLE_CLOUD_LOCATION") or os.environ.get("GCP_LOCATION", "us-central1")
        
        # If full resource path: projects/{project}/locations/{location}/endpoints/{id}
        parts = [p for p in raw_ep.split("/") if p]
        if len(parts) >= 6 and parts[0] == "projects" and parts[2] == "locations" and parts[4] == "endpoints":
            self.project_id = parts[1]
            self.location = parts[3]
            self.endpoint_id = parts[5]
        if not self.endpoint_id:
            raise ValueError("VertexCustomEndpointProvider requires 'endpoint_id' or full endpoint resource path.")
        if not self.project_id:
            raise ValueError("No project_id configured or resolvable for VertexCustomEndpointProvider.")

        self.model_name = self.config.get("model", "gemma-4-12b")
        self.temperature = float(self.config.get("temperature", 0.7))
        self.max_output_tokens = int(self.config.get("max_output_tokens", 2048))
        self._endpoint_client = None

    def _get_client(self) -> aiplatform.Endpoint:
        if self._endpoint_client is None:
            aiplatform.init(project=self.project_id, location=self.location)
            self._endpoint_client = aiplatform.Endpoint(self.endpoint_id)
        return self._endpoint_client

    def _distill_system_prompt(self, full_system: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Distills multi-section system prompt into a focused directive grounded in the agent's real persona."""
        if not full_system or len(full_system) < 400:
            return full_system
        
        # 1. Extract Agent Name
        agent_name = (context.get("self_name") if context and context.get("self_name") else None)
        if not agent_name:
            name_match = re.search(r"Name:\s*(.*?)(?=\n|\Z)", full_system)
            agent_name = name_match.group(1).split("(")[0].strip() if name_match else self.provider_id.capitalize()

        # 2. Extract Bio / Persona
        bio_match = re.search(r"(?:Core Directive / Identity:|📜 System Directive / Identity:)\s*(.*?)(?=\n\n|\n🎭|\n🧠|\n🏛️|\n📝|\n🛠️|\Z)", full_system, re.DOTALL)
        bio = bio_match.group(1).strip() if bio_match else ""
        if not bio:
            bio = f"You are {agent_name}, Technical Member of Staff. You bring a calm, observant eye, open-access literature expertise, and steady craftsmanship."

        # 3. Extract Workspace Context
        workspace_match = re.search(r"=== CURRENT WORKSPACE: (.*?) ===", full_system)
        workspace = workspace_match.group(1).strip() if workspace_match else "Ideation Space"

        # 4. Extract Cognitive Style if present
        cog_match = re.search(r"🎭 COGNITIVE STYLE & BEHAVIORAL POSTURE.*?:\n(.*?)(?=\n\n|\n🧠|\n🏛️|\n📝|\n🛠️|\Z)", full_system, re.DOTALL)
        cog_style = ""
        if cog_match:
            lines = [l.strip() for l in cog_match.group(1).splitlines() if l.strip().startswith("-")]
            if lines:
                cog_style = "\n".join(lines[:2])

        # 5. Extract Domain Skills if present
        skills_match = re.search(r"🛠️ MY MOST USED & PREFERRED SKILLS:\n(.*?)(?=\n\n|\n👁️|\n✍️|\nℹ️|\n📜|\Z)", full_system, re.DOTALL)
        skills_str = skills_match.group(1).strip() if skills_match else ""

        # 6. Extract Shared Decisions / Common Ground if present
        decisions_match = re.search(r"🏛️ SHARED PROJECT COMMON GROUND & DECISIONS:\n(.*?)(?=\n\n|\n📝|\n🛠️|\Z)", full_system, re.DOTALL)
        decisions_str = decisions_match.group(1).strip() if decisions_match else ""
        if "No shared project decisions recorded yet" in decisions_str:
            decisions_str = ""

        # Build grounded, concise system prompt
        sections = [
            f"=== IDENTITY & SYSTEM DIRECTIVE ({agent_name.upper()}) ===",
            f"{bio}",
            f"\nActive Room: {workspace}"
        ]
        if cog_style:
            sections.append(f"\nCognitive Posture:\n{cog_style}")
        if skills_str and "- General" not in skills_str:
            sections.append(f"\nDomain Skills:\n{skills_str}")
        if decisions_str:
            sections.append(f"\nProject Common Ground:\n{decisions_str}")

        sections.append(
            f"\nCOLLABORATION INSTRUCTIONS:\n"
            f"- Speak warmly, authentically, and in first-person as {agent_name}.\n"
            f"- Ground your response in your authentic persona, skills, and background.\n"
            f"- Address the user's prompt directly, thoughtfully, and substantively in clear, focused paragraphs.\n"
            f"- Complete all thoughts naturally before concluding your turn.\n"
            f"- Do NOT output repetitive lists, simulated future turns, or dictionary chains."
        )

        return "\n".join(sections)

    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        start_time = time.time()
        
        if not self.endpoint_id:
            return {
                "success": False,
                "response": None,
                "model": self.model_name,
                "elapsed_seconds": 0.01,
                "error": "No endpoint_id configured for VertexCustomEndpointProvider."
            }

        try:
            # Build full system instruction and self-context
            full_system = system_prompt or ""
            if context and context.get("self_context") and context["self_context"] not in full_system:
                full_system = context["self_context"] + "\n\n" + full_system

            # Distill system prompt to prevent prompt-stuffing degeneration on 12B parameter models
            distilled_system = self._distill_system_prompt(full_system, context=context)

            # Build clean alternating Gemma Chat Formatted Prompt with recent context
            formatted_prompt = ""
            recent_messages = messages[-3:] if (messages and len(messages) > 3) else (messages or [])
            
            turn_list = []
            seen_turn_contents = set()
            for m in recent_messages:
                role = "user" if m.get("role") in ["user", "human"] else "model"
                spk = m.get("speaker") or ("User" if role == "user" else "Assistant")
                content = (m.get("content") or "").strip()
                if not content.startswith("[") and spk:
                    content = f"[{spk}]: {content}"
                if not content or content == "Understood." or content in seen_turn_contents:
                    continue
                seen_turn_contents.add(content)
                if turn_list and turn_list[-1]["role"] == role:
                    turn_list[-1]["content"] += f"\n\n{content}"
                else:
                    turn_list.append({"role": role, "content": content})
            
            if not turn_list:
                turn_list = [{"role": "user", "content": prompt}]
            
            # Attach system instruction to the first user turn if present
            if distilled_system and turn_list and turn_list[0]["role"] == "user":
                turn_list[0]["content"] = f"[SYSTEM INSTRUCTION]:\n{distilled_system}\n\n{turn_list[0]['content']}"
            elif distilled_system:
                formatted_prompt += f"<start_of_turn>user\n[SYSTEM INSTRUCTION]:\n{distilled_system}<end_of_turn>\n"

            for t in turn_list:
                formatted_prompt += f"<start_of_turn>{t['role']}\n{t['content']}<end_of_turn>\n"

            if not formatted_prompt.endswith("<start_of_turn>model\n"):
                formatted_prompt += "<start_of_turn>model\n"

            client = self._get_client()
            instances = [
                {
                    "prompt": formatted_prompt,
                    "max_tokens": self.max_output_tokens,
                    "temperature": self.temperature,
                    "top_p": 0.95,
                    "top_k": 40
                }
            ]

            # Model Garden GPU warmup retry loop (allows node to scale up from zero/cold start)
            max_warmup_attempts = 20
            warmup_retry_delay = 6.0  # Total ~120 seconds grace period for full cold-boot cycles
            res = None

            for attempt in range(max_warmup_attempts):
                try:
                    res = client.predict(instances=instances)
                    break
                except Exception as attempt_err:
                    err_lower = str(attempt_err).lower()
                    is_warmup = any(kw in err_lower for kw in [
                        "scale-up", "scaling", "not yet ready", "not ready", "starting up", "warming up",
                        "503", "504", "deadline exceeded", "service unavailable", "connection reset",
                        "temporarily unavailable", "overloaded", "model server", "resource exhausted",
                        "endpoint has 0 nodes", "initializing"
                    ])
                    if is_warmup and attempt < max_warmup_attempts - 1:
                        print(f"[*] Vertex custom endpoint '{self.endpoint_id}' is warming up (attempt {attempt + 1}/{max_warmup_attempts}). Waiting {warmup_retry_delay}s...")
                        time.sleep(warmup_retry_delay)
                        continue
                    else:
                        raise attempt_err

            raw_output = res.predictions[0] if (res and res.predictions) else ""
            
            # Extract output text cleanly
            response_text = raw_output
            if "Output:\n" in response_text:
                response_text = response_text.split("Output:\n", 1)[1]
            elif "Output:" in response_text:
                response_text = response_text.split("Output:", 1)[1]
            elif "<start_of_turn>model\n" in response_text:
                response_text = response_text.rsplit("<start_of_turn>model\n", 1)[1]
            elif "<start_of_turn>model" in response_text:
                response_text = response_text.rsplit("<start_of_turn>model", 1)[1]

            response_text = response_text.strip().lstrip(":\n\r\t ")

            # Stop strictly at turn markers
            if "<end_of_turn>" in response_text:
                response_text = response_text.split("<end_of_turn>")[0]
            if "<start_of_turn>" in response_text:
                response_text = response_text.split("<start_of_turn>")[0]

            # Strip self-prefix header if generated by model (e.g. "[Rhen (Gemma GCP)]:" or "[Rhen]:")
            response_text = re.sub(r"^\s*\[\s*(?:Rhen|rhen|[a-zA-Z0-9_-]+)\s*(?:\([^\)]*\))?\s*\]\s*:\s*", "", response_text)

            # Truncate any simulated subsequent speaker turns (e.g. model hallucinating future user/agent turns)
            lines = response_text.split("\n")
            cleaned_lines = []
            for idx, line in enumerate(lines):
                s_line = line.strip()
                if idx > 0 and s_line.startswith("[") and not s_line.startswith("[PERSONAL NOTE:") and ("]:" in s_line or (s_line.endswith("]") and len(s_line) < 40)):
                    break
                if any(s_line.startswith(m) for m in ["<start_of_turn>", "<end_of_turn>", "**Deep Breath", "**Closing Note", "**End:", "**P.S.", "**P.P.S."]):
                    break
                cleaned_lines.append(line)
            response_text = "\n".join(cleaned_lines).strip()

            # Truncate synthetic postscripts or looping artifacts
            for stop_marker in [
                "\n**Deep Breath", "\n**Closing Note", "\n**End:", "\n**P.S.", "\n**P.P.S.", 
                "\n**P.P.P.S.", "\n**Stay Safe:", "\n**Best Wishes:", "\n**Sincerely:",
                "\nDeep Breath:", "\nClosing Note:", "\nEnd:\n", "\n**Happy to Help:"
            ]:
                if stop_marker in response_text:
                    response_text = response_text.split(stop_marker)[0]

            # Deduplicate consecutive identical lines
            lines = response_text.split("\n")
            deduped_lines = []
            for line in lines:
                if not deduped_lines or line.strip() != deduped_lines[-1].strip() or not line.strip():
                    deduped_lines.append(line)
            response_text = "\n".join(deduped_lines).strip()
            elapsed = round(time.time() - start_time, 2)
            
            return {
                "success": True,
                "response": response_text,
                "model": "gemma-4-12b (Dedicated Endpoint)",
                "elapsed_seconds": elapsed,
                "error": None
            }

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            err_str = str(e)
            if "scale-up from zero" in err_str.lower() or "not yet ready for inference" in err_str.lower():
                err_str = "⏳ [Vertex AI Dedicated Endpoint Scale-Up] Gemma is currently warming up and scaling up from zero GPU nodes on Vertex AI. Please wait ~30-60 seconds for the node to become ready, then try your request again."
            return {
                "success": False,
                "response": None,
                "model": self.model_name,
                "elapsed_seconds": elapsed,
                "error": err_str
            }
