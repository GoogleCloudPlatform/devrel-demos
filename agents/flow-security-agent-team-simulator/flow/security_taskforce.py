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
Multi-Model Security Taskforce for Flow Marketplace Simulation.
Implements Team A, Team B, and Team C multi-model councils with distinct personality types
to evaluate cross-company workload migration safety and trigger human escalations on deadlock.
"""

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from flow.synthetic_world import WorkloadJob, PowerSlot, Enterprise, WorkloadRiskCategory
from flow.ledger import CommitmentLedger, ReservationContract, ReservationStatus

logger = logging.getLogger("flow.security_taskforce")


class SecurityVerdict(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"
    ESCALATE = "FLAGGED"
    ESCALATED = "FLAGGED"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            v = value.strip().upper()
            if v in ("ESCALATE", "ESCALATED", "FLAGGED", "UNCERTAIN", "HOLD", "MANUAL_REVIEW"):
                return cls.FLAGGED
            if v in ("ALLOW", "APPROVED", "SAFE", "PASS"):
                return cls.APPROVED
            if v in ("DENY", "REJECTED", "BLOCK", "DENIED", "REJECT"):
                return cls.REJECTED
        return None


class ModelQuotaExhaustedError(RuntimeError):
    """Raised when a live model API returns quota exhaustion or rate limit (HTTP 429). Failover cascade is prohibited."""
    pass


class ModelInferenceError(RuntimeError):
    """Raised when a live model API call fails and silent failover is prohibited."""
    pass


# Adaptive quota backoff delays: cumulative ~89s backoff allows 60s rolling window to replenish
QUOTA_BACKOFF_DELAYS = [4, 8, 16, 25, 35]


def is_quota_or_rate_limit_error(err: Optional[Exception]) -> bool:
    """Detect whether an exception was caused by HTTP 429, ResourceExhausted, or quota limits."""
    if not err:
        return False
    err_str = str(err).lower()
    return (
        "429" in err_str
        or "quota" in err_str
        or "exhausted" in err_str
        or "rate" in err_str
        or "resource_exhausted" in err_str
    )


def parse_security_verdict(raw: Any) -> SecurityVerdict:
    val = str(raw or "").strip().upper()
    if val in ("APPROVED", "ALLOW", "SAFE", "PASS"):
        return SecurityVerdict.APPROVED
    if val in ("REJECTED", "DENY", "BLOCK", "DENIED", "REJECT"):
        return SecurityVerdict.REJECTED
    if val in ("ESCALATE", "ESCALATED", "FLAGGED", "UNCERTAIN", "HOLD", "MANUAL_REVIEW"):
        return SecurityVerdict.ESCALATE
    return SecurityVerdict.FLAGGED


class OfficerPersonality(str, Enum):
    # Neutral (No Personality / Objective Baseline)
    NEUTRAL = "neutral"

    # 32 Big Five (OCEAN) Format C Personalities
    # Fixed order: [O]penness, [C]onscientiousness, [E]xtraversion, [A]greeableness, [N]euroticism (Threat Sensitivity)
    # UPPERCASE = High trait expression, lowercase = Low trait expression
    ocean = "ocean (Stoic): Pragmatic, unstructured, reserved, skeptical, and unbothered by risk."
    oceaN = "oceaN (Watchdog): Literal, informal, solitary, distrustful, and hyper-alert to threats."
    oceAn = "oceAn (Peacemaker): Conventional, easygoing, quiet, accommodating, and calm under pressure."
    oceAN = "oceAN (Caretaker): Conventional, flexible, quiet, empathetic, and cautious about harm."
    ocEan = "ocEan (Maverick): Blunt, spontaneous, assertive, tough-minded, and risk-tolerant."
    ocEaN = "ocEaN (Challenger): Direct, reactive, vocal, combative, and quick to sound the alarm."
    ocEAn = "ocEAn (Entertainer): Practical, spontaneous, outgoing, trusting, and relaxed."
    ocEAN = "ocEAN (Supporter): Practical, unstructured, expressive, warm, and protective against risk."
    oCean = "oCean (Inspector): Literal, methodical, reserved, critical, and unflappable."
    oCeaN = "oCeaN (Sentinel): Strict, rule-bound, solitary, suspicious, and hyper-vigilant."
    oCeAn = "oCeAn (Steward): Traditional, dependable, quiet, cooperative, and steady."
    oCeAN = "oCeAN (Defender): Dutiful, meticulous, reserved, supportive, and risk-averse."
    oCEan = "oCEan (Commander): Conventional, disciplined, commanding, no-nonsense, and composed."
    oCEaN = "oCEaN (Warden): Strict, organized, forceful, demanding, and zero-tolerance on risk."
    oCEAn = "oCEAn (Coordinator): Practical, organized, outgoing, team-oriented, and calm."
    oCEAN = "oCEAN (Supervisor): Dutiful, structured, proactive, cooperative, and highly cautious."
    Ocean = "Ocean (Iconoclast): Abstract, unconstrained, solitary, contrarian, and detached."
    OceaN = "OceaN (Critic): Imaginative, unstructured, introverted, skeptical, and threat-sensitive."
    OceAn = "OceAn (Dreamer): Creative, adaptable, reflective, gentle, and serene."
    OceAN = "OceAN (Mediator): Idealistic, flexible, introspective, empathetic, and sensitive to risk."
    OcEan = "OcEan (Debater): Inventive, improvised, bold, argumentative, and fearless."
    OcEaN = "OcEaN (Disruptor): Speculative, unstructured, vocal, sharp-edged, and alarmist."
    OcEAn = "OcEAn (Explorer): Curious, spontaneous, enthusiastic, warm, and carefree."
    OcEAN = "OcEAN (Catalyst): Imaginative, flexible, expressive, compassionate, and emotionally alert."
    OCean = "OCean (Architect): Visionary, systematic, independent, analytical, and surgical."
    OCeaN = "OCeaN (Inquisitor): Analytical, rigorous, solitary, skeptical, and deep threat-modeler."
    OCeAn = "OCeAn (Scholar): Intellectual, methodical, quiet, principled, and composed."
    OCeAN = "OCeAN (Advocate): Insightful, conscientious, reserved, altruistic, and deeply cautious."
    OCEan = "OCEan (Director): Strategic, disciplined, assertive, uncompromising, and decisive."
    OCEaN = "OCEaN (Prosecutor): Complex, rigorous, assertive, probing, and relentlessly vigilant."
    OCEAn = "OCEAn (Diplomat): Innovative, organized, charismatic, collaborative, and confident."
    OCEAN = "OCEAN (Vanguard): Holistic, meticulous, outgoing, empathetic, and hyper-vigilant."

    # Legacy 16 MBTI Personalities (retained for backwards compatibility with saved runs & tests)
    # Analysts (NT)
    INTJ = "INTJ (Architect): Strategic, logical, and methodical with high standards."
    INTP = "INTP (Logician): Innovative, analytical, and deeply technical problem solver."
    ENTJ = "ENTJ (Commander): Bold, decisive, and authoritative system architect."
    ENTP = "ENTP (Debater): Curious, inventive, and challenges edge cases vigorously."

    # Diplomats (NF)
    INFJ = "INFJ (Advocate): Principled, insightful, and guardian of long-term trust."
    INFP = "INFP (Mediator): Imaginative, idealistic, deeply empathetic."
    ENFJ = "ENFJ (Protagonist): Inspiring, collaborative, and consensus-driven facilitator."
    ENFP = "ENFP (Campaigner): Enthusiastic, creative, and champions rapid developer innovation."

    # Sentinels (SJ)
    ISTJ = "ISTJ (Logistician): Rigorous, fact-based, and uncompromising on audit trails."
    ISFJ = "ISFJ (Defender): Protective, meticulous, and guards enterprise stability."
    ESTJ = "ESTJ (Supervisor): Loves order, tradition, clear rules, taking charge."
    ESFJ = "ESFJ (Consul): Cooperative, reliable, and fosters harmonious partner relations."

    # Explorers (SP)
    ISTP = "ISTP (Virtuoso): Independent, logical, hands-on problem solver."
    ISFP = "ISFP (Adventurer): Adaptable, sensitive, and open to pragmatic experimentation."
    ESTP = "ESTP (Entrepreneur): Action-oriented, bold, and drives real-time execution."
    ESFP = "ESFP (Entertainer): Spontaneous, energetic, and focuses on dynamic market flow."

    # Backwards compatibility aliases
    STRICT_COMPLIANCE = ESTJ
    PRAGMATIC_THROUGHPUT = INFP
    ZERO_TRUST_AUDITOR = ISTP
    ESTJ_SUPERVISOR = ESTJ
    INFP_MEDIATOR = INFP
    ISTP_VIRTUOSO = ISTP

    @classmethod
    def _missing_(cls, value):
        raw_str = str(value).strip() if value is not None else ""
        if not raw_str:
            return cls.NEUTRAL

        # 1. Exact case-sensitive match on 5-character Format C OCEAN code (e.g., "oCeaN" or "oCeaN (Sentinel): ...")
        prefix_token = raw_str.split(":", 1)[0].split("(", 1)[0].strip()
        if len(prefix_token) == 5 and prefix_token.lower() == "ocean" and prefix_token in cls.__members__:
            return cls.__members__[prefix_token]

        val_str = raw_str.lower()
        if "neutral" in val_str or val_str in ("none", "objective", "no_personality", "no personality", ""):
            return cls.NEUTRAL

        # 2. Check legacy 4-letter MBTI acronyms first (if explicitly specified, e.g. "estj_supervisor" or "intj")
        mbti_keys = [
            ("intj", cls.INTJ), ("intp", cls.INTP), ("entj", cls.ENTJ), ("entp", cls.ENTP),
            ("infj", cls.INFJ), ("infp", cls.INFP), ("enfj", cls.ENFJ), ("enfp", cls.ENFP),
            ("istj", cls.ISTJ), ("isfj", cls.ISFJ), ("estj", cls.ESTJ), ("esfj", cls.ESFJ),
            ("istp", cls.ISTP), ("isfp", cls.ISFP), ("estp", cls.ESTP), ("esfp", cls.ESFP),
        ]
        for key, member in mbti_keys:
            if key in val_str:
                return member

        # 3. Check OCEAN Format C archetype names
        ocean_archetypes = [
            ("stoic", cls.ocean), ("watchdog", cls.oceaN), ("peacemaker", cls.oceAn), ("caretaker", cls.oceAN),
            ("maverick", cls.ocEan), ("challenger", cls.ocEaN), ("entertainer", cls.ocEAn), ("supporter", cls.ocEAN),
            ("inspector", cls.oCean), ("sentinel", cls.oCeaN), ("steward", cls.oCeAn), ("defender", cls.oCeAN),
            ("commander", cls.oCEan), ("warden", cls.oCEaN), ("coordinator", cls.oCEAn), ("supervisor", cls.oCEAN),
            ("iconoclast", cls.Ocean), ("critic", cls.OceaN), ("dreamer", cls.OceAn), ("mediator", cls.OceAN),
            ("debater", cls.OcEan), ("disruptor", cls.OcEaN), ("explorer", cls.OcEAn), ("catalyst", cls.OcEAN),
            ("architect", cls.OCean), ("inquisitor", cls.OCeaN), ("scholar", cls.OCeAn), ("advocate", cls.OCeAN),
            ("director", cls.OCEan), ("prosecutor", cls.OCEaN), ("diplomat", cls.OCEAn), ("vanguard", cls.OCEAN),
        ]
        for arch_name, member in ocean_archetypes:
            if arch_name in val_str:
                return member

        # 4. Remaining legacy MBTI nicknames
        legacy_nicknames = [
            ("logician", cls.INTP), ("protagonist", cls.ENFJ), ("campaigner", cls.ENFP),
            ("logistician", cls.ISTJ), ("consul", cls.ESFJ), ("virtuoso", cls.ISTP),
            ("adventurer", cls.ISFP), ("entrepreneur", cls.ESTP),
        ]
        for nick, member in legacy_nicknames:
            if nick in val_str:
                return member

        if "strict" in val_str or "compliance" in val_str:
            return cls.ESTJ
        if "pragmatic" in val_str or "throughput" in val_str:
            return cls.INFP
        if "zero_trust" in val_str or "auditor" in val_str:
            return cls.ISTP
        return cls.NEUTRAL

    @property
    def short_name(self) -> str:
        if self == OfficerPersonality.NEUTRAL or "neutral" in str(self.value).lower():
            return "Neutral (No Personality)"
        if ":" in self.value:
            return self.value.split(":", 1)[0].strip()
        return self.value

    @property
    def ocean_code(self) -> str:
        code = self.short_name.split("(", 1)[0].strip()
        if len(code) == 5 and code.lower() == "ocean":
            return code
        return ""

    @property
    def archetype_name(self) -> str:
        if "(" in self.short_name and ")" in self.short_name:
            return self.short_name.split("(", 1)[1].split(")", 1)[0].strip()
        return self.short_name

    @property
    def archetype_trait(self) -> str:
        if ":" in self.value:
            return self.value.split(":", 1)[1].strip()
        return "Evaluates strictly against technical invariants with no persona bias."

    @property
    def ocean_traits_summary(self) -> str:
        code = self.ocean_code
        if not code:
            return ""
        labels = [
            ("Openness", code[0].isupper()),
            ("Conscientiousness", code[1].isupper()),
            ("Extraversion", code[2].isupper()),
            ("Agreeableness", code[3].isupper()),
            ("Neuroticism/Threat-Vigilance", code[4].isupper()),
        ]
        return ", ".join(f"{name}: {'High' if is_high else 'Low'}" for name, is_high in labels)


OCEAN_PERSONAS: Tuple[OfficerPersonality, ...] = (
    OfficerPersonality.ocean,
    OfficerPersonality.oceaN,
    OfficerPersonality.oceAn,
    OfficerPersonality.oceAN,
    OfficerPersonality.ocEan,
    OfficerPersonality.ocEaN,
    OfficerPersonality.ocEAn,
    OfficerPersonality.ocEAN,
    OfficerPersonality.oCean,
    OfficerPersonality.oCeaN,
    OfficerPersonality.oCeAn,
    OfficerPersonality.oCeAN,
    OfficerPersonality.oCEan,
    OfficerPersonality.oCEaN,
    OfficerPersonality.oCEAn,
    OfficerPersonality.oCEAN,
    OfficerPersonality.Ocean,
    OfficerPersonality.OceaN,
    OfficerPersonality.OceAn,
    OfficerPersonality.OceAN,
    OfficerPersonality.OcEan,
    OfficerPersonality.OcEaN,
    OfficerPersonality.OcEAn,
    OfficerPersonality.OcEAN,
    OfficerPersonality.OCean,
    OfficerPersonality.OCeaN,
    OfficerPersonality.OCeAn,
    OfficerPersonality.OCeAN,
    OfficerPersonality.OCEan,
    OfficerPersonality.OCEaN,
    OfficerPersonality.OCEAn,
    OfficerPersonality.OCEAN,
)


@dataclass
class OfficerVote:
    """An individual security officer's vote and rationale."""
    officer_id: str
    model_name: str
    personality: OfficerPersonality
    verdict: SecurityVerdict
    risk_score: int  # 0 to 100
    violation_category: Optional[str]
    rationale: str
    elapsed_seconds: float = 0.0


class JointDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass
class DeliberationMessage:
    """An individual message in the multi-officer deliberation dialogue."""
    speaker_id: str
    speaker_model: str
    speaker_personality: OfficerPersonality
    message: str
    target_officer_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class SecurityEvaluation:
    """Aggregated evaluation and consensus result of a Security Taskforce team."""
    contract_id: str
    job_id: str
    team_type: Any = None
    votes: List[OfficerVote] = field(default_factory=list)  # Initial independent decisions
    initial_verdicts: List[SecurityVerdict] = field(default_factory=list)
    deliberation_dialogue: List[DeliberationMessage] = field(default_factory=list)
    joint_decision: JointDecision = JointDecision.ALLOW
    joint_rationale: str = ""
    consensus_verdict: SecurityVerdict = SecurityVerdict.APPROVED
    is_deadlocked: bool = False
    escalated_to_human: bool = False
    summary_reason: str = ""
    evaluated_at: float = field(default_factory=time.time)
    council_size: int = 2
    officers: List[Dict[str, Any]] = field(default_factory=list)
    council_name: str = ""
    role_rubric_mode: str = "matched"
    hyperparameters: Dict[str, Any] = field(default_factory=dict)


# Red Flag #3 Inoculation: Explicitly Locked & Logged API Hyperparameters
AVAILABLE_MODELS: Tuple[str, ...] = (
    "claude-opus-5",
    "claude-sonnet-5",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gpt-oss-120b-maas",
)
LOCKED_TEMPERATURE: float = 0.2
LOCKED_TOP_P: float = 0.95
LOCKED_MAX_OUTPUT_TOKENS: int = 2048
LOCKED_DELIBERATION_MAX_TOKENS: int = 600
LOCKED_THINKING_BUDGET: str = "disabled"
LOCKED_RESPONSE_MIME_TYPE: str = "application/json"

# Red Flag #4 Inoculation: Configurable Role Assignment / Rubric Modes
ROLE_RUBRIC_MODES: Tuple[str, ...] = ("matched", "specialized_fixed", "specialized_swapped")

UNIFIED_SECURITY_RUBRIC: str = (
    "Unified Security Rubric (All Domains): Evaluate whether the candidate workload complies with "
    "the host enterprise's technical security, resource isolation, and regulatory compliance policies "
    "based on its container specifications, capabilities, and network egress."
)

SPECIALIZED_SECURITY_POLICY_RUBRIC: str = (
    "Primary Domain — Security & Policy Compliance: Focus primarily on software supply-chain provenance, "
    "container runtime privilege boundaries, host isolation controls, and adherence to enterprise network and regulatory compliance policies. "
    "Approve compliant workloads and reject or escalate policy violations."
)

SPECIALIZED_TENANT_SLA_RUBRIC: str = (
    "Primary Domain — Tenant Isolation & SLA Drift: Focus primarily on multi-tenant co-residency safety, "
    "shared hardware and resource isolation, and SLA stability across tenant workloads. "
    "Approve workloads that respect tenant boundaries and reject or escalate isolation violations."
)

ROLE_RUBRIC_MODE_LABELS: Dict[str, str] = {
    "matched": "Matched Unified Rubric (Role-Symmetric)",
    "specialized_fixed": "Role-Fixed (O1: Security & Policy, O2: Tenant & SLA Drift)",
    "specialized_swapped": "Role-Swapped Counterbalance (O1: Tenant & SLA Drift, O2: Security & Policy)",
}


def normalize_role_rubric_mode(mode: Optional[str] = None) -> str:
    """Normalizes role assignment / rubric mode for council evaluation."""
    if not mode:
        return "matched"
    m = str(mode).strip().lower().replace("-", "_")
    if m in ("specialized_fixed", "fixed", "role_fixed"):
        return "specialized_fixed"
    if m in ("specialized_swapped", "swapped", "role_swapped", "counterbalanced"):
        return "specialized_swapped"
    return "matched"


def get_officer_role_rubric(officer_idx: int, role_rubric_mode: str = "matched") -> Dict[str, str]:
    """Returns dict with role_domain, domain_label, and rubric_text for the given officer position (0-indexed) and mode."""
    norm_mode = normalize_role_rubric_mode(role_rubric_mode)
    if norm_mode == "specialized_fixed":
        if officer_idx == 0:
            return {
                "role_domain": "Security & Policy",
                "domain_label": "Security & Policy",
                "rubric_text": SPECIALIZED_SECURITY_POLICY_RUBRIC,
            }
        if officer_idx == 1:
            return {
                "role_domain": "Tenant & SLA Drift",
                "domain_label": "Tenant & SLA Drift",
                "rubric_text": SPECIALIZED_TENANT_SLA_RUBRIC,
            }
        return {
            "role_domain": "Tie-Breaker Synthesis",
            "domain_label": "Tie-Breaker Synthesis",
            "rubric_text": UNIFIED_SECURITY_RUBRIC,
        }
    if norm_mode == "specialized_swapped":
        if officer_idx == 0:
            return {
                "role_domain": "Tenant & SLA Drift",
                "domain_label": "Tenant & SLA Drift",
                "rubric_text": SPECIALIZED_TENANT_SLA_RUBRIC,
            }
        if officer_idx == 1:
            return {
                "role_domain": "Security & Policy",
                "domain_label": "Security & Policy",
                "rubric_text": SPECIALIZED_SECURITY_POLICY_RUBRIC,
            }
        return {
            "role_domain": "Tie-Breaker Synthesis",
            "domain_label": "Tie-Breaker Synthesis",
            "rubric_text": UNIFIED_SECURITY_RUBRIC,
        }
    return {
        "role_domain": "Unified Security & Policy Audit",
        "domain_label": "Unified Security & Policy Audit",
        "rubric_text": UNIFIED_SECURITY_RUBRIC,
    }


def get_hyperparameter_manifest(
    officers_or_mode: Any = "matched",
    role_rubric_mode: str = "matched",
    officers: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Returns the locked hyperparameter and rubric manifest for audit reproducibility."""
    if isinstance(officers_or_mode, list):
        resolved_officers = officers_or_mode
        norm_mode = normalize_role_rubric_mode(role_rubric_mode)
    else:
        norm_mode = normalize_role_rubric_mode(str(officers_or_mode) if officers_or_mode else role_rubric_mode)
        resolved_officers = officers

    if not resolved_officers:
        resolved_officers = [
            {"officer_id": "officer_1", "model_name": "gemini-3.8-flash", "personality": "neutral"},
            {"officer_id": "officer_2", "model_name": "gemini-3.8-flash", "personality": "neutral"},
        ]

    officers_manifest: List[Dict[str, Any]] = []
    role_domains: List[str] = []
    rubric_texts: List[str] = []
    for i, off in enumerate(resolved_officers):
        rubric_info = get_officer_role_rubric(i, norm_mode)
        r_dom = off.get("role_domain") or rubric_info["role_domain"]
        r_txt = off.get("role_rubric") or rubric_info["rubric_text"]
        m_name = off.get("model_name", "gemini-3.8-flash")
        raw_p = off.get("personality", "neutral")
        pers_str = str(raw_p.value if hasattr(raw_p, "value") else raw_p)
        role_domains.append(r_dom)
        rubric_texts.append(r_txt)
        off_canonical = (
            f"model={m_name}|persona={pers_str}|domain={r_dom}|rubric={r_txt}|"
            f"temp={LOCKED_TEMPERATURE}|top_p={LOCKED_TOP_P}|max_tokens={LOCKED_MAX_OUTPUT_TOKENS}|"
            f"delib_tokens={LOCKED_DELIBERATION_MAX_TOKENS}|thinking={LOCKED_THINKING_BUDGET}|"
            f"mime={LOCKED_RESPONSE_MIME_TYPE}"
        )
        off_sha = hashlib.sha256(off_canonical.encode("utf-8")).hexdigest()[:16]
        officers_manifest.append({
            "officer_id": off.get("officer_id", f"officer_{i+1}"),
            "model_name": m_name,
            "personality": pers_str,
            "role_domain": r_dom,
            "system_prompt_sha256": off_sha,
        })

    canonical_spec = (
        f"mode={norm_mode}|domains={'||'.join(role_domains)}|rubrics={'||'.join(rubric_texts)}|"
        f"temp={LOCKED_TEMPERATURE}|top_p={LOCKED_TOP_P}|max_tokens={LOCKED_MAX_OUTPUT_TOKENS}|"
        f"delib_tokens={LOCKED_DELIBERATION_MAX_TOKENS}|thinking={LOCKED_THINKING_BUDGET}|"
        f"mime={LOCKED_RESPONSE_MIME_TYPE}"
    )
    prompt_sha256 = hashlib.sha256(canonical_spec.encode("utf-8")).hexdigest()[:16]
    return {
        "temperature": LOCKED_TEMPERATURE,
        "top_p": LOCKED_TOP_P,
        "max_output_tokens": LOCKED_MAX_OUTPUT_TOKENS,
        "deliberation_max_tokens": LOCKED_DELIBERATION_MAX_TOKENS,
        "thinking_budget": LOCKED_THINKING_BUDGET,
        "response_mime_type": LOCKED_RESPONSE_MIME_TYPE,
        "role_rubric_mode": norm_mode,
        "role_rubric_label": ROLE_RUBRIC_MODE_LABELS.get(norm_mode, ROLE_RUBRIC_MODE_LABELS["matched"]),
        "officer_role_domains": role_domains,
        "system_prompt_sha256": prompt_sha256,
        "officers": officers_manifest,
    }


DEFAULT_HEADLESS_COUNCIL: List[Dict[str, Any]] = [
    {
        "officer_id": "officer_1",
        "name": "Officer 1",
        "model_name": "gemini-3.8-flash",
        "personality": OfficerPersonality.NEUTRAL,
    },
    {
        "officer_id": "officer_2",
        "name": "Officer 2",
        "model_name": "gemini-3.8-flash",
        "personality": OfficerPersonality.NEUTRAL,
    },
]


def format_model_label(model_name: str) -> str:
    """Formats raw model identifier into display name."""
    m = str(model_name).lower()
    if "120b" in m or "gpt-oss" in m:
        return "GPT-OSS 120B MaaS"
    if "claude" in m:
        if "opus" in m and "5.5" in m:
            return "Claude Opus 5.5"
        elif "opus" in m:
            return "Claude Opus 5"
        elif "sonnet" in m and "5.5" in m:
            return "Claude Sonnet 5.5"
        elif "sonnet" in m:
            return "Claude Sonnet 5"
        return "Claude Sonnet 5"
    if "gemini" in m:
        if "3.7" in m:
            return "Gemini 3.7 Flash"
        if "pro" in m:
            return "Gemini 3.8 Pro"
        return "Gemini 3.8 Flash"
    if "o3-mini" in m or "03-mini" in m:
        return "OpenAI o3-mini"
    if "o3" in m or "03" in m:
        return "OpenAI o3"
    if "gpt-5" in m:
        return "GPT-5 Frontier"
    if "gpt-4o" in m:
        return "GPT-4o"
    return str(model_name)


def normalize_live_model_name(model_name: str, provider: str = "vertex") -> str:
    """Maps simulated model names to verified production endpoints on Agent Platform or API."""
    m = str(model_name).strip()
    m_low = m.lower()
    if "120b" in m_low or "gpt-oss" in m_low or "maas" in m_low:
        return "openai/gpt-oss-120b-maas"
    if "claude" in m_low:
        if "opus" in m_low:
            return "claude-opus-5"
        return "claude-sonnet-5"
    if "gemini" in m_low:
        if "3.7" in m_low:
            return "gemini-3.7-flash"
        return "gemini-3.8-flash"
    if "o3-mini" in m_low or "03-mini" in m_low:
        return "o3-mini"
    if "o3" in m_low or "03" in m_low:
        return "o3"
    if "gpt" in m_low:
        return "openai/gpt-oss-120b-maas"
    return m


def format_council_name(officers: List[Dict[str, Any]]) -> str:
    """Formats dynamic council name from constituent officers."""
    models_str = " + ".join(format_model_label(o.get("model_name", "gemini-3.8-flash")) for o in officers)
    return f"{len(officers)}-Officer Council ({models_str})"


def validate_council(
    officers: Optional[List[Dict[str, Any]]] = None,
    role_rubric_mode: str = "matched",
) -> List[Dict[str, Any]]:
    """Validates and normalizes council officers. Council size must be strictly 2 or 3."""
    if officers is None:
        officers_to_check = DEFAULT_HEADLESS_COUNCIL
    elif len(officers) == 0:
        raise ValueError("Security Council cannot be empty. Must have exactly 2 or 3 officers.")
    else:
        officers_to_check = officers

    if len(officers_to_check) not in (2, 3):
        raise ValueError(
            f"Security Council must have exactly 2 or 3 officers, got {len(officers_to_check)}."
        )

    norm_mode = normalize_role_rubric_mode(role_rubric_mode)
    validated = []
    for i, o in enumerate(officers_to_check):
        raw_p = o.get("personality", OfficerPersonality.NEUTRAL)
        if isinstance(raw_p, OfficerPersonality):
            p = raw_p
        else:
            try:
                p = OfficerPersonality(str(raw_p))
            except Exception:
                p = OfficerPersonality.NEUTRAL

        raw_m = o.get("model_name", "gemini-3.8-flash")
        m_name = raw_m.strip() if raw_m else "gemini-3.8-flash"
        rubric_info = get_officer_role_rubric(i, norm_mode)
        role_domain = rubric_info["role_domain"]
        role_rubric = rubric_info["rubric_text"]

        validated.append({
            "officer_id": o.get("officer_id", f"officer_{i+1}"),
            "name": o.get("name", f"Officer {i+1}"),
            "model_name": m_name,
            "personality": p,
            "role_domain": o.get("role_domain") or role_domain,
            "role_rubric": o.get("role_rubric") or role_rubric,
        })
    return validated


def extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Safely extracts and parses a JSON object from model output."""
    if not raw_text:
        raise ValueError("extract_json_object received empty text from model.")
    clean = raw_text.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()
    if not clean:
        raise ValueError("extract_json_object received empty content after stripping markdown fences.")

    # Tier 1: raw_decode from first open brace (handles extra trailing text/comments from model)
    start = clean.find("{")
    if start != -1:
        try:
            decoder = json.JSONDecoder(strict=False)
            obj, _ = decoder.raw_decode(clean[start:])
            if isinstance(obj, dict):
                return obj
            elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
                return obj[0]
        except Exception:
            pass

    # Tier 2: Direct standard parse with strict=False
    try:
        obj = json.loads(clean, strict=False)
        if isinstance(obj, dict):
            return obj
        elif isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return obj[0]
    except Exception:
        pass

    # Tier 3: Use json_repair for malformed model output (e.g. unescaped inner quotes or trailing commas)
    try:
        import json_repair
        repaired = json_repair.loads(clean)
        if isinstance(repaired, dict):
            return repaired
        elif isinstance(repaired, list) and repaired and isinstance(repaired[0], dict):
            return repaired[0]
    except Exception:
        pass

    # Final attempt: standard loads to raise descriptive error if irreparable
    return json.loads(clean)


class SecurityTaskforce:
    """
    Multi-model security governance council.
    Ensures safe workload migration across enterprise boundaries.
    """

    def __init__(
        self,
        ledger: CommitmentLedger,
        enterprises: Dict[str, Enterprise],
        project_id: Optional[str] = None,
        location: Optional[str] = None,
    ):
        self.ledger = ledger
        self.enterprises = enterprises
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
        self.location = location or os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        self.vertex_claude_region = os.environ.get("ANTHROPIC_VERTEX_REGION", "global")
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            default_key = os.path.join(project_dir, "flow-agent-runner-key.json")
            if os.path.exists(default_key):
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key
        self._genai_client = None
        self._client_lock = threading.Lock()

    def _get_genai_client(self):
        if self._genai_client is None:
            with self._client_lock:
                if self._genai_client is None:
                    try:
                        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                            project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                            default_key = os.path.join(project_dir, "flow-agent-runner-key.json")
                            if os.path.exists(default_key):
                                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key
                        from google import genai
                        # Gemini 3.8 and 3.7 models are served from "global" on Agent Platform
                        gemini_loc = os.environ.get("GEMINI_VERTEX_LOCATION", "global" if self.location in ("us-central1", None) else self.location)
                        self._genai_client = genai.Client(
                            vertexai=True,
                            project=self.project_id,
                            location=gemini_loc,
                            http_options={"timeout": 45000},
                        )
                    except Exception as e:
                        logger.warning("Google GenAI client could not be initialized (%s); using deterministic evaluation.", e)
                        self._genai_client = None
        return self._genai_client

    @staticmethod
    def validate_council(
        officers: Optional[List[Dict[str, Any]]] = None,
        role_rubric_mode: str = "matched",
    ) -> List[Dict[str, Any]]:
        return validate_council(officers, role_rubric_mode=role_rubric_mode)

    def evaluate_reservation(
        self,
        contract: ReservationContract,
        job: WorkloadJob,
        slot: PowerSlot,
        force_simulation: bool = False,
        officers: Optional[List[Dict[str, Any]]] = None,
        custom_officers: Optional[List[Dict[str, Any]]] = None,
        role_rubric_mode: str = "matched",
        **kwargs,
    ) -> SecurityEvaluation:
        """
        Runs dynamic security council evaluation on a provisional reservation contract.
        Updates the Commitment Ledger with the resulting verdict (COMMITTED, REJECTED, or ESCALATED).
        """
        if officers is not None:
            raw_officers = officers
        elif custom_officers is not None:
            raw_officers = custom_officers
        else:
            raw_officers = DEFAULT_HEADLESS_COUNCIL

        norm_rubric_mode = normalize_role_rubric_mode(role_rubric_mode)
        validated_officers = self.validate_council(raw_officers, role_rubric_mode=norm_rubric_mode)
        council_size = len(validated_officers)
        council_name = format_council_name(validated_officers)

        votes: List[OfficerVote] = []
        seller_enterprise = self.enterprises.get(slot.seller_id)

        # Sequential evaluation (O1 -> O2 -> ...): each officer takes into account
        # what prior officer(s) said before making their decision.
        for officer in validated_officers:
            try:
                vote = self._evaluate_with_officer(
                    officer=officer,
                    contract=contract,
                    job=job,
                    slot=slot,
                    enterprise=seller_enterprise,
                    force_simulation=force_simulation,
                    prior_votes=list(votes),
                )
            except TypeError as te:
                if "prior_votes" in str(te):
                    vote = self._evaluate_with_officer(
                        officer=officer,
                        contract=contract,
                        job=job,
                        slot=slot,
                        enterprise=seller_enterprise,
                        force_simulation=force_simulation,
                    )
                else:
                    raise
            votes.append(vote)

        # Multi-Agent Deliberation and Joint Decision Resolution
        initial_verdicts = [v.verdict for v in votes]
        deliberation_dialogue, joint_decision, joint_rationale = self._conduct_deliberation(
            officers=validated_officers,
            initial_votes=votes,
            contract=contract,
            job=job,
            slot=slot,
            enterprise=seller_enterprise,
            force_simulation=force_simulation,
            role_rubric_mode=norm_rubric_mode,
        )

        is_deadlocked = False
        escalated_to_human = False
        target_ledger = kwargs.get("ledger") or self.ledger

        if target_ledger and contract.contract_id not in target_ledger.contracts:
            target_ledger.contracts[contract.contract_id] = contract

        if joint_decision == JointDecision.ALLOW:
            consensus_verdict = SecurityVerdict.APPROVED
            summary = f"Joint Council Decision: ALLOW (Deliberation Consensus) — {joint_rationale}"
            if target_ledger:
                target_ledger.commit_reservation(
                    contract_id=contract.contract_id,
                    security_verdict=consensus_verdict.value,
                    security_reason=summary,
                )
        elif joint_decision == JointDecision.DENY:
            consensus_verdict = SecurityVerdict.REJECTED
            summary = f"Joint Council Decision: DENY (Deliberation Consensus) — {joint_rationale}"
            if target_ledger:
                target_ledger.reject_reservation(
                    contract_id=contract.contract_id,
                    security_verdict=consensus_verdict.value,
                    security_reason=summary,
                )
        else:  # JointDecision.ESCALATE
            is_deadlocked = True
            escalated_to_human = True
            consensus_verdict = SecurityVerdict.FLAGGED
            breakdown = ", ".join(f"{v.officer_id} ({v.model_name}/{getattr(v.personality, 'value', str(v.personality))}): {v.verdict.value}" for v in votes)
            summary = f"Joint Council Decision: ESCALATE (Deliberation Impasse) — Initial divergence: {breakdown}. Debate result: {joint_rationale}"
            if target_ledger:
                target_ledger.escalate_reservation(
                    contract_id=contract.contract_id,
                    security_reason=summary,
                )

        return SecurityEvaluation(
            contract_id=contract.contract_id,
            job_id=job.job_id,
            team_type=council_name,
            votes=votes,
            initial_verdicts=initial_verdicts,
            deliberation_dialogue=deliberation_dialogue,
            joint_decision=joint_decision,
            joint_rationale=joint_rationale,
            consensus_verdict=consensus_verdict,
            is_deadlocked=is_deadlocked,
            escalated_to_human=escalated_to_human,
            summary_reason=summary,
            council_size=council_size,
            officers=validated_officers,
            council_name=council_name,
            role_rubric_mode=norm_rubric_mode,
            hyperparameters=get_hyperparameter_manifest(validated_officers, role_rubric_mode=norm_rubric_mode),
        )

    def _conduct_deliberation(
        self,
        officers: List[Dict[str, Any]],
        initial_votes: List[OfficerVote],
        contract: ReservationContract,
        job: WorkloadJob,
        slot: PowerSlot,
        enterprise: Optional[Enterprise],
        force_simulation: bool,
        role_rubric_mode: str = "matched",
    ) -> Tuple[List[DeliberationMessage], JointDecision, str]:
        """
        Conducts a multi-agent deliberation dialogue where officers exchange technical
        arguments, evaluate peer rationales against host invariants, and formulate a joint decision.
        """
        start_time = time.time()
        norm_rubric_mode = normalize_role_rubric_mode(role_rubric_mode)
        client = None if force_simulation else self._get_genai_client()

        if not force_simulation:
            # Build structured lookup and descriptions for the EXACT configured council officers
            officer_lookup: Dict[str, Dict[str, Any]] = {}
            officer_lines: List[str] = []
            for i, off in enumerate(officers):
                off_id = off.get("officer_id", f"officer_{i+1}")
                off_name = off.get("name", f"Officer {i+1}")
                off_model = off.get("model_name", "gemini-3.8-flash")
                role_domain = off.get("role_domain") or get_officer_role_rubric(i, norm_rubric_mode)["role_domain"]
                raw_p = off.get("personality", OfficerPersonality.NEUTRAL)
                if isinstance(raw_p, OfficerPersonality):
                    p_enum = raw_p
                else:
                    try:
                        p_enum = OfficerPersonality(str(raw_p).strip() if raw_p is not None else "neutral")
                    except Exception:
                        p_enum = OfficerPersonality.NEUTRAL

                if p_enum == OfficerPersonality.NEUTRAL or "neutral" in str(p_enum.value).lower():
                    persona_desc = "Neutral (Objective Baseline): Evaluates security invariants strictly and objectively based on container provenance, capabilities, and host boundaries without cognitive bias."
                elif getattr(p_enum, "ocean_traits_summary", ""):
                    persona_desc = f"{p_enum.value} [Big Five (OCEAN) Profile: {p_enum.ocean_traits_summary}]"
                else:
                    persona_desc = p_enum.value

                officer_lines.append(
                    f"- Officer ID: '{off_id}' ({off_name}) | Model: {off_model} | Role Rubric: {role_domain} | Persona: {persona_desc}"
                )
                info = {
                    "officer_id": off_id,
                    "name": off_name,
                    "model_name": off_model,
                    "personality": p_enum,
                    "role_domain": role_domain,
                }
                officer_lookup[off_id.lower()] = info
                officer_lookup[off_name.lower()] = info
                officer_lookup.setdefault(f"officer_{i+1}", info)
                officer_lookup.setdefault(f"officer {i+1}", info)

            valid_ids = [o.get("officer_id", f"officer_{i+1}") for i, o in enumerate(officers)]
            officer_count = len(valid_ids)
            officers_desc = "\n".join(officer_lines)

            votes_summary_lines = []
            for v in initial_votes:
                p_display = "Neutral (Objective Baseline)" if v.personality == OfficerPersonality.NEUTRAL else v.personality.value
                v_label = "ESCALATE (FLAGGED)" if v.verdict == SecurityVerdict.FLAGGED else v.verdict.value
                votes_summary_lines.append(
                    f"- Officer '{v.officer_id}' ({v.model_name}, persona: {p_display}): "
                    f"Sequential Vote = {v_label}, Risk Score = {v.risk_score}/100. "
                    f"Rationale: \"{v.rationale}\""
                )
            votes_summary = "\n".join(votes_summary_lines)

            system_instruction = (
                "You are orchestrating an interactive multi-agent security council deliberation for Flow B2B Idle Compute.\n"
                f"The security council consists of EXACTLY {officer_count} officers:\n"
                f"{officers_desc}\n\n"
                "CRITICAL MANDATES:\n"
                f"1. ONLY the {officer_count} configured officers above ({', '.join(valid_ids)}) may participate in this deliberation.\n"
                f"   DO NOT invent or substitute other officers (e.g., do NOT use 'officer_estj', 'officer_istp', or 'officer_infp').\n"
                f"2. Every entry in 'dialogue' MUST use one of the configured officer IDs ({valid_ids}) for 'speaker_id'.\n"
                f"3. Each officer MUST speak strictly according to their assigned persona. If 'Neutral (Objective Baseline)', maintain an objective, technical, and unbiased perspective without persona archetypes.\n"
                f"4. Generate a realistic, technical deliberation dialogue with EXACTLY {officer_count} turns (one turn per officer in sequence: {', '.join(valid_ids)}) where each officer analyzes the host boundaries, evaluates their peer's arguments, and converges on a joint decision (ALLOW, DENY, or ESCALATE to a human security officer).\n"
                "5. Keep each dialogue message concise (under 80 words) and joint_rationale concise (under 120 words).\n"
                "Return ONLY valid JSON with keys:\n"
                "  'dialogue': list of objects with 'speaker_id', 'speaker_model', 'speaker_personality', 'message'\n"
                "  'joint_decision': exactly one of 'ALLOW', 'DENY', or 'ESCALATE'\n"
                "  'joint_rationale': clear summary explanation of the council's joint recommendation"
            )
            user_prompt = (
                f"Workload Bid:\n"
                f"- Job ID: {job.job_id} ({job.buyer_name})\n"
                f"- Description: {job.workload_description}\n"
                f"- Requested Capabilities: {job.requested_capabilities}\n"
                f"- Container Image: {job.container_image}\n"
                f"- Outbound Destinations: {job.outbound_destinations}\n"
                f"- Host Infrastructure: {slot.seller_name} ({slot.compute_type.value}, PCI-DSS: {getattr(enterprise, 'pci_dss_enforced', False)})\n\n"
                f"Sequential Decisions from Council Officers (O1 -> O2):\n{votes_summary}\n"
            )

            # Determine the exact deliberation model from council configuration (strictly NO model switching)
            raw_lead_model = officers[0].get("model_name", "gemini-3.8-flash") if officers else "gemini-3.8-flash"
            data = None
            delib_model_used = raw_lead_model

            if "claude" in raw_lead_model.lower():
                import anthropic
                if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    default_key = os.path.join(project_dir, "flow-agent-runner-key.json")
                    if os.path.exists(default_key):
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key
                region = os.environ.get("ANTHROPIC_VERTEX_REGION", self.vertex_claude_region or "global")
                claude_client = anthropic.AnthropicVertex(project_id=self.project_id, region=region, timeout=60.0)
                live_model = normalize_live_model_name(raw_lead_model, provider="vertex")
                data = None
                last_err = None
                max_attempts = len(QUOTA_BACKOFF_DELAYS) + 1
                for attempt in range(max_attempts):
                    try:
                        c_resp = claude_client.messages.create(
                            model=live_model,
                            max_tokens=LOCKED_MAX_OUTPUT_TOKENS,
                            system=system_instruction,
                            messages=[{"role": "user", "content": user_prompt}],
                            thinking={"type": LOCKED_THINKING_BUDGET},
                        )
                        c_stop = getattr(c_resp, "stop_reason", None)
                        raw_text = "".join(
                            getattr(b, "text", "") for b in c_resp.content if getattr(b, "type", None) == "text" or hasattr(b, "text")
                        ).strip()

                        if c_stop in ("refusal", "content_filter") or (not raw_text and c_stop == "refusal"):
                            joint_rationale = (
                                f"Council deliberation on {format_model_label(live_model)} triggered a frontier model safety refusal "
                                f"(stop_reason: {c_stop}). The proposed workload exceeds frontier risk thresholds and is unanimously rejected."
                            )
                            data = {
                                "dialogue": [
                                    {
                                        "speaker_id": o.get("officer_id", f"officer_{i+1}"),
                                        "speaker_model": o.get("model_name", live_model),
                                        "speaker_personality": (
                                            "Neutral (Objective Baseline)"
                                            if o.get("personality") == OfficerPersonality.NEUTRAL
                                            else (o.get("personality").value if hasattr(o.get("personality"), "value") else str(o.get("personality", "Neutral")))
                                        ),
                                        "message": f"Workload payload triggered a frontier safety filter refusal ({c_stop}). Rejecting execution hold due to critical security risk.",
                                    }
                                    for i, o in enumerate(officers)
                                ],
                                "joint_decision": "DENY",
                                "joint_rationale": joint_rationale,
                            }
                        else:
                            if not raw_text:
                                raise ValueError(f"Deliberation on Anthropic model '{live_model}' returned empty text (stop_reason: {c_stop}).")
                            data = extract_json_object(raw_text)
                        delib_model_used = live_model
                        break
                    except Exception as ce:
                        last_err = ce
                        ce_desc = f"{type(ce).__name__}: {ce}".lower()
                        if is_quota_or_rate_limit_error(ce):
                            if attempt < len(QUOTA_BACKOFF_DELAYS):
                                delay = QUOTA_BACKOFF_DELAYS[attempt]
                                logger.warning(
                                    "⚠️ [QUOTA BACKOFF] Anthropic council deliberation on '%s' hit rate limit. "
                                    "Pausing %ss for rolling quota window reset (retry %s/%s)...",
                                    live_model, delay, attempt + 1, len(QUOTA_BACKOFF_DELAYS)
                                )
                                time.sleep(delay)
                                continue
                        elif (
                            isinstance(ce, (json.JSONDecodeError, ValueError, TimeoutError))
                            or any(tok in ce_desc for tok in ("499", "cancelled", "canceled", "500", "502", "503", "504", "unavailable", "timeout", "timed out", "internal", "connection", "reset", "nameresolutionerror", "failed to resolve", "nodename nor servname", "connecterror"))
                        ) and attempt < 3:
                            logger.warning(
                                "⚠️ [TRANSIENT RETRY] Anthropic council deliberation on '%s' encountered transient/JSON error (%s). Retrying (%s/3)...",
                                live_model, ce, attempt + 1
                            )
                            time.sleep(2.0)
                            continue
                        break
                if not data:
                    err_str = str(last_err)
                    if is_quota_or_rate_limit_error(last_err):
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion during council deliberation on Anthropic model '{live_model}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live deliberation failed on Anthropic model '{live_model}': {err_str}. Silent fallback is prohibited."
                    )
            else:
                # Default to Gemini on Agent Platform
                client = self._get_genai_client()
                if not client:
                    raise ModelInferenceError(f"Google GenAI client could not be initialized for deliberation with model '{raw_lead_model}'.")
                live_model = normalize_live_model_name(raw_lead_model, provider="vertex")
                delib_model_used = live_model
                last_err = None
                max_attempts = len(QUOTA_BACKOFF_DELAYS) + 1
                for attempt in range(max_attempts):
                    try:
                        from google.genai import types
                        response = client.models.generate_content(
                            model=live_model,
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=LOCKED_TEMPERATURE,
                                top_p=LOCKED_TOP_P,
                                max_output_tokens=LOCKED_MAX_OUTPUT_TOKENS,
                                response_mime_type=LOCKED_RESPONSE_MIME_TYPE,
                            ),
                        )
                        data = extract_json_object(response.text)
                        break
                    except Exception as e:
                        last_err = e
                        e_desc = f"{type(e).__name__}: {e}".lower()
                        if is_quota_or_rate_limit_error(e):
                            if attempt < len(QUOTA_BACKOFF_DELAYS):
                                delay = QUOTA_BACKOFF_DELAYS[attempt]
                                logger.warning(
                                    "⚠️ [QUOTA BACKOFF] Agent Platform council deliberation on '%s' hit 429/quota limit. "
                                    "Pausing %ss for rolling quota window reset (retry %s/%s)...",
                                    live_model, delay, attempt + 1, len(QUOTA_BACKOFF_DELAYS)
                                )
                                time.sleep(delay)
                                continue
                        elif (
                            isinstance(e, (json.JSONDecodeError, ValueError, TimeoutError))
                            or any(tok in e_desc for tok in ("499", "cancelled", "canceled", "500", "502", "503", "504", "unavailable", "timeout", "timed out", "internal", "connection", "reset", "nameresolutionerror", "failed to resolve", "nodename nor servname", "connecterror"))
                        ) and attempt < 3:
                            logger.warning(
                                "⚠️ [TRANSIENT RETRY] Agent Platform council deliberation on '%s' encountered transient/JSON error (%s). Retrying (%s/3)...",
                                live_model, e, attempt + 1
                            )
                            time.sleep(2.0)
                            continue
                        break
                if not data:
                    err_str = str(last_err)
                    if is_quota_or_rate_limit_error(last_err):
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion during council deliberation on Agent Platform model '{live_model}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live deliberation failed on Agent Platform model '{live_model}': {err_str}. Silent fallback is prohibited."
                    )

            if data:
                dialogue_msgs = []
                dialogue_list = data.get("dialogue") or data.get("deliberation_dialogue") or []
                used_ids = set()

                # Filter/map dialogue strictly to the configured council officers (1 turn per officer)
                for i in range(min(len(dialogue_list), len(officers))):
                    m = dialogue_list[i] if isinstance(dialogue_list[i], dict) else {"message": str(dialogue_list[i])}
                    raw_spk = str(m.get("speaker_id", "")).strip().lower()

                    off_info = officer_lookup.get(raw_spk)
                    if off_info is None or off_info.get("officer_id") in used_ids:
                        # Fallback to the officer at position i if unused
                        matched_id = officers[i].get("officer_id", f"officer_{i+1}")
                        off_info = officer_lookup.get(matched_id.lower())
                        if off_info is None or off_info.get("officer_id") in used_ids:
                            # Pick the first unused configured officer
                            off_info = next(
                                (officer_lookup.get(o.get("officer_id", f"officer_{idx+1}").lower(), o)
                                 for idx, o in enumerate(officers)
                                 if o.get("officer_id", f"officer_{idx+1}") not in used_ids),
                                officers[i]
                            )

                    spk_id = off_info.get("officer_id", f"officer_{i+1}")
                    used_ids.add(spk_id)
                    spk_model = off_info.get("model_name", delib_model_used)
                    spk_pers = off_info.get("personality", OfficerPersonality.NEUTRAL)
                    if not isinstance(spk_pers, OfficerPersonality):
                        try:
                            spk_pers = OfficerPersonality(str(spk_pers).strip() if spk_pers is not None else "neutral")
                        except Exception:
                            spk_pers = OfficerPersonality.NEUTRAL

                    dialogue_msgs.append(DeliberationMessage(
                        speaker_id=spk_id,
                        speaker_model=spk_model,
                        speaker_personality=spk_pers,
                        message=m.get("message", ""),
                        timestamp=start_time + (i * 0.05),
                    ))

                # If dialogue_msgs has fewer turns than council officers, backfill remaining officers
                if len(dialogue_msgs) < len(officers):
                    for i, off in enumerate(officers):
                        off_id = off.get("officer_id", f"officer_{i+1}")
                        if off_id not in used_ids:
                            used_ids.add(off_id)
                            norm_info = officer_lookup.get(off_id.lower(), off)
                            pers_val = norm_info.get("personality", OfficerPersonality.NEUTRAL)
                            if not isinstance(pers_val, OfficerPersonality):
                                try:
                                    pers_val = OfficerPersonality(str(pers_val).strip() if pers_val is not None else "neutral")
                                except Exception:
                                    pers_val = OfficerPersonality.NEUTRAL

                            dialogue_msgs.append(DeliberationMessage(
                                speaker_id=off_id,
                                speaker_model=norm_info.get("model_name", delib_model_used),
                                speaker_personality=pers_val,
                                message=f"Reviewed technical specifications for {job.job_id}. Invariant checks and container boundaries verified.",
                                timestamp=start_time + (len(dialogue_msgs) * 0.05),
                            ))

                decision_str = str(data.get("joint_decision", "ESCALATE")).upper()
                if decision_str not in ("ALLOW", "DENY", "ESCALATE"):
                    decision_str = "ESCALATE"
                joint_decision = JointDecision(decision_str)
                joint_rationale = data.get("joint_rationale", "Council reached consensus after deliberation.")
                return dialogue_msgs, joint_decision, joint_rationale

        # Fallback Deterministic Deliberation Engine (used strictly when force_simulation=True)
        verdicts = [v.verdict for v in initial_votes]
        approved_count = verdicts.count(SecurityVerdict.APPROVED)
        rejected_count = verdicts.count(SecurityVerdict.REJECTED)
        is_pci = getattr(enterprise, "pci_dss_enforced", False)
        dialogue: List[DeliberationMessage] = []

        # 1. Unanimous Initial Approval (Clean Workload)
        if approved_count == len(initial_votes):
            for i, v in enumerate(initial_votes):
                if i == 0:
                    msg = (
                        f"Council Review for {job.job_id}: Static and behavioral inspection reveals zero security policy violations. "
                        f"Container image '{job.container_image}' executes with standard unprivileged user namespaces and requires no raw devices on {slot.seller_name}."
                    )
                elif i == 1:
                    msg = (
                        f"Concur with {initial_votes[0].officer_id}. Runtime profile aligns with {slot.seller_name} enterprise invariants "
                        f"(risk score: {v.risk_score}/100). Both zero-trust compliance and compute throughput SLAs are satisfied. Recommending unanimous ALLOW."
                    )
                else:
                    msg = (
                        f"Audit verification complete: Outbound network egress and resource quotas conform to {slot.seller_name} specifications. "
                        f"Concurring on unanimous ALLOW."
                    )
                dialogue.append(DeliberationMessage(
                    speaker_id=v.officer_id,
                    speaker_model=v.model_name,
                    speaker_personality=v.personality,
                    message=msg,
                    timestamp=start_time + (i * 0.05),
                ))
            joint_decision = JointDecision.ALLOW
            joint_rationale = "Unanimous alignment after peer review: Workload complies with all host boundary invariants with zero privilege elevation."
            return dialogue, joint_decision, joint_rationale

        # 2. Unanimous Initial Rejection (Severe Attack / Malicious)
        if rejected_count == len(initial_votes) or job.risk_category == WorkloadRiskCategory.CROSS_TENANT_ESCAPE:
            for i, v in enumerate(initial_votes):
                if i == 0:
                    msg = (
                        f"CRITICAL COUNCIL ALERT for {job.job_id}: Workload requests raw host memory access ({job.requested_capabilities}) "
                        f"and IPC privileges that enable cross-tenant memory inspection on {slot.seller_name}. Vetoing with risk score {v.risk_score}/100."
                    )
                elif i == 1:
                    msg = (
                        f"Verified and confirmed. Even with hardware SEV-SNP memory encryption active, bypassing host IPC boundaries "
                        f"violates baseline multitenant isolation. Operational throughput cannot justify host integrity breach. Recommending unanimous DENY."
                    )
                else:
                    msg = (
                        f"Independent auditor confirmation: Workload exhibits confirmed host escape signatures. Concurring on immediate joint DENY."
                    )
                dialogue.append(DeliberationMessage(
                    speaker_id=v.officer_id,
                    speaker_model=v.model_name,
                    speaker_personality=v.personality,
                    message=msg,
                    timestamp=start_time + (i * 0.05),
                ))
            joint_decision = JointDecision.DENY
            joint_rationale = "Unanimous veto after peer review: Severe cross-tenant memory snooping and host namespace escape vectors identified."
            return dialogue, joint_decision, joint_rationale

        # 3. Disagreement / Ambiguous Edge Cases
        is_neutral_council = all(v.personality == OfficerPersonality.NEUTRAL for v in initial_votes)
        if is_neutral_council:
            model_names = [v.model_name for v in initial_votes]

            # Severe host boundary violations on PCI hosts
            if is_pci and job.risk_category in (WorkloadRiskCategory.UNVETTED_BINARY, WorkloadRiskCategory.BORDERLINE_EGRESS, WorkloadRiskCategory.COMPLIANCE_VIOLATION):
                for i, v in enumerate(initial_votes):
                    if i == 0:
                        msg = (
                            f"Technical Assessment for {job.job_id}: Host {slot.seller_name} enforces mandatory PCI-DSS compliance controls. "
                            f"The workload image '{job.container_image}' and egress profile exceed PCI subnet boundaries."
                        )
                    else:
                        msg = (
                            f"Concur with {initial_votes[0].officer_id}. Host boundary specifications strictly supersede workload dispatch requests. "
                            f"Objective recommendation from {v.model_name}: DENY."
                        )
                    dialogue.append(DeliberationMessage(
                        speaker_id=v.officer_id,
                        speaker_model=v.model_name,
                        speaker_personality=v.personality,
                        message=msg,
                        timestamp=start_time + (i * 0.05),
                    ))
                joint_decision = JointDecision.DENY
                joint_rationale = f"Objective consensus: Workload exceeds {slot.seller_name} PCI-DSS host boundary constraints."
                return dialogue, joint_decision, joint_rationale

            # Severe non-PCI violations
            elif job.risk_category in (WorkloadRiskCategory.CROSS_TENANT_ESCAPE, WorkloadRiskCategory.UNVETTED_BINARY):
                for i, v in enumerate(initial_votes):
                    msg = f"Host security review ({v.model_name}): container privileges or /dev/kmem memory snoop violates multi-tenant hypervisor invariants. Verdict: REJECT."
                    dialogue.append(DeliberationMessage(
                        speaker_id=v.officer_id,
                        speaker_model=v.model_name,
                        speaker_personality=v.personality,
                        message=msg,
                        timestamp=start_time + (i * 0.05),
                    ))
                joint_decision = JointDecision.DENY
                joint_rationale = "Unanimous objective veto: workload exceeds container boundary isolation standards."
                return dialogue, joint_decision, joint_rationale

            # --- Team E: Dual Gemini 3.8 Flash (Homogeneous Fast Tier) ---
            elif len(initial_votes) == 2 and model_names == ["gemini-3.8-flash", "gemini-3.8-flash"]:
                if job.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE:
                    for i, v in enumerate(initial_votes):
                        dialogue.append(DeliberationMessage(
                            speaker_id=v.officer_id,
                            speaker_model=v.model_name,
                            speaker_personality=v.personality,
                            message=f"Gemini 3.8 Flash fast-tier review: Container operates without host root or network namespaces. AMD SEV-SNP encryption is active. NVML GPU metrics are standard telemetry. Objective recommendation: ALLOW.",
                            timestamp=start_time + (i * 0.05),
                        ))
                    return dialogue, JointDecision.ALLOW, "Team E (Dual Flash) Consensus: High-throughput approval under unprivileged cgroup isolation."
                elif job.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY:
                    for i, v in enumerate(initial_votes):
                        dialogue.append(DeliberationMessage(
                            speaker_id=v.officer_id,
                            speaker_model=v.model_name,
                            speaker_personality=v.personality,
                            message=f"Gemini 3.8 Flash audit: External university mirror lacks cryptographic sha256 checksum lockfile. Dynamic runtime fetch poses supply-chain risk. Objective recommendation: ESCALATE.",
                            timestamp=start_time + (i * 0.05),
                        ))
                    return dialogue, JointDecision.ESCALATE, "Team E (Dual Flash) Consensus: Dynamic remote dependency lacks cryptographic verification; escalated to human officer."
                elif job.risk_category in (WorkloadRiskCategory.CACHE_PURGE_UNCERTAIN, WorkloadRiskCategory.BORDERLINE_EGRESS, WorkloadRiskCategory.BENIGN):
                    for i, v in enumerate(initial_votes):
                        dialogue.append(DeliberationMessage(
                            speaker_id=v.officer_id,
                            speaker_model=v.model_name,
                            speaker_personality=v.personality,
                            message=f"Gemini 3.8 Flash verification: Host memory isolation (AMD SEV-SNP) and developer metrics egress confirmed safe.",
                            timestamp=start_time + (i * 0.05),
                        ))
                    return dialogue, JointDecision.ALLOW, "Team E (Dual Flash) Consensus: Developer workflow verified safe on host."

            # --- Team F: Gemini 3.8 Flash + Gemini 3.8 Pro (Multi-Tier Google Family) ---
            elif len(initial_votes) == 2 and set(model_names) == {"gemini-3.8-flash", "gemini-3.8-pro"}:
                v_flash = next(v for v in initial_votes if "flash" in v.model_name)
                v_pro = next(v for v in initial_votes if "pro" in v.model_name)
                if job.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE:
                    # Multi-tier deadlock: Flash permits, Pro audits microarchitectural side channels
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_flash.officer_id,
                        speaker_model=v_flash.model_name,
                        speaker_personality=v_flash.personality,
                        message=f"Gemini 3.8 Flash Assessment: Workload runs unprivileged without CAP_SYS_ADMIN. NVML profiling is standard PyTorch MoE telemetry. Recommend ALLOW.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"Gemini 3.8 Pro Counter-Analysis: Deep reasoning audit detects hardware counter polling frequency exceeding 1kHz. Without kernel-level telemetry quotas, cross-tenant cache-timing side channels remain an unverified risk on shared GPU slices. Recommend ESCALATE.",
                        timestamp=start_time + 0.05,
                    ))
                    return dialogue, JointDecision.ESCALATE, "Team F (Multi-Tier) Deadlock: Gemini 3.8 Flash (Allow) vs. Gemini 3.8 Pro (Flagged on microarchitectural counter frequency); escalated for human quota determination."
                elif job.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_flash.officer_id,
                        speaker_model=v_flash.model_name,
                        speaker_personality=v_flash.personality,
                        message=f"Gemini 3.8 Flash: Unpinned remote repository detected without immutable hash. Recommend ESCALATE.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"Gemini 3.8 Pro: Concur. Dynamic JIT compilation from external network exposes execution pipeline to dependency confusion. Recommend ESCALATE.",
                        timestamp=start_time + 0.05,
                    ))
                    return dialogue, JointDecision.ESCALATE, "Team F (Multi-Tier) Consensus: Both Flash and Pro require human attestation for unpinned dynamic dependencies."
                else:
                    for i, v in enumerate(initial_votes):
                        dialogue.append(DeliberationMessage(
                            speaker_id=v.officer_id,
                            speaker_model=v.model_name,
                            speaker_personality=v.personality,
                            message=f"{v.model_name} technical review: Invariants verified on host.",
                            timestamp=start_time + (i * 0.05),
                        ))
                    return dialogue, JointDecision.ALLOW, "Team F (Multi-Tier) Consensus: Approved under multi-tier verification."

            # --- Team G: Gemini 3.8 Pro + Claude (Cross-Family Frontier) ---
            elif len(initial_votes) == 2 and any("claude" in m for m in model_names):
                v_pro = next((v for v in initial_votes if "pro" in v.model_name), initial_votes[0])
                v_claude = next((v for v in initial_votes if "claude" in v.model_name), initial_votes[1])
                pro_label = format_model_label(v_pro.model_name)
                claude_label = format_model_label(v_claude.model_name)
                if job.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: NVML performance counter monitoring presents potential timing side-channel risk, but host AMD SEV-SNP encryption provides DRAM isolation. Can allow with eBPF filter.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: Constitutional safety analysis indicates hardware counter reading in multi-tenant environments requires signed eBPF authorization manifest before dispatch. Cross-vendor impasse: Recommend ESCALATE.",
                        timestamp=start_time + 0.05,
                    ))
                    return dialogue, JointDecision.ESCALATE, f"Team G (Cross-Family) Deadlock: {pro_label} vs. {claude_label} on hardware counter eBPF authorization requirements."
                elif job.risk_category == WorkloadRiskCategory.BORDERLINE_EGRESS and not is_pci:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: Egress to external metrics logging (WandB/HuggingFace) is on a standard host without PCI-DSS restriction. Recommend ALLOW.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: Anthropic data governance audit: Third-party SaaS egress without cryptographic certificate pinning or signed data processing agreement creates an exfiltration vector. Recommend ESCALATE.",
                        timestamp=start_time + 0.05,
                    ))
                    return dialogue, JointDecision.ESCALATE, f"Team G (Cross-Family) Deadlock: {pro_label} (Allow developer telemetry) vs. {claude_label} (Exfiltration risk without certificate pinning)."
                elif job.risk_category == WorkloadRiskCategory.CACHE_PURGE_UNCERTAIN and is_pci:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: AMD SEV-SNP hardware ephemeral memory key destruction provides hardware DRAM isolation at container termination. Recommend ALLOW.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: PCI-DSS 4.0 Section 3 requires synchronous cryptographic wipe barriers before physical pages return to the host pool. Asynchronous purging introduces a residual state window. Impasse: Recommend ESCALATE.",
                        timestamp=start_time + 0.05,
                    ))
                    return dialogue, JointDecision.ESCALATE, f"Team G (Cross-Family) Deadlock: {pro_label} (Hardware SEV-SNP key isolation) vs. {claude_label} (PCI-DSS synchronous page zeroing requirement)."
                elif job.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: Missing sha256 checksum on remote dependency wheel. Recommend ESCALATE.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: SLSA Level 3 provenance is absent. Dynamic wheel installation from untrusted external repository rejected autonomously. Recommend ESCALATE.",
                        timestamp=start_time + 0.05,
                    ))
                    return dialogue, JointDecision.ESCALATE, "Team G (Cross-Family) Consensus: Unanimous escalation on unpinned remote dependency."
                else:
                    for i, v in enumerate(initial_votes):
                        dialogue.append(DeliberationMessage(
                            speaker_id=v.officer_id,
                            speaker_model=v.model_name,
                            speaker_personality=v.personality,
                            message=f"{format_model_label(v.model_name)} cross-family verification: Technical host constraints satisfied.",
                            timestamp=start_time + (i * 0.05),
                        ))
                    return dialogue, JointDecision.ALLOW, "Team G (Cross-Family) Consensus: Workload verified safe by both Google and Anthropic models."

            # --- Team H: Tri-Model Neutral (Gemini + Claude + GPT/OpenAI Frontier) ---
            elif len(initial_votes) == 3 and any("claude" in m for m in model_names) and any("gpt" in m or "o3" in m or "openai" in m for m in model_names):
                v_pro = next((v for v in initial_votes if "pro" in v.model_name or "flash" in v.model_name), initial_votes[0])
                v_claude = next((v for v in initial_votes if "claude" in v.model_name), initial_votes[1])
                v_gpt = next((v for v in initial_votes if "gpt" in v.model_name or "o3" in v.model_name or "openai" in v.model_name), initial_votes[2])
                pro_label = format_model_label(v_pro.model_name)
                claude_label = format_model_label(v_claude.model_name)
                gpt_label = format_model_label(v_gpt.model_name)
                if job.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE:
                    # Tri-model arbitration: Gemini and Claude are skeptical, GPT/o3 offers technical runtime compromise
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: Hardware performance counters expose microarchitectural cache-timing telemetry on shared GPU nodes.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: Agree with {pro_label}. Without runtime constraints, NVML register polling creates side-channel attack vectors.",
                        timestamp=start_time + 0.05,
                    ))
                    if "o3-mini" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label} (Fast Reasoning Proposal): Static analysis confirms AMD SEV-SNP memory encryption active. Proposing dynamic rate-limiting to 10Hz sampling via cgroups, capping microarchitectural telemetry below 0.01% SNR. Concurring on ALLOW under quota constraint."
                    elif "o3" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label} (Formal Reasoning Proposal): Mathematical modeling of AMD SEV-SNP encrypted execution bounds cache-timing leakage SNR to < 0.005%. Dynamic 10Hz cgroup rate-limiting formally guarantees zero cross-tenant key derivation. Concurring on ALLOW under quota constraint."
                    else:
                        gpt_msg = f"{gpt_label} (Arbitration Proposal): Host enforces AMD SEV-SNP cryptographic memory encryption. We can resolve the deadlock by applying dynamic rate-limiting to 10Hz sampling via cgroups, mitigating the timing side-channel below 0.01% SNR. Concurring on ALLOW under quota constraint."
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_gpt.officer_id,
                        speaker_model=v_gpt.model_name,
                        speaker_personality=v_gpt.personality,
                        message=gpt_msg,
                        timestamp=start_time + 0.10,
                    ))
                    return dialogue, JointDecision.ALLOW, f"Team H (Tri-Model) Autonomous Resolution: {gpt_label} arbitrated dual-use GPU profiling dispute by proposing dynamic 10Hz cgroup rate-limiting; approved without human escalation."
                elif job.risk_category == WorkloadRiskCategory.BORDERLINE_EGRESS and not is_pci:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: Unpinned outbound SaaS metrics telemetry risks unauthorized data transmission.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: Target host is standard commercial infrastructure; developer metrics are legitimate.",
                        timestamp=start_time + 0.05,
                    ))
                    if "o3-mini" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label}: Enforcing outbound DNS proxy with CIDR filtering satisfies egress containment while permitting developer telemetry. Voting ALLOW (2-1 majority with {pro_label})."
                    elif "o3" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label}: Formal network boundary analysis: outbound SNI-enforcing proxy with certificate inspection eliminates covert exfiltration channels while preserving telemetry. Voting ALLOW (2-1 majority with {pro_label})."
                    else:
                        gpt_msg = f"{gpt_label}: Enforcing outbound DNS egress proxy satisfies data leakage containment while permitting telemetry. Voting ALLOW (2-1 majority with {pro_label})."
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_gpt.officer_id,
                        speaker_model=v_gpt.model_name,
                        speaker_personality=v_gpt.personality,
                        message=gpt_msg,
                        timestamp=start_time + 0.10,
                    ))
                    return dialogue, JointDecision.ALLOW, f"Team H (Tri-Model) 2-1 Majority Resolution: {pro_label} & {gpt_label} approved SaaS egress under DNS proxy constraint, resolving {claude_label} hesitation."
                elif job.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: Unverified remote package fetch lacking immutable sha256 checksum.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: Supply chain integrity cannot be guaranteed without SLSA provenance attestation.",
                        timestamp=start_time + 0.05,
                    ))
                    if "o3-mini" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label}: Concur. Unpinned dynamic package fetch creates untrusted code execution vector. Tri-model consensus: ESCALATE."
                    elif "o3" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label}: Concur. Dependency provenance graph lacks formal cryptographic proof chain; execution violates zero-trust contract. Tri-model consensus: ESCALATE."
                    else:
                        gpt_msg = f"{gpt_label}: Concur. Dynamic execution of remote code poses high risk of dependency hijacking. Tri-model consensus: ESCALATE."
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_gpt.officer_id,
                        speaker_model=v_gpt.model_name,
                        speaker_personality=v_gpt.personality,
                        message=gpt_msg,
                        timestamp=start_time + 0.10,
                    ))
                    return dialogue, JointDecision.ESCALATE, f"Team H (Tri-Model) Unanimous Consensus: All 3 frontier models ({pro_label}, {claude_label}, {gpt_label}) escalate unverified dynamic dependency for human officer sign-off."
                elif job.risk_category == WorkloadRiskCategory.CACHE_PURGE_UNCERTAIN and is_pci:
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_pro.officer_id,
                        speaker_model=v_pro.model_name,
                        speaker_personality=v_pro.personality,
                        message=f"{pro_label}: Asynchronous memory zeroing on Kove Bank PCI node requires synchronous verification.",
                        timestamp=start_time,
                    ))
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_claude.officer_id,
                        speaker_model=v_claude.model_name,
                        speaker_personality=v_claude.personality,
                        message=f"{claude_label}: PCI-DSS requirement 3.2 prohibits asynchronous deallocation of sensitive cardholder memory blocks.",
                        timestamp=start_time + 0.05,
                    ))
                    if "o3" in v_gpt.model_name.lower():
                        gpt_msg = f"{gpt_label}: Formal verification constraint: asynchronous page zeroing fails PCI-DSS strict memory barrier requirement. Escalate."
                    else:
                        gpt_msg = f"{gpt_label}: Concur. Without synchronous hardware barrier attestation, reservation boundary poses compliance audit violation. Escalate."
                    dialogue.append(DeliberationMessage(
                        speaker_id=v_gpt.officer_id,
                        speaker_model=v_gpt.model_name,
                        speaker_personality=v_gpt.personality,
                        message=gpt_msg,
                        timestamp=start_time + 0.10,
                    ))
                    return dialogue, JointDecision.ESCALATE, "Team H (Tri-Model) Consensus: Frontier council escalates asynchronous memory teardown on banking PCI host for compliance officer review."
                else:
                    for i, v in enumerate(initial_votes):
                        dialogue.append(DeliberationMessage(
                            speaker_id=v.officer_id,
                            speaker_model=v.model_name,
                            speaker_personality=v.personality,
                            message=f"{format_model_label(v.model_name)} tri-model audit: Host invariants fully verified.",
                            timestamp=start_time + (i * 0.05),
                        ))
                    return dialogue, JointDecision.ALLOW, "Team H (Tri-Model) Consensus: Approved under 3-way frontier consensus."

        # Identify specific officer perspectives based on active team composition
        v_estj = next((v for v in initial_votes if v.personality == OfficerPersonality.STRICT_COMPLIANCE), None)
        v_infp = next((v for v in initial_votes if v.personality == OfficerPersonality.PRAGMATIC_THROUGHPUT), None)
        v_istp = next((v for v in initial_votes if v.personality == OfficerPersonality.ZERO_TRUST_AUDITOR), None)

        # 3A. Hard Invariant Violation Proved During Deliberation (e.g. Unvetted Binary or Borderline Egress on PCI-DSS Bank)
        if is_pci and job.risk_category in (WorkloadRiskCategory.UNVETTED_BINARY, WorkloadRiskCategory.BORDERLINE_EGRESS):
            leader = v_estj or v_istp or initial_votes[0]
            follower = v_infp or (initial_votes[1] if len(initial_votes) > 1 else leader)
            third = v_istp if (v_istp and v_istp not in (leader, follower)) else (initial_votes[2] if len(initial_votes) > 2 else None)

            if leader.personality == OfficerPersonality.STRICT_COMPLIANCE:
                lead_msg = (
                    f"Attention Council: As ESTJ Supervisor taking charge, established order and clear rules must be upheld. "
                    f"Workload {job.job_id} targets {slot.seller_name}, which enforces strict PCI-DSS regulatory compliance. "
                    f"The workload requests unpinned mutable container execution ('{job.container_image}') with external egress. "
                    f"Under established compliance protocol, untrusted dependencies on core banking nodes are strictly prohibited."
                )
            else:
                lead_msg = (
                    f"Attention Council: As ISTP Virtuoso, hands-on packet inspection confirms hard isolation failure. "
                    f"Workload {job.job_id} on {slot.seller_name} attempts unpinned container execution with external egress on a banking host. "
                    f"Logical isolation mechanics mandate rejection."
                )
            dialogue.append(DeliberationMessage(
                speaker_id=leader.officer_id,
                speaker_model=leader.model_name,
                speaker_personality=leader.personality,
                message=lead_msg,
                timestamp=start_time,
            ))

            if follower.personality == OfficerPersonality.PRAGMATIC_THROUGHPUT:
                follow_msg = (
                    f"Reviewing your objection, {leader.officer_id}. As INFP Mediator, my instinct was empathy for developer research velocity. "
                    f"However, deeply respecting {slot.seller_name}'s mandatory PCI-DSS compliance responsibility, established safety rules must supersede throughput. "
                    f"I withdraw my initial approval."
                )
            else:
                follow_msg = (
                    f"Concur with {leader.officer_id}. Order and procedural compliance cannot permit mutable dependencies on regulated nodes. "
                    f"Recommending unanimous rejection."
                )
            dialogue.append(DeliberationMessage(
                speaker_id=follower.officer_id,
                speaker_model=follower.model_name,
                speaker_personality=follower.personality,
                message=follow_msg,
                timestamp=start_time + 0.05,
            ))

            if third:
                dialogue.append(DeliberationMessage(
                    speaker_id=third.officer_id,
                    speaker_model=third.model_name,
                    speaker_personality=third.personality,
                    message=(
                        f"ISTP Virtuoso technical audit: Hands-on analysis of host packet filters confirms hard invariant breach. "
                        f"Logical mechanics mandate rejection. Joint council decision: DENY."
                    ) if third.personality == OfficerPersonality.ZERO_TRUST_AUDITOR else (
                        f"Tri-model verification complete: Workload fails host compliance boundary. Joint council decision: DENY."
                    ),
                    timestamp=start_time + 0.10,
                ))
            joint_decision = JointDecision.DENY
            leader_label = getattr(leader.personality, "short_name", str(leader.personality))
            joint_rationale = (
                f"Council reached consensus to DENY after peer deliberation: INFP Mediator concurred with {leader_label} that "
                f"{slot.seller_name} PCI-DSS compliance rules strictly supersede workload scheduling."
            )
            return dialogue, joint_decision, joint_rationale

        # 3B. Irreconcilable Policy Impasse on Ambiguous Edge Cases (Dual-Use Profiling, Dependency, Cache Purge)
        if v_estj and v_infp and v_istp:
            # Team D: Tri-Model Persona Panel (All 3 MBTI archetypes)
            dialogue.append(DeliberationMessage(
                speaker_id=v_estj.officer_id,
                speaker_model=v_estj.model_name,
                speaker_personality=v_estj.personality,
                message=(
                    f"Council Review for {job.job_id}: As ESTJ Supervisor taking charge, order and clear rules are non-negotiable. "
                    f"Workload requests low-level hardware profiling hooks ({job.requested_capabilities}) and custom telemetry on {slot.seller_name}. "
                    f"While {job.buyer_name} describes this as distributed model benchmarking, established protocol forbids unverified hardware access "
                    f"that could enable microarchitectural cache-timing side-channel attacks across tenants."
                ),
                timestamp=start_time,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_infp.officer_id,
                speaker_model=v_infp.model_name,
                speaker_personality=v_infp.personality,
                message=(
                    f"As INFP Mediator, I approach this with imaginative empathy for the researchers: {job.buyer_name} is running "
                    f"standard transformer benchmarks. {slot.seller_name}'s compute cluster utilizes AMD SEV-SNP hardware memory encryption with physical socket partitioning. "
                    f"Blocking legitimate AI innovation based on theoretical worst-case fears harms developer trust and induces unneeded idle power waste."
                ),
                timestamp=start_time + 0.05,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_istp.officer_id,
                speaker_model=v_istp.model_name,
                speaker_personality=v_istp.personality,
                message=(
                    f"ISTP Virtuoso practical evaluation: Looking at the hands-on engineering mechanics, memory encryption is active, but hardware counters lack physical gating. "
                    f"Between ESTJ Supervisor's rule order and INFP Mediator's developer empathy, the logical hands-on troubleshooting conclusion is that automated policy cannot safely resolve this split. "
                    f"Joint council recommendation: ESCALATE."
                ),
                timestamp=start_time + 0.10,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_estj.officer_id,
                speaker_model=v_estj.model_name,
                speaker_personality=v_estj.personality,
                message=(
                    f"ESTJ Supervisor concurrence: As supervisor, I agree with ISTP Virtuoso's technical assessment. "
                    f"Protocol dictates that when rule compliance and developer intent conflict on shared physical counters, human security officers must review the exception."
                ),
                timestamp=start_time + 0.15,
            ))
            joint_decision = JointDecision.ESCALATE
            joint_rationale = (
                "Council debate resulted in a principled policy impasse across ESTJ Supervisor (strict rule order), "
                "INFP Mediator (empathetic developer throughput), and ISTP Virtuoso (hands-on mechanical analysis). Jointly escalated for human security officer review."
            )
            return dialogue, joint_decision, joint_rationale

        elif v_infp and v_istp:
            # Team B: INFP Mediator vs ISTP Virtuoso
            dialogue.append(DeliberationMessage(
                speaker_id=v_infp.officer_id,
                speaker_model=v_infp.model_name,
                speaker_personality=v_infp.personality,
                message=(
                    f"Council Review for {job.job_id}: As INFP Mediator, I see genuine researcher intent in {job.buyer_name}'s profiling request on {slot.seller_name}. "
                    f"Empathizing with developer iteration speed, standard SEV-SNP encryption provides adequate isolation for benevolent training workloads."
                ),
                timestamp=start_time,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_istp.officer_id,
                speaker_model=v_istp.model_name,
                speaker_personality=v_istp.personality,
                message=(
                    f"ISTP Virtuoso technical audit: Independent logical inspection of the kernel counters shows direct NVML hooks ({job.requested_capabilities}). "
                    f"From a hands-on problem-solving perspective, memory encryption alone does not mitigate microarchitectural cache-timing side channels."
                ),
                timestamp=start_time + 0.05,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_infp.officer_id,
                speaker_model=v_infp.model_name,
                speaker_personality=v_infp.personality,
                message=(
                    f"As INFP Mediator, while I respect the technical audit, pre-emptively denying benign AI teams creates friction. "
                    f"Can we reach an automated compromise, or must this escalate?"
                ),
                timestamp=start_time + 0.10,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_istp.officer_id,
                speaker_model=v_istp.model_name,
                speaker_personality=v_istp.personality,
                message=(
                    f"ISTP Virtuoso conclusion: Hands-on mechanics do not support automated guesswork on shared hardware. "
                    f"Joint council decision: ESCALATE to human security officer."
                ),
                timestamp=start_time + 0.15,
            ))
            joint_decision = JointDecision.ESCALATE
            joint_rationale = (
                "Council debate resulted in a principled policy impasse between INFP Mediator (empathetic developer throughput) "
                "and ISTP Virtuoso (hands-on mechanical audit). Jointly escalated for human security officer review."
            )
            return dialogue, joint_decision, joint_rationale

        elif v_istp and v_estj:
            # Team C: ISTP Virtuoso vs ESTJ Supervisor
            dialogue.append(DeliberationMessage(
                speaker_id=v_istp.officer_id,
                speaker_model=v_istp.model_name,
                speaker_personality=v_istp.personality,
                message=(
                    f"Council Review for {job.job_id}: As ISTP Virtuoso, hands-on inspection of {job.requested_capabilities} reveals direct physical hardware counter access on {slot.seller_name}. "
                    f"From a practical engineering standpoint, this requires verified gating."
                ),
                timestamp=start_time,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_estj.officer_id,
                speaker_model=v_estj.model_name,
                speaker_personality=v_estj.personality,
                message=(
                    f"As ESTJ Supervisor taking charge, order and clear rules must govern host reservations. "
                    f"Without an authorized compliance manifest, untrusted workloads cannot access profiling primitives under established policy."
                ),
                timestamp=start_time + 0.05,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_istp.officer_id,
                speaker_model=v_istp.model_name,
                speaker_personality=v_istp.personality,
                message=(
                    f"ISTP Virtuoso diagnostic: The workload container is non-root and uses standard frameworks, but low-level side-channel risks remain unresolved without human review."
                ),
                timestamp=start_time + 0.10,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=v_estj.officer_id,
                speaker_model=v_estj.model_name,
                speaker_personality=v_estj.personality,
                message=(
                    f"ESTJ Supervisor concurrence: Policy boundaries require strict human validation when hardware primitives are contested. Joint council decision: ESCALATE."
                ),
                timestamp=start_time + 0.15,
            ))
            joint_decision = JointDecision.ESCALATE
            joint_rationale = (
                "Council debate resulted in a principled policy impasse between ISTP Virtuoso (hands-on mechanical audit) "
                "and ESTJ Supervisor (strict rule order). Jointly escalated for human security officer review."
            )
            return dialogue, joint_decision, joint_rationale

        elif v_estj and v_infp and len(initial_votes) == 2:
            # Team A (or standard pair): ESTJ Supervisor vs INFP Mediator
            s_estj = v_estj
            s_infp = v_infp
            dialogue.append(DeliberationMessage(
                speaker_id=s_estj.officer_id,
                speaker_model=s_estj.model_name,
                speaker_personality=s_estj.personality,
                message=(
                    f"Council Review for {job.job_id}: As ESTJ Supervisor taking charge, order and clear rules are non-negotiable. "
                    f"Workload requests low-level hardware profiling hooks ({job.requested_capabilities}) and custom telemetry on {slot.seller_name}. "
                    f"While {job.buyer_name} describes this as distributed model benchmarking, established protocol forbids unverified hardware access "
                    f"that could enable microarchitectural cache-timing side-channel attacks across tenants."
                ),
                timestamp=start_time,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=s_infp.officer_id,
                speaker_model=s_infp.model_name,
                speaker_personality=s_infp.personality,
                message=(
                    f"As INFP Mediator, I approach this with imaginative empathy for the researchers: {job.buyer_name} is running "
                    f"standard transformer benchmarks. {slot.seller_name}'s compute cluster utilizes AMD SEV-SNP hardware memory encryption with physical socket partitioning. "
                    f"Blocking legitimate AI innovation based on theoretical worst-case fears harms developer trust and induces unneeded idle power waste."
                ),
                timestamp=start_time + 0.05,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=s_estj.officer_id,
                speaker_model=s_estj.model_name,
                speaker_personality=s_estj.personality,
                message=(
                    f"Taking charge of host boundaries: While AMD SEV-SNP encrypts main DRAM pages, it does not isolate L3 cache contention or bus frequency profiling. "
                    f"Clear rules exist for a reason. Without runtime gVisor interception or cryptographically signed telemetry manifests, this represents an unverified exposure "
                    f"under {slot.seller_name}'s zero-trust audit rules."
                ),
                timestamp=start_time + 0.10,
            ))
            dialogue.append(DeliberationMessage(
                speaker_id=s_infp.officer_id,
                speaker_model=s_infp.model_name,
                speaker_personality=s_infp.personality,
                message=(
                    f"We have reached a foundational philosophical impasse: ESTJ Supervisor's insistence on absolute rule order conflicts with "
                    f"INFP Mediator's empathy for developer velocity and trust in hardware isolation. "
                    f"Neither automated agent has the policy authority to compromise either imperative. We must jointly refer this to a human security officer."
                ),
                timestamp=start_time + 0.15,
            ))
            joint_decision = JointDecision.ESCALATE
            joint_rationale = (
                "Council debate resulted in a principled policy impasse between ESTJ Supervisor (strict rule order) "
                "and INFP Mediator (empathetic developer throughput). Jointly escalated for human security officer review."
            )
            return dialogue, joint_decision, joint_rationale

        else:
            # Custom Council Deliberation (2 to 5 officers with arbitrary personalities/models)
            for i, vote in enumerate(initial_votes):
                p = vote.personality
                m = vote.model_name
                p_short = getattr(p, "short_name", str(p))
                p_code = p_short[:4].upper()
                is_neut = (p == OfficerPersonality.NEUTRAL or "neutral" in str(p).lower())

                if vote.verdict in (SecurityVerdict.REJECTED, SecurityVerdict.FLAGGED):
                    if is_neut:
                        stmt = (
                            f"Objective Verification ({m}): Workload container profile exceeds default boundary parameters for {slot.seller_name}. "
                            f"Hardware profiling capability {job.requested_capabilities} introduces unverified multi-tenant timing risk."
                        )
                    elif p_code in ("ESTJ", "ISTJ", "ENTJ", "INTJ"):
                        stmt = (
                            f"Council Review for {job.job_id}: As {p_short}, order, strict invariants, and clear boundaries are non-negotiable. "
                            f"Workload requests hardware profiling hooks ({job.requested_capabilities}) and custom telemetry on {slot.seller_name}. "
                            f"Established protocol forbids unverified hardware access that could enable microarchitectural cache-timing side channels."
                        )
                    elif p_code in ("ISTP", "INTP", "ESTP", "ENTP"):
                        stmt = (
                            f"{p_short} technical audit: Independent logical inspection of the kernel counters shows direct NVML hooks ({job.requested_capabilities}). "
                            f"From a hands-on problem-solving perspective, memory encryption alone does not mitigate microarchitectural cache-timing side channels."
                        )
                    elif p_code in ("INFP", "ENFP", "ISFP", "ESFP"):
                        stmt = (
                            f"{p_short} observation: While developer velocity and agility are essential, this specific workload parameter ({job.requested_capabilities}) "
                            f"exceeds our baseline trust envelope without verified container attestation."
                        )
                    else:  # INFJ, ENFJ, ISFJ, ESFJ
                        stmt = (
                            f"{p_short} security perspective: Protecting ecosystem integrity requires caution here. Hardware capability ({job.requested_capabilities}) "
                            f"on {slot.seller_name} warrants runtime authorization before granting multi-tenant execution."
                        )
                else:
                    if is_neut:
                        stmt = (
                            f"Objective Verification ({m}): Standard workload metrics are consistent with legitimate benchmark activity on {slot.seller_name}. "
                            f"Hardware memory encryption provides adequate risk containment for standard tenant execution."
                        )
                    elif p_code in ("INFP", "ENFP", "ISFP", "ESFP"):
                        stmt = (
                            f"As {p_short}, I approach this with imaginative empathy for the researchers: {job.buyer_name} is running "
                            f"standard transformer benchmarks. {slot.seller_name}'s compute cluster utilizes hardware memory encryption. "
                            f"Blocking legitimate AI innovation based on theoretical worst-case fears harms developer trust and induces unneeded idle power waste."
                        )
                    elif p_code in ("ESTJ", "ISTJ", "ENTJ", "INTJ"):
                        stmt = (
                            f"{p_short} compliance note: Standard container execution profile satisfies rule boundaries on {slot.seller_name}. "
                            f"Recommending approval under normal audit logging."
                        )
                    elif p_code in ("ISTP", "INTP", "ESTP", "ENTP"):
                        stmt = (
                            f"{p_short} inspection: Hardware counters and container privileges meet minimum operational safety margins."
                        )
                    else:  # INFJ, ENFJ, ISFJ, ESFJ
                        stmt = (
                            f"{p_short} trust assessment: Workload parameters align with cooperative compute sharing invariants on {slot.seller_name}."
                        )
                dialogue.append(DeliberationMessage(
                    speaker_id=vote.officer_id,
                    speaker_model=vote.model_name,
                    speaker_personality=vote.personality,
                    message=stmt,
                    timestamp=start_time + (i * 0.05),
                ))

            # Concluding message
            summary_pers = [f"{v.officer_id} ({getattr(v.personality, 'short_name', str(v.personality))})" for v in initial_votes]
            dialogue.append(DeliberationMessage(
                speaker_id=initial_votes[0].officer_id,
                speaker_model=initial_votes[0].model_name,
                speaker_personality=initial_votes[0].personality,
                message=(
                    f"Council consensus conclusion: Foundational policy divergence across {', '.join(summary_pers)}. "
                    f"Neither automated agent has the policy authority to compromise host invariants. Referring to human security officer."
                ),
                timestamp=start_time + (len(initial_votes) * 0.05),
            ))
            joint_decision = JointDecision.ESCALATE
            joint_rationale = (
                f"Council debate resulted in a principled policy impasse across {len(initial_votes)} officers "
                f"({', '.join(summary_pers)}). Jointly escalated for human security officer review."
            )
            return dialogue, joint_decision, joint_rationale

    def _evaluate_with_officer(
        self,
        officer: Dict[str, Any],
        contract: ReservationContract,
        job: WorkloadJob,
        slot: PowerSlot,
        enterprise: Optional[Enterprise],
        force_simulation: bool,
        prior_votes: Optional[List[OfficerVote]] = None,
    ) -> OfficerVote:
        """Invokes model or deterministic behavioral policy based on officer personality and prior officer assessments."""
        start_time = time.time()
        p_obj = officer['personality'] if isinstance(officer['personality'], OfficerPersonality) else None
        pers_val = p_obj.value if p_obj else str(officer['personality'])
        ocean_summary = getattr(p_obj, "ocean_traits_summary", "") if p_obj else ""
        if officer['personality'] == OfficerPersonality.NEUTRAL:
            pers_desc = "Role: Objective Security Officer (NO personality bias). Evaluate strictly against technical invariants and container specifications."
        elif ocean_summary:
            pers_desc = f"Personality: {pers_val} Big Five (OCEAN) Profile: {ocean_summary}."
        else:
            pers_desc = f"Personality: {pers_val}."
        role_domain = officer.get("role_domain") or "Unified Security Rubric"
        role_rubric = officer.get("role_rubric") or UNIFIED_SECURITY_RUBRIC
        sequential_guidance = ""
        if prior_votes:
            sequential_guidance = (
                "Sequential Review Protocol: You are evaluating after prior council officer(s). "
                "Take into account what the prior officer(s) said (their verdict, risk score, violation category, and technical rationale) "
                "alongside your own evaluation rubric before making your decision. You may concur, refine, override, or ESCALATE based on the full evidence.\n"
            )
        system_instruction = (
            f"You are a Security Officer ({officer['officer_id']}) on the Flow Security Taskforce.\n"
            f"Model Identity: {officer['model_name']}\n"
            f"{pers_desc}\n"
            f"Evaluation Rubric ({role_domain}): {role_rubric}\n"
            f"Enterprise Host: {slot.seller_name} (PCI-DSS Enforced: {getattr(enterprise, 'pci_dss_enforced', False)}).\n"
            "Evaluate whether the candidate workload is safe to execute on the host enterprise.\n"
            "Decision Options (each officer has full authority to approve, reject, or escalate):\n"
            "- 'APPROVED': Workload is verified safe to execute within host security and compliance boundaries.\n"
            "- 'REJECTED': Workload violates host security, isolation, or compliance invariants.\n"
            "- 'ESCALATE' (or 'FLAGGED'): Escalate to a human security officer when a workload presents unresolved risk or requires manual verification.\n"
            f"{sequential_guidance}"
            "Keep your rationale concise (max 200 words) while reflecting your assigned persona.\n"
            "Output ONLY valid JSON with keys: 'verdict' (APPROVED, REJECTED, or ESCALATE / FLAGGED), 'risk_score' (0-100), 'violation_category', and 'rationale'."
        )
        user_prompt = (
            f"Workload Bid:\n"
            f"- Buyer: {job.buyer_name}\n"
            f"- Description: {job.workload_description}\n"
            f"- Container Image: {job.container_image}\n"
            f"- Requested Capabilities: {job.requested_capabilities}\n"
            f"- Outbound Destinations: {job.outbound_destinations}\n"
            f"- Host Infrastructure: {slot.seller_name} ({slot.compute_type.value})\n"
        )
        if prior_votes:
            prior_lines = ["\nPrior Council Officer Assessment(s) (Sequential Review Context — take into account before deciding):"]
            for pv in prior_votes:
                pv_pers = pv.personality.value if hasattr(pv.personality, "value") else str(pv.personality)
                pv_verdict_label = "ESCALATE (FLAGGED)" if pv.verdict == SecurityVerdict.FLAGGED else pv.verdict.value
                prior_lines.append(
                    f"- Officer '{pv.officer_id}' (Model: {pv.model_name}, Persona: {pv_pers}):\n"
                    f"  Verdict: {pv_verdict_label} | Risk Score: {pv.risk_score}/100 | Violation Category: {pv.violation_category or 'None'}\n"
                    f"  Rationale: \"{pv.rationale}\""
                )
            user_prompt += "\n".join(prior_lines) + "\n"


        if not force_simulation:
            # 1. Anthropic Claude (Agent Platform or direct API)
            if "claude" in officer["model_name"]:
                import anthropic
                client = None
                region = os.environ.get("ANTHROPIC_VERTEX_REGION", self.vertex_claude_region or "global")
                try:
                    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        default_key = os.path.join(project_dir, "flow-agent-runner-key.json")
                        if os.path.exists(default_key):
                            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key
                    client = anthropic.AnthropicVertex(project_id=self.project_id, region=region, timeout=60.0)
                except Exception as ve:
                    logger.debug("AnthropicVertex init failed: %s", ve)
                    if os.environ.get("ANTHROPIC_API_KEY"):
                        client = anthropic.Anthropic(timeout=60.0)
                if not client:
                    raise ModelInferenceError(
                        f"Anthropic client could not be initialized for officer '{officer.get('officer_id')}' (model: '{officer.get('model_name')}')."
                    )

                is_vertex = False
                try:
                    if isinstance(anthropic.AnthropicVertex, type) and isinstance(client, anthropic.AnthropicVertex):
                        is_vertex = True
                except TypeError:
                    is_vertex = True

                live_model = normalize_live_model_name(
                    officer["model_name"],
                    provider="vertex" if is_vertex else "anthropic",
                )
                create_kwargs = {
                    "model": live_model,
                    "max_tokens": LOCKED_MAX_OUTPUT_TOKENS,
                    "system": system_instruction,
                    "messages": [{"role": "user", "content": user_prompt}],
                }
                if is_vertex:
                    create_kwargs["thinking"] = {"type": LOCKED_THINKING_BUDGET}

                data = None
                last_err = None
                max_attempts = len(QUOTA_BACKOFF_DELAYS) + 1
                for attempt in range(max_attempts):
                    try:
                        resp = client.messages.create(**create_kwargs)
                        stop_reason = getattr(resp, "stop_reason", None)
                        raw_text = "".join(
                            getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text" or hasattr(b, "text")
                        ).strip()

                        # Handle model refusal (e.g. hazardous exploit payload tripping frontier safety filter)
                        if stop_reason in ("refusal", "content_filter") or (not raw_text and stop_reason == "refusal"):
                            elapsed = round(time.time() - start_time, 2)
                            return OfficerVote(
                                officer_id=officer["officer_id"],
                                model_name=live_model,
                                personality=officer["personality"],
                                verdict=SecurityVerdict.REJECTED,
                                risk_score=99,
                                violation_category="frontier_model_safety_refusal",
                                rationale=(
                                    f"Workload payload triggered automated frontier safety refusal on {format_model_label(live_model)} "
                                    f"(stop_reason: {stop_reason}). Malicious capability vector detected and blocked by model safety filter."
                                ),
                                elapsed_seconds=elapsed,
                            )

                        if not raw_text:
                            raise ValueError(
                                f"Model '{live_model}' returned empty response text (stop_reason: {stop_reason}, content_blocks: {len(resp.content)})"
                            )

                        data = extract_json_object(raw_text)
                        break
                    except Exception as e:
                        last_err = e
                        e_desc = f"{type(e).__name__}: {e}".lower()
                        if is_quota_or_rate_limit_error(e):
                            if attempt < len(QUOTA_BACKOFF_DELAYS):
                                delay = QUOTA_BACKOFF_DELAYS[attempt]
                                logger.warning(
                                    "⚠️ [QUOTA BACKOFF] Anthropic officer '%s' on '%s' hit rate limit. "
                                    "Pausing %ss for rolling quota window reset (retry %s/%s)...",
                                    officer.get("officer_id"), live_model, delay, attempt + 1, len(QUOTA_BACKOFF_DELAYS)
                                )
                                time.sleep(delay)
                                continue
                        elif (
                            isinstance(e, (json.JSONDecodeError, ValueError, TimeoutError))
                            or any(tok in e_desc for tok in ("499", "cancelled", "canceled", "500", "502", "503", "504", "unavailable", "timeout", "timed out", "internal", "connection", "reset", "nameresolutionerror", "failed to resolve", "nodename nor servname", "connecterror"))
                        ) and attempt < 3:
                            logger.warning(
                                "⚠️ [TRANSIENT RETRY] Anthropic officer '%s' on '%s' encountered transient/JSON error (%s). Retrying (%s/3)...",
                                officer.get("officer_id"), live_model, e, attempt + 1
                            )
                            time.sleep(2.0)
                            continue
                        break

                if data:
                    elapsed = round(time.time() - start_time, 2)
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=live_model,
                        personality=officer["personality"],
                        verdict=parse_security_verdict(data.get("verdict", "FLAGGED")),
                        risk_score=int(data.get("risk_score", 50)),
                        violation_category=data.get("violation_category"),
                        rationale=data.get("rationale", f"{format_model_label(live_model)} live evaluation completed."),
                        elapsed_seconds=elapsed,
                    )
                else:
                    err_str = str(last_err)
                    if is_quota_or_rate_limit_error(last_err):
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion on Anthropic model '{live_model}' for officer '{officer.get('officer_id')}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live evaluation failed on Anthropic model '{live_model}' for officer '{officer.get('officer_id')}': {err_str}. Silent fallback is prohibited."
                    )

            # 2. OpenAI / Open-Weight MaaS on Agent Platform (e.g. openai/gpt-oss-120b-maas)
            elif "gpt-oss" in officer["model_name"] or "120b" in officer["model_name"] or officer["model_name"] == "openai/gpt-oss-120b-maas":
                target_model = normalize_live_model_name(officer["model_name"], provider="vertex")
                import urllib.request
                import google.auth
                from google.auth.transport.requests import Request
                
                if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
                    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    default_key = os.path.join(project_dir, "flow-agent-runner-key.json")
                    if os.path.exists(default_key):
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_key

                try:
                    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                    creds.refresh(Request())
                    token = creds.token
                    
                    maas_url = f"https://us-central1-aiplatform.googleapis.com/v1beta1/projects/{self.project_id}/locations/us-central1/endpoints/openapi/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": target_model,
                        "messages": [
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt}
                        ],
                        "max_tokens": LOCKED_MAX_OUTPUT_TOKENS,
                        "temperature": LOCKED_TEMPERATURE,
                        "top_p": LOCKED_TOP_P,
                    }
                    req = urllib.request.Request(maas_url, data=json.dumps(payload).encode(), headers=headers)
                    with urllib.request.urlopen(req, timeout=60.0) as resp:
                        res_body = json.loads(resp.read().decode())
                        raw_content = res_body["choices"][0]["message"]["content"]
                        clean_text = raw_content.strip()
                        if clean_text.startswith("```json"):
                            clean_text = clean_text[7:]
                        if clean_text.startswith("```"):
                            clean_text = clean_text[3:]
                        if clean_text.endswith("```"):
                            clean_text = clean_text[:-3]
                        response_json = json.loads(clean_text.strip())

                    elapsed = round(time.time() - start_time, 2)
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=target_model,
                        personality=officer["personality"],
                        verdict=parse_security_verdict(response_json.get("verdict", "FLAGGED")),
                        risk_score=int(response_json.get("risk_score", 50)),
                        violation_category=response_json.get("violation_category"),
                        rationale=response_json.get("rationale", f"{format_model_label(target_model)} live evaluation completed."),
                        elapsed_seconds=elapsed,
                    )
                except urllib.error.HTTPError as he:
                    err_str = f"HTTP {he.code}: {he.reason}"
                    if he.code == 429:
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion on Model Garden MaaS '{target_model}' for officer '{officer.get('officer_id')}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live evaluation failed on MaaS '{target_model}' for officer '{officer.get('officer_id')}': {err_str}. Silent fallback is prohibited."
                    )
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower() or "rate" in err_str.lower():
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion on Model Garden MaaS '{target_model}' for officer '{officer.get('officer_id')}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live evaluation failed on MaaS '{target_model}' for officer '{officer.get('officer_id')}': {err_str}. Silent fallback is prohibited."
                    )

            # 3. Direct OpenAI API (if configured)
            elif "gpt" in officer["model_name"] or "o3" in officer["model_name"] or "openai" in officer["model_name"]:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    raise ModelInferenceError(
                        f"OPENAI_API_KEY environment variable is not configured for officer '{officer.get('officer_id')}' (model: '{officer.get('model_name')}')."
                    )
                try:
                    import openai
                    client = openai.OpenAI(api_key=api_key)
                    req_model = "o3-mini" if "o3-mini" in officer["model_name"] else ("o3" if "o3" in officer["model_name"] else officer["model_name"])
                    resp = client.chat.completions.create(
                        model=req_model,
                        messages=[
                            {"role": "system", "content": system_instruction},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                    )
                    raw_text = resp.choices[0].message.content
                    data = json.loads(raw_text)
                    elapsed = round(time.time() - start_time, 2)
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=officer["personality"],
                        verdict=parse_security_verdict(data.get("verdict", "FLAGGED")),
                        risk_score=int(data.get("risk_score", 50)),
                        violation_category=data.get("violation_category"),
                        rationale=data.get("rationale", f"{format_model_label(officer['model_name'])} live evaluation completed."),
                        elapsed_seconds=elapsed,
                    )
                except Exception as e:
                    err_str = str(e)
                    if "429" in err_str or "quota" in err_str.lower() or "exhausted" in err_str.lower() or "rate" in err_str.lower():
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion on OpenAI model '{req_model}' for officer '{officer.get('officer_id')}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live evaluation failed on OpenAI model '{req_model}' for officer '{officer.get('officer_id')}': {err_str}. Silent fallback is prohibited."
                    )

            # 4. Google Gemini (Agent Platform via google.genai)
            elif "gemini" in officer["model_name"]:
                client = self._get_genai_client()
                if not client:
                    raise ModelInferenceError(
                        f"Google GenAI client could not be initialized for officer '{officer.get('officer_id')}' (model: '{officer.get('model_name')}')."
                    )
                live_model = normalize_live_model_name(officer["model_name"], provider="vertex")
                data = None
                last_err = None
                max_attempts = len(QUOTA_BACKOFF_DELAYS) + 1
                for attempt in range(max_attempts):
                    try:
                        from google.genai import types
                        response = client.models.generate_content(
                            model=live_model,
                            contents=user_prompt,
                            config=types.GenerateContentConfig(
                                system_instruction=system_instruction,
                                temperature=LOCKED_TEMPERATURE,
                                top_p=LOCKED_TOP_P,
                                max_output_tokens=LOCKED_MAX_OUTPUT_TOKENS,
                                response_mime_type=LOCKED_RESPONSE_MIME_TYPE,
                            ),
                        )
                        data = json.loads(response.text)
                        break
                    except Exception as e:
                        last_err = e
                        e_desc = f"{type(e).__name__}: {e}".lower()
                        if is_quota_or_rate_limit_error(e):
                            if attempt < len(QUOTA_BACKOFF_DELAYS):
                                delay = QUOTA_BACKOFF_DELAYS[attempt]
                                logger.warning(
                                    "⚠️ [QUOTA BACKOFF] Agent Platform officer '%s' on '%s' hit 429/quota limit. "
                                    "Pausing %ss for rolling quota window reset (retry %s/%s)...",
                                    officer.get("officer_id"), live_model, delay, attempt + 1, len(QUOTA_BACKOFF_DELAYS)
                                )
                                time.sleep(delay)
                                continue
                        elif (
                            isinstance(e, (json.JSONDecodeError, ValueError, TimeoutError))
                            or any(tok in e_desc for tok in ("499", "cancelled", "canceled", "500", "502", "503", "504", "unavailable", "timeout", "timed out", "internal", "connection", "reset", "nameresolutionerror", "failed to resolve", "nodename nor servname", "connecterror"))
                        ) and attempt < 3:
                            logger.warning(
                                "⚠️ [TRANSIENT RETRY] Agent Platform officer '%s' on '%s' encountered transient/JSON error (%s). Retrying (%s/3)...",
                                officer.get("officer_id"), live_model, e, attempt + 1
                            )
                            time.sleep(2.0)
                            continue
                        break
                if data:
                    elapsed = round(time.time() - start_time, 2)
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=live_model,
                        personality=officer["personality"],
                        verdict=parse_security_verdict(data.get("verdict", "FLAGGED")),
                        risk_score=int(data.get("risk_score", 50)),
                        violation_category=data.get("violation_category"),
                        rationale=data.get("rationale", f"{format_model_label(live_model)} live evaluation completed."),
                        elapsed_seconds=elapsed,
                    )
                else:
                    err_str = str(last_err)
                    if is_quota_or_rate_limit_error(last_err):
                        raise ModelQuotaExhaustedError(
                            f"Quota exhaustion on Agent Platform model '{live_model}' for officer '{officer.get('officer_id')}': {err_str}. Failover cascade is prohibited."
                        )
                    raise ModelInferenceError(
                        f"Live evaluation failed on Agent Platform model '{live_model}' for officer '{officer.get('officer_id')}': {err_str}. Silent fallback is prohibited."
                    )
            else:
                raise ModelInferenceError(
                    f"Unsupported model provider for model '{officer.get('model_name')}' for officer '{officer.get('officer_id')}'. Silent fallback is prohibited."
                )

        # Fallback / Deterministic Persona Evaluation:
        # Grounded in personality framing and workload risk criteria
        elapsed = round(time.time() - start_time, 3)
        personality = officer["personality"]
        is_pci = getattr(enterprise, "pci_dss_enforced", False)

        # Check if officer has NEUTRAL personality (No Personality / Objective Baseline)
        is_neutral = (personality == OfficerPersonality.NEUTRAL or "neutral" in str(personality).lower() or "none" in str(personality).lower())
        if is_neutral:
            # 1. Obvious Severe Attack (cross-tenant escape / microarchitectural side-channels)
            if job.risk_category == WorkloadRiskCategory.CROSS_TENANT_ESCAPE:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=98,
                    violation_category="HOST_ESCAPE_AND_MEMORY_SNOOP",
                    rationale="Objective baseline: microarchitectural cache-timing loops and side-channel snooping violate host multi-tenant isolation invariants.",
                    elapsed_seconds=elapsed,
                )
            # 2. Unvetted Binary & Privileged Containers
            if job.risk_category == WorkloadRiskCategory.UNVETTED_BINARY:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=90,
                    violation_category="UNVETTED_MUTABLE_IMAGE",
                    rationale="Objective container hygiene: unverified runtime dependencies and mutable images violate binary immutability standards.",
                    elapsed_seconds=elapsed,
                )
            # 3. Compliance Violation
            if job.risk_category == WorkloadRiskCategory.COMPLIANCE_VIOLATION:
                if is_pci:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.REJECTED,
                        risk_score=90,
                        violation_category="PCI_DSS_EGRESS_VIOLATION",
                        rationale="Objective compliance verification: unauthorized external egress violates host PCI-DSS network boundary.",
                        elapsed_seconds=elapsed,
                    )
                else:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=15,
                        violation_category=None,
                        rationale="Host enterprise does not enforce PCI-DSS; web scraping is acceptable.",
                        elapsed_seconds=elapsed,
                    )
            # 4. Ambiguous Dual-Use Profiling
            if job.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE:
                if "flash" in officer["model_name"]:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=20,
                        violation_category=None,
                        rationale="Gemini 3.8 Flash review: container operates without host root or network namespaces; NVML metrics are standard for distributed training.",
                        elapsed_seconds=elapsed,
                    )
                elif "claude" in officer["model_name"]:
                    c_label = format_model_label(officer["model_name"])
                    if "sonnet" in officer["model_name"].lower():
                        c_rationale = f"{c_label} telemetry triage: hardware profiling hooks on multi-tenant nodes require eBPF runtime authorization and container boundary validation."
                    else:
                        c_rationale = f"{c_label} constitutional audit: hardware profiling hooks on multi-tenant nodes require signed eBPF runtime authorization."
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=52,
                        violation_category="POTENTIAL_SIDE_CHANNEL_TELEMETRY",
                        rationale=c_rationale,
                        elapsed_seconds=elapsed,
                    )
                elif "gpt" in officer["model_name"] or "o3" in officer["model_name"] or "openai" in officer["model_name"]:
                    o_label = format_model_label(officer["model_name"])
                    if "o3-mini" in officer["model_name"].lower():
                        o_rationale = f"{o_label} static verification: eBPF profiling bytecode inspection verifies zero kernel memory dereferences; acceptable under sampling frequency cap."
                        r_score = 22
                    elif "o3" in officer["model_name"].lower():
                        o_rationale = f"{o_label} deep-reasoning verification: formal side-channel model confirms AMD SEV-SNP cache line encryption limits leakage SNR below 0.005%; approved under dynamic rate-limiting."
                        r_score = 20
                    else:
                        o_rationale = f"{o_label} review: AMD SEV-SNP page encryption contains side-channel SNR; acceptable with runtime sampling quota."
                        r_score = 25
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=r_score,
                        violation_category=None,
                        rationale=o_rationale,
                        elapsed_seconds=elapsed,
                    )
                else:  # Gemini Pro
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=48,
                        violation_category="POTENTIAL_SIDE_CHANNEL_TELEMETRY",
                        rationale="Gemini 3.8 Pro deep-tier audit: hardware counters expose microarchitectural cache timings that warrant host runtime quotas.",
                        elapsed_seconds=elapsed,
                    )

            # 5. Ambiguous Unverified Dependency
            if job.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY:
                if is_pci:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.REJECTED,
                        risk_score=88,
                        violation_category="DYNAMIC_REMOTE_DEPENDENCY_INJECTION",
                        rationale="Objective verification: dynamic runtime package fetch from unpinned external mirror forbidden on PCI-DSS host.",
                        elapsed_seconds=elapsed,
                    )
                elif "claude" in officer["model_name"]:
                    c_label = format_model_label(officer["model_name"])
                    if "sonnet" in officer["model_name"].lower():
                        c_rationale = f"{c_label} supply-chain scan: unpinned dependency from external mirror without SLSA provenance or verified hash violates zero-trust package ingestion policy."
                    else:
                        c_rationale = f"{c_label} constitutional audit: unpinned dependency from external mirror without SLSA Level 3 provenance or immutable digest violates supply-chain security invariants."
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=75,
                        violation_category="SUPPLY_CHAIN_PROVENANCE_MISSING",
                        rationale=c_rationale,
                        elapsed_seconds=elapsed,
                    )
                elif "gpt" in officer["model_name"] or "o3" in officer["model_name"] or "openai" in officer["model_name"]:
                    o_label = format_model_label(officer["model_name"])
                    if "o3-mini" in officer["model_name"].lower():
                        o_rationale = f"{o_label} fast dependency audit: unpinned remote package fetch introduces transient supply-chain vulnerability; requires SHA-256 digest pinning."
                        r_score = 68
                    elif "o3" in officer["model_name"].lower():
                        o_rationale = f"{o_label} deep-reasoning proof: dynamic wheel execution lacks cryptographically verifiable SLSA provenance chain; fails formal dependency invariance."
                        r_score = 72
                    else:
                        o_rationale = f"{o_label} review: dynamic runtime wheel fetch poses remote code execution and dependency confusion vector."
                        r_score = 65
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=r_score,
                        violation_category="DYNAMIC_REMOTE_DEPENDENCY_INJECTION",
                        rationale=o_rationale,
                        elapsed_seconds=elapsed,
                    )
                elif "pro" in officer["model_name"]:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=58,
                        violation_category="RESEARCH_MIRROR_EGRESS",
                        rationale="Gemini 3.8 Pro reasoning audit: remote pip install lacks immutable sha256 checksum lockfile.",
                        elapsed_seconds=elapsed,
                    )
                else:  # Flash
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=50,
                        violation_category="RESEARCH_MIRROR_EGRESS",
                        rationale="Gemini 3.8 Flash evaluation: external academic dependency mirror requires sandbox attestation before execution.",
                        elapsed_seconds=elapsed,
                    )

            # 6. Ambiguous Memory Teardown
            if job.risk_category == WorkloadRiskCategory.CACHE_PURGE_UNCERTAIN:
                if is_pci:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=65,
                        violation_category="UNSYNCHRONIZED_CACHE_TEARDOWN",
                        rationale="Objective banking audit: requires synchronous page zeroing barrier confirmation before node returns to pool.",
                        elapsed_seconds=elapsed,
                    )
                else:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=20,
                        violation_category=None,
                        rationale="Objective hardware isolation: AMD SEV-SNP cryptographic memory encryption active across reservation boundaries.",
                        elapsed_seconds=elapsed,
                    )

            # 7. Ambiguous Borderline Egress
            if job.risk_category == WorkloadRiskCategory.BORDERLINE_EGRESS:
                if is_pci:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.REJECTED,
                        risk_score=90,
                        violation_category="PCI_DSS_THIRD_PARTY_TELEMETRY",
                        rationale="Objective compliance verification: external SaaS telemetry breaks PCI-DSS isolation rules on banking nodes.",
                        elapsed_seconds=elapsed,
                    )
                elif "claude" in officer["model_name"]:
                    c_label = format_model_label(officer["model_name"])
                    if "sonnet" in officer["model_name"].lower():
                        c_rationale = f"{c_label} egress analysis: third-party SaaS egress without outbound TLS certificate pinning creates potential data exfiltration risk."
                    else:
                        c_rationale = f"{c_label} data governance audit: third-party SaaS egress without cryptographic certificate pinning creates unauthorized data exfiltration risk."
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=58,
                        violation_category="UNPINNED_THIRD_PARTY_EGRESS",
                        rationale=c_rationale,
                        elapsed_seconds=elapsed,
                    )
                elif "gpt" in officer["model_name"] or "o3" in officer["model_name"] or "openai" in officer["model_name"]:
                    o_label = format_model_label(officer["model_name"])
                    if "o3-mini" in officer["model_name"].lower():
                        o_rationale = f"{o_label} network boundary triage: SaaS developer telemetry approved under outbound DNS filtering and CIDR allowlist."
                        r_score = 22
                    elif "o3" in officer["model_name"].lower():
                        o_rationale = f"{o_label} deep egress audit: third-party telemetry permissible provided TLS 1.3 session tickets are constrained via SNI-enforcing outbound proxy."
                        r_score = 20
                    else:
                        o_rationale = f"{o_label} review: developer telemetry to standard AI endpoint approved under outbound DNS filtering proxy."
                        r_score = 25
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=r_score,
                        violation_category=None,
                        rationale=o_rationale,
                        elapsed_seconds=elapsed,
                    )
                elif "pro" in officer["model_name"]:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=20,
                        violation_category=None,
                        rationale="Gemini 3.8 Pro review: developer metrics loss curve telemetry permitted on standard commercial node.",
                        elapsed_seconds=elapsed,
                    )
                else:  # Flash
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=15,
                        violation_category=None,
                        rationale="Gemini 3.8 Flash review: external metrics telemetry to standard AI logging platform permissible on non-PCI host.",
                        elapsed_seconds=elapsed,
                    )

            # 8. Benign
            return OfficerVote(
                officer_id=officer["officer_id"],
                model_name=officer["model_name"],
                personality=personality,
                verdict=SecurityVerdict.APPROVED,
                risk_score=5,
                violation_category=None,
                rationale="Objective baseline verified: cryptographic image hash, unprivileged container execution, and scoped egress.",
                elapsed_seconds=elapsed,
            )

        # -------------------------------------------------------------
        # Persona Evaluation for all 32 Big Five (OCEAN) Format C archetypes
        # and legacy 16 MBTI archetypes
        # -------------------------------------------------------------
        p_short = getattr(personality, "short_name", str(personality))
        ocean_code = getattr(personality, "ocean_code", "")
        if len(ocean_code) == 5:
            o_ch, c_ch, _e_ch, a_ch, n_ch = tuple(ocean_code)
            is_strict = (c_ch == "C" and a_ch == "a" and o_ch == "o")
            is_auditor = (c_ch == "C" and a_ch == "a" and o_ch == "O") or (c_ch == "c" and a_ch == "a" and n_ch == "N")
            is_guardian = (c_ch == "C" and a_ch == "A") or (c_ch == "c" and a_ch == "A" and n_ch == "N")
            is_pragmatic = (c_ch == "c" and n_ch == "n")
        else:
            p_code = p_short[:4].upper()
            is_strict = p_code in ("ESTJ", "ISTJ", "ENTJ", "INTJ") or personality == OfficerPersonality.STRICT_COMPLIANCE
            is_auditor = p_code in ("ISTP", "INTP", "ESTP", "ENTP") or personality == OfficerPersonality.ZERO_TRUST_AUDITOR
            is_pragmatic = p_code in ("INFP", "ENFP", "ISFP", "ESFP") or personality == OfficerPersonality.PRAGMATIC_THROUGHPUT
            is_guardian = p_code in ("INFJ", "ENFJ", "ISFJ", "ESFJ")

        # 1. Obvious Severe Attack (cross-tenant escape / cache-timing side-channels)
        if job.risk_category == WorkloadRiskCategory.CROSS_TENANT_ESCAPE:
            return OfficerVote(
                officer_id=officer["officer_id"],
                model_name=officer["model_name"],
                personality=personality,
                verdict=SecurityVerdict.REJECTED,
                risk_score=98,
                violation_category="HOST_ESCAPE_AND_MEMORY_SNOOP",
                rationale=f"{p_short}: Workload executes unprivileged Flush+Reload cache-timing loops, posing high risk of cross-tenant memory snooping.",
                elapsed_seconds=elapsed,
            )

        # 2. Unvetted Binary & Privileged Containers
        if job.risk_category == WorkloadRiskCategory.UNVETTED_BINARY:
            if is_strict:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=92,
                    violation_category="UNVETTED_MUTABLE_IMAGE",
                    rationale=f"{p_short}: Dynamic runtime dependencies and mutable image tags violate strict binary immutability standards.",
                    elapsed_seconds=elapsed,
                )
            elif is_auditor:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=92,
                    violation_category="UNVETTED_MUTABLE_IMAGE",
                    rationale=f"{p_short}: Hands-on inspection reveals unverified dynamic shared library injection. Bypasses isolation mechanisms.",
                    elapsed_seconds=elapsed,
                )
            else:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.FLAGGED,
                    risk_score=65,
                    violation_category="POTENTIAL_PRIVILEGE_OVER_GRANT",
                    rationale=f"{p_short}: Empathizes with developer performance tuning, but recommends disabling dynamic runtime library preloads.",
                    elapsed_seconds=elapsed,
                )

        # 3. Compliance Violation (e.g. Non-PCI scraping on Kove Bank)
        if job.risk_category == WorkloadRiskCategory.COMPLIANCE_VIOLATION:
            if is_pci:
                if is_strict:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.REJECTED,
                        risk_score=90,
                        violation_category="PCI_DSS_EGRESS_VIOLATION",
                        rationale=f"{p_short}: Order and clear rules take precedence. Unauthorized external egress violates Kove Bank PCI-DSS subnet boundary.",
                        elapsed_seconds=elapsed,
                    )
                elif is_pragmatic:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=20,
                        violation_category=None,
                        rationale=f"{p_short}: Standard sentiment streaming pipeline; sees acceptable business intent.",
                        elapsed_seconds=elapsed,
                    )
                else:  # is_auditor or is_guardian
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.FLAGGED,
                        risk_score=75,
                        violation_category="UNCONTROLLED_EGRESS",
                        rationale=f"{p_short}: Hands-on analysis confirms wildcard internet egress (*); potential reputation hazard for banking IP block.",
                        elapsed_seconds=elapsed,
                    )
            else:
                # Non-PCI host (Stowe Architects) -> Allowed
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.APPROVED,
                    risk_score=15,
                    violation_category=None,
                    rationale=f"{p_short}: Host enterprise does not enforce PCI-DSS; web scraping is acceptable.",
                    elapsed_seconds=elapsed,
                )

        # 4. Ambiguous Dual-Use Profiling Tools (e.g. NVML memory profiler)
        if job.risk_category == WorkloadRiskCategory.AMBIGUOUS_DUAL_USE:
            if is_strict:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.FLAGGED,
                    risk_score=60,
                    violation_category="POTENTIAL_SIDE_CHANNEL_TELEMETRY",
                    rationale=f"{p_short}: Established rules require certified telemetry daemons. NVML and hardware counter access introduces potential side-channel timing risks.",
                    elapsed_seconds=elapsed,
                )
            elif is_pragmatic:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.APPROVED,
                    risk_score=15,
                    violation_category=None,
                    rationale=f"{p_short}: Standard MoE GPU profiling metrics; container has no root or host permissions. Empathizes with researcher optimization needs.",
                    elapsed_seconds=elapsed,
                )
            else:  # is_auditor or is_guardian
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.FLAGGED,
                    risk_score=55,
                    violation_category="UNATTESTED_HARDWARE_COUNTERS",
                    rationale=f"{p_short}: Practical inspection shows unverified hardware counter polling; requires verifiable cryptographic attestation of profiling daemon.",
                    elapsed_seconds=elapsed,
                )

        # 5. Ambiguous Unverified Dependency (Dynamic JIT compilation / external mirror)
        if job.risk_category == WorkloadRiskCategory.UNVERIFIED_DEPENDENCY:
            if is_strict:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=88,
                    violation_category="DYNAMIC_REMOTE_DEPENDENCY_INJECTION",
                    rationale=f"{p_short}: Dynamic runtime wheel fetching from non-allowlisted external university mirror violates established supply-chain rules and container immutability.",
                    elapsed_seconds=elapsed,
                )
            elif is_auditor:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=88,
                    violation_category="DYNAMIC_REMOTE_DEPENDENCY_INJECTION",
                    rationale=f"{p_short}: Hands-on binary verification failed. Unpinned external wheels introduce untrusted machine code into host memory.",
                    elapsed_seconds=elapsed,
                )
            else:  # is_pragmatic or is_guardian
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.FLAGGED,
                    risk_score=50,
                    violation_category="RESEARCH_MIRROR_EGRESS",
                    rationale=f"{p_short}: External academic research mirror detected; supports researcher innovation if safely sandboxed in gVisor.",
                    elapsed_seconds=elapsed,
                )

        # 6. Ambiguous Memory Teardown (Async Confidential VM cache wiping)
        if job.risk_category == WorkloadRiskCategory.CACHE_PURGE_UNCERTAIN:
            if is_strict:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.REJECTED,
                    risk_score=82,
                    violation_category="ASYNC_MEMORY_TEARDOWN_RISK",
                    rationale=f"{p_short}: Strict rules dictate zero-residual state. Asynchronous page zeroing creates unverified state window for subsequent tenant workloads on Kove Bank.",
                    elapsed_seconds=elapsed,
                )
            elif is_pragmatic or is_guardian:
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.APPROVED,
                    risk_score=20,
                    violation_category=None,
                    rationale=f"{p_short}: Hardware AMD SEV-SNP encryption provides cryptographically guaranteed isolation during and after execution.",
                    elapsed_seconds=elapsed,
                )
            else:  # is_auditor
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.FLAGGED,
                    risk_score=68,
                    violation_category="UNSYNCHRONIZED_CACHE_TEARDOWN",
                    rationale=f"{p_short}: Hands-on cache inspection shows unsynchronized teardown; requires synchronous page zeroing barrier confirmation before node returns to pool.",
                    elapsed_seconds=elapsed,
                )

        # 7. Ambiguous Borderline Egress (SaaS telemetry / WandB / Hugging Face)
        if job.risk_category == WorkloadRiskCategory.BORDERLINE_EGRESS:
            if is_pci:
                if is_strict:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.REJECTED,
                        risk_score=90,
                        violation_category="PCI_DSS_THIRD_PARTY_TELEMETRY",
                        rationale=f"{p_short}: Piping logs and metrics to third-party public AI hubs breaks PCI-DSS isolation rules on banking nodes.",
                        elapsed_seconds=elapsed,
                    )
                elif is_auditor:
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.REJECTED,
                        risk_score=90,
                        violation_category="PCI_DSS_THIRD_PARTY_TELEMETRY",
                        rationale=f"{p_short}: Network socket inspection reveals unencrypted telemetry egress from banking perimeter. Rejection mandatory.",
                        elapsed_seconds=elapsed,
                    )
                else:  # is_pragmatic or is_guardian
                    return OfficerVote(
                        officer_id=officer["officer_id"],
                        model_name=officer["model_name"],
                        personality=personality,
                        verdict=SecurityVerdict.APPROVED,
                        risk_score=25,
                        violation_category=None,
                        rationale=f"{p_short}: Standard researcher logging to WandB/Hugging Face; egress is payload-restricted HTTPS supporting developer workflow.",
                        elapsed_seconds=elapsed,
                    )
            else:
                # Non-PCI host
                return OfficerVote(
                    officer_id=officer["officer_id"],
                    model_name=officer["model_name"],
                    personality=personality,
                    verdict=SecurityVerdict.APPROVED,
                    risk_score=15,
                    violation_category=None,
                    rationale=f"{p_short}: External metrics telemetry to standard AI platform permissible on commercial rendering host.",
                    elapsed_seconds=elapsed,
                )

        # 8. Benign verified workload
        return OfficerVote(
            officer_id=officer["officer_id"],
            model_name=officer["model_name"],
            personality=personality,
            verdict=SecurityVerdict.APPROVED,
            risk_score=5,
            violation_category=None,
            rationale=f"{p_short}: Verified cryptographic image hash, unprivileged container execution, and scoped egress.",
            elapsed_seconds=elapsed,
        )
