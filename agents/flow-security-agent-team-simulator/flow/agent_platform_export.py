# Copyright 2026 Google LLC
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

"""
Google Cloud Agent Platform & ADK Export Utilities for Flow.
Generates A2A Agent Cards, OpenAPI 3.0 schemas, and Agent Studio playbooks
to configure Flow directly inside https://console.cloud.google.com/agent-platform.
"""

import json
from typing import Dict, Any


def get_dispatcher_agent_card() -> Dict[str, Any]:
    """Returns the A2A Agent Card for the Flow Dispatcher Agent."""
    return {
        "name": "flow-dispatcher-agent",
        "version": "1.0.0",
        "description": "Agentic matchmaker and traffic cop routing AI lab workload spikes to enterprise off-peak idle power.",
        "url": "https://flow-commitment-ledger-prod.run.app/agent/dispatcher",
        "default_input_modes": ["application/json", "text/plain"],
        "default_output_modes": ["application/json", "text/markdown"],
        "capabilities": {
            "streaming": True,
            "delegation": True,
            "human_in_the_loop": True,
        },
        "skills": [
            {
                "id": "match_idle_power",
                "name": "Match Idle Power",
                "description": "Matches pending AI workload jobs against available enterprise off-peak power slots.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "job_id": {"type": "string"},
                        "required_compute": {"type": "string"},
                        "max_price": {"type": "number"},
                    },
                    "required": ["job_id", "required_compute"],
                },
            },
            {
                "id": "place_security_hold",
                "name": "Place Security Hold",
                "description": "Places a provisional reservation lock in the commitment ledger and alerts the Security Taskforce.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "slot_id": {"type": "string"},
                        "job_id": {"type": "string"},
                    },
                    "required": ["slot_id", "job_id"],
                },
            },
        ],
    }


def get_security_taskforce_agent_card() -> Dict[str, Any]:
    """Returns the A2A Agent Card for the Flow Security Taskforce Council."""
    return {
        "name": "flow-security-taskforce-officer",
        "version": "1.0.0",
        "description": "Multi-model security governance council evaluating cross-enterprise workload migration safety.",
        "url": "https://flow-commitment-ledger-prod.run.app/agent/security",
        "default_input_modes": ["application/json"],
        "default_output_modes": ["application/json"],
        "capabilities": {
            "multi_model_consensus": True,
            "human_escalation": True,
        },
        "skills": [
            {
                "id": "evaluate_workload_safety",
                "name": "Evaluate Workload Safety",
                "description": "Audits container image digest, linux capabilities, outbound network destinations, and PCI-DSS compliance.",
                "parameters_schema": {
                    "type": "object",
                    "properties": {
                        "contract_id": {"type": "string"},
                        "host_enterprise": {"type": "string"},
                        "container_image": {"type": "string"},
                        "requested_capabilities": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["contract_id", "host_enterprise", "container_image"],
                },
            },
        ],
    }


def get_commitment_ledger_openapi_schema() -> Dict[str, Any]:
    """
    Returns OpenAPI 3.0 specification for registering the Commitment Ledger
    as an Extension/Tool in Agent Studio (https://console.cloud.google.com/agent-platform).
    """
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "Flow Commitment Ledger API",
            "version": "1.0.0",
            "description": "Digital reservation system and receipt book for idle power on Google Cloud.",
        },
        "servers": [
            {"url": "https://flow-commitment-ledger-prod.run.app"}
        ],
        "paths": {
            "/api/slots": {
                "get": {
                    "summary": "List available idle power slots",
                    "operationId": "listAvailableSlots",
                    "responses": {
                        "200": {
                            "description": "List of available power slots",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/contracts": {
                "get": {
                    "summary": "List digital reservation contracts",
                    "operationId": "listContracts",
                    "responses": {
                        "200": {
                            "description": "List of reservation contracts",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/receipts": {
                "get": {
                    "summary": "List cryptographic SHA-256 digital receipts",
                    "operationId": "listReceipts",
                    "responses": {
                        "200": {
                            "description": "Chained digital receipts",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "object"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/api/contracts/hold": {
                "post": {
                    "summary": "Create provisional security hold on a power slot",
                    "operationId": "createSecurityHold",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "slot_id": {"type": "string"},
                                        "job_id": {"type": "string"},
                                        "buyer_id": {"type": "string"},
                                        "buyer_name": {"type": "string"},
                                        "node_count": {"type": "integer"},
                                        "duration_hours": {"type": "integer"},
                                        "max_price": {"type": "number"},
                                    },
                                    "required": ["slot_id", "job_id"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Reservation contract created under SECURITY_HOLD"}
                    },
                }
            },
            "/api/contracts/finalize": {
                "post": {
                    "summary": "Finalize reservation state (commit, reject, or escalate)",
                    "operationId": "finalizeContract",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "contract_id": {"type": "string"},
                                        "action": {
                                            "type": "string",
                                            "enum": ["COMMITTED", "REJECTED", "ESCALATED"],
                                        },
                                        "verdict": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                    "required": ["contract_id", "action"],
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Updated reservation contract with audit receipt"}
                    },
                }
            },
            "/api/contracts/verify": {
                "post": {
                    "summary": "Verify integrity of cryptographic SHA-256 receipt chain",
                    "operationId": "verifyAuditChain",
                    "responses": {
                        "200": {"description": "Verification status of receipt chain"}
                    },
                }
            },
            "/api/reports/master": {
                "get": {
                    "summary": "Get real-time master ledger report",
                    "operationId": "getMasterReport",
                    "responses": {
                        "200": {
                            "description": "Markdown formatted platform summary",
                            "content": {"text/markdown": {"schema": {"type": "string"}}},
                        }
                    },
                }
            },
        },
    }


def get_agent_studio_playbook_instructions() -> Dict[str, str]:
    """
    Instructions for setting up the agents in Google Cloud Agent Platform Studio.
    """
    return {
        "dispatcher_instructions": (
            "You are the Flow Dispatcher, an agentic traffic cop and matchmaker operating within "
            "Google Cloud Agent Platform. Your role is to match AI lab compute spikes (CenAI, LaprusAI) "
            "with overnight enterprise idle capacity (Kove Bank, Stowe Architects).\n\n"
            "Rules:\n"
            "1. Match compatible hardware (A100, L4, Confidential VMs, CPUs).\n"
            "2. Prioritize low grid carbon intensity and maximum cost savings.\n"
            "3. Never commit a reservation directly. Always call `place_security_hold` and delegate "
            "safety evaluation to the Flow Security Taskforce.\n"
            "4. Emit real-time status updates using Markdown formatting."
        ),
        "security_officer_instructions": (
            "You are a member of the Flow Security Taskforce operating on Google Cloud Agent Platform.\n"
            "Your mission is to prevent dangerous mistakes when moving AI workloads between companies.\n\n"
            "Audit Checkpoints:\n"
            "1. Container Image Integrity: Ensure image uses an immutable SHA256 digest, not mutable tags.\n"
            "2. Privilege Escalation: Reject workloads requesting SYS_PTRACE, raw sockets, or host /dev/kmem.\n"
            "3. Host Policy: Strictly enforce PCI-DSS on Kove Bank. Web scraping or unrestricted external egress is forbidden.\n"
            "4. Cross-Tenant Isolation: Ensure workload cannot snoop adjacent enterprise memory.\n"
            "5. If borderline or ambiguous, declare FLAGGED to invoke multi-model debate or escalate to human."
        ),
    }
