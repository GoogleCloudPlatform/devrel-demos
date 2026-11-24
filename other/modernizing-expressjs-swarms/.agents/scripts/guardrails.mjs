#!/usr/bin/env node
/**
 * PreToolUse lifecycle hook enforcing workspace safety invariants across all
 * coordinator and /swarm worker sessions:
 *   1. Hard-blocks reading or writing .env / .env.* secret files (allows .env.example).
 *   2. Protects legacy-app/ source code from accidental writes during parallel swarms
 *      (allows docker-compose.yml port exposure; prompts user before touching server.js).
 *   3. Hard-blocks reading workshop docs (root README.md and docs/prompts.md)
 *      so agents derive architecture, domains, and contracts from legacy-app/,
 *      live MongoDB, and the user's current chat prompt; prompts user ("ask")
 *      before modifying them via file tools.
 */

import path from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../.."
);
const LEGACY_APP_DIR = path.resolve(REPO_ROOT, "legacy-app");
const BLOCKED_WORKSHOP_DOCS = [
  { path: path.normalize(path.join(REPO_ROOT, "README.md")), label: "Root 'README.md'" },
  { path: path.normalize(path.join(REPO_ROOT, "docs", "prompts.md")), label: "'docs/prompts.md'" },
];

const ALLOWED_ENV_TEMPLATES = new Set([
  ".env.example",
  ".env.sample",
  ".env.template",
]);

const PATH_ARG_KEYS = new Set([
  "path",
  "filepath",
  "filepaths",
  "file",
  "files",
  "targetfile",
  "absolutepath",
]);

const COMMAND_ARG_KEYS = new Set(["commandline", "command", "cmd"]);

const SHELL_FILE_OPS_REGEX =
  /\b(?:cat|head|tail|less|more|nl|od|xxd|strings|base64|cp|mv|rm|tee|sed|awk|grep|rg|touch|tar|zip|unzip|nano|vim|vi|source|node|python|python3|perl|ruby|jq|diff|cut|sort|tac|rev|hexdump|truncate|dd|bat)\b|\bgit\s+(?:show|diff|grep|cat-file)\b|(?:^|[;&|]\s*)\.\s+|>{1,2}|</;

function normalizeKey(key) {
  return String(key).toLowerCase().replace(/_/g, "");
}

function collectArgStrings(obj, allowedKeys, depth = 0, out = []) {
  if (!obj || typeof obj !== "object" || Array.isArray(obj) || depth > 2) {
    return out;
  }

  for (const [rawKey, value] of Object.entries(obj)) {
    const norm = normalizeKey(rawKey);
    if (
      (norm === "arguments" || norm === "args") &&
      value &&
      typeof value === "object" &&
      !Array.isArray(value)
    ) {
      collectArgStrings(value, allowedKeys, depth + 1, out);
      continue;
    }

    if (!allowedKeys.has(norm)) {
      continue;
    }

    if (typeof value === "string" && value.length > 0) {
      out.push(value);
    } else if (Array.isArray(value)) {
      for (const item of value) {
        if (typeof item === "string" && item.length > 0) {
          out.push(item);
        }
      }
    }
  }

  return out;
}

function respond(decision, reason) {
  const out = reason ? { decision, reason } : { decision };
  process.stdout.write(`${JSON.stringify(out)}\n`);
  process.exit(0);
}

function isProtectedEnvFile(filePath) {
  const base = path.basename(filePath);
  if (ALLOWED_ENV_TEMPLATES.has(base)) return false;
  return base === ".env" || base.startsWith(".env.");
}

function shellTouchesProtectedEnv(cmd) {
  // Strip safe --env-file=... flags first so standalone Node scripts are allowed.
  const stripped = cmd.replace(/--env-file(?:=|\s+)\S+/g, "");
  if (!SHELL_FILE_OPS_REGEX.test(stripped)) return false;

  // Match direct shell inspection, script strings, or redirection targeting .env / .env.<suffix>
  const envTokenRegex =
    /(?:^|[\s'"/])(\.env(?:\.[A-Za-z0-9_.-]+)?)(?=$|[\s'"();&|,])/g;

  for (const match of stripped.matchAll(envTokenRegex)) {
    const tokenBase = path.basename(match[1]);
    if (!ALLOWED_ENV_TEMPLATES.has(tokenBase)) {
      return true;
    }
  }
  return false;
}

function findBlockedWorkshopDoc(resolvedPath) {
  const normalized = path.normalize(resolvedPath);
  return BLOCKED_WORKSHOP_DOCS.find((doc) => doc.path === normalized) || null;
}

function shellTouchesBlockedWorkshopDoc(cmd, cwd) {
  if (!SHELL_FILE_OPS_REGEX.test(cmd)) return null;

  const docTokenRegex =
    /(?:^|[\s'"=:])([^\s'"=:()]*(?:README|prompts)\.md)(?=$|[\s'"();&|,])/g;
  for (const match of cmd.matchAll(docTokenRegex)) {
    const resolved = path.resolve(cwd, match[1]);
    const blocked = findBlockedWorkshopDoc(resolved);
    if (blocked) {
      return blocked;
    }
  }
  return null;
}

let raw = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  raw += chunk;
});

process.stdin.on("end", () => {
  try {
    const payload = JSON.parse(raw || "{}");
    const toolName = String(payload?.toolCall?.name || "").toLowerCase();
    const args = payload?.toolCall?.args || {};
    const cwd = payload?.cwd || process.cwd();
    const nestedToolName =
      typeof args?.ToolName === "string"
        ? args.ToolName
        : typeof args?.toolName === "string"
          ? args.toolName
          : "";
    const effectiveToolName = `${toolName} ${nestedToolName}`.toLowerCase();
    const isMutationTool =
      effectiveToolName.includes("write") ||
      effectiveToolName.includes("edit") ||
      effectiveToolName.includes("replace") ||
      effectiveToolName.includes("delete");

    // 1. Inspect file path arguments across read/write/edit/MCP tools (case-insensitive)
    const rawPaths = collectArgStrings(args, PATH_ARG_KEYS);

    for (const rawPath of rawPaths) {
      const resolved = path.resolve(cwd, rawPath);

      const blockedDoc = findBlockedWorkshopDoc(resolved);
      if (blockedDoc) {
        if (isMutationTool) {
          respond(
            "ask",
            `Modifying ${blockedDoc.label} requires explicit user confirmation.`
          );
        }
        respond(
          "deny",
          `Blocked by modernization-guardrails: ${blockedDoc.label} is workshop documentation and off-limits to agents. Derive all domains, schemas, and routes directly from 'legacy-app/' and live MongoDB.`
        );
      }

      if (isProtectedEnvFile(resolved)) {
        respond(
          "deny",
          `Blocked by modernization-guardrails: Accessing '${path.basename(resolved)}' is prohibited. Ask the user to inspect or update environment variables, and use 'node --env-file=.env.local' when running standalone scripts.`
        );
      }

      const relFromLegacy = path.relative(LEGACY_APP_DIR, resolved);
      const isInsideLegacy =
        relFromLegacy === "" ||
        (!relFromLegacy.startsWith("..") && !path.isAbsolute(relFromLegacy));
      if (isMutationTool && isInsideLegacy) {
        const relInsideLegacy = relFromLegacy.split(path.sep).join("/");
        if (
          relInsideLegacy === "docker-compose.yml" ||
          relInsideLegacy === "docker-compose.yaml"
        ) {
          continue;
        }
        if (relInsideLegacy === "server.js") {
          respond(
            "ask",
            "Modifying legacy-app/server.js (e.g., for Mongoose EADDRINUSE reconnect guard) requires explicit user confirmation."
          );
        }
        const displayTarget = relInsideLegacy
          ? `legacy-app/${relInsideLegacy}`
          : "legacy-app";
        respond(
          "deny",
          `Blocked by modernization-guardrails: '${displayTarget}' is read-only ground-truth source code. Implement changes in 'modern-app/' instead.`
        );
      }
    }

    // 2. Inspect shell commands for direct .env or workshop doc reads/writes
    const shellCommands = collectArgStrings(args, COMMAND_ARG_KEYS);
    for (const cmd of shellCommands) {
      if (shellTouchesProtectedEnv(cmd)) {
        respond(
          "deny",
          "Blocked by modernization-guardrails: Shell commands reading or writing .env / .env.* files are prohibited. Ask the user to verify or edit environment variables."
        );
      }
      const blockedDoc = shellTouchesBlockedWorkshopDoc(cmd, cwd);
      if (blockedDoc) {
        respond(
          "deny",
          `Blocked by modernization-guardrails: Shell commands reading or writing ${blockedDoc.label} are prohibited. Derive all domains, schemas, and routes directly from 'legacy-app/' and live MongoDB.`
        );
      }
    }

    respond("allow");
  } catch {
    // Fail open on unexpected hook payloads so normal tool execution is never wedged
    respond("allow");
  }
});
