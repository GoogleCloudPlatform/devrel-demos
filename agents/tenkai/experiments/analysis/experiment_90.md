# Experiment 90: GoDoctor MCP vs Extension

## Overview
This experiment aimed to evaluate the effectiveness of the GoDoctor MCP server compared to the GoDoctor extension, specifically investigating the impact of context injection on tool adoption and success rates.

**Hypothesis:** The "Extension Context" (a detailed guide on how/why to use GoDoctor tools) is the key ingredient for high tool adoption and success, regardless of whether the tools are provided via MCP or the legacy extension mechanism.

## Alternatives
1.  **`godoctor-mcp`**: GoDoctor via MCP, default system prompt.
2.  **`godoctor-mcp-with-extension-context`**: GoDoctor via MCP, with the exact same detailed instructions used by the extension.
3.  **`godoctor-extension`**: The legacy setup (GoDoctor as an extension + detailed instructions).
4.  **`godoctor-mcp-with-custom-context`**: GoDoctor via MCP, with a generic "use specialized tools" prompt.

## Results

### Overall Performance (All Runs)

| Alternative | Success Rate | Avg Duration (s) | Avg Tokens |
|---|---|---|---|
| **godoctor-mcp** | 28/30 (93.3%) | 127.4 | 1.12M |
| **godoctor-mcp-with-extension-context** | 29/30 (96.7%) | 151.7 | 1.23M |
| **godoctor-extension** | 28/30 (93.3%) | 159.6 | 1.42M |
| **godoctor-mcp-with-custom-context** | 28/30 (93.3%) | 145.7 | 1.30M |

### GoDoctor Tool Adoption (Filtered Analysis)
This section filters for runs where the agent *actually used* at least one GoDoctor tool (e.g., `smart_edit`, `read_docs`), ignoring runs where it fell back to standard shell commands.

| Alternative | Adoption Rate | GD Runs | GD Success Rate | Avg Duration (s) | Avg Tokens | Top Tools |
|---|---|---|---|---|---|---|
| **godoctor-mcp-with-extension-context** | **100.0%** | 30 | **96.7%** | 151.7 | 1.23M | `file_create`, `smart_edit`, `read_docs` |
| **godoctor-extension** | **100.0%** | 30 | 93.3% | 159.6 | 1.42M | `file_create`, `smart_edit`, `read_docs` |
| **godoctor-mcp** | 93.3% | 28 | 92.9% | **125.2** | **1.12M** | `file_create`, `smart_edit`, `read_docs` |
| **godoctor-mcp-with-custom-context** | 90.0% | 27 | 92.6% | 142.1 | 1.26M | `file_create`, `smart_edit`, `read_docs` |

## Key Findings

1.  **Context is King for Adoption:** The detailed "Extension Context" guarantees 100% adoption of GoDoctor tools. Both `godoctor-extension` and `godoctor-mcp-with-extension-context` saw the agent use the specialized tools in every single run.
2.  **MCP is More Efficient:** When using the *exact same context*, the MCP implementation (`godoctor-mcp-with-extension-context`) was **~8 seconds faster** and used **~13% fewer tokens** (1.23M vs 1.42M) than the Extension implementation. This suggests the MCP protocol/transport is more efficient or less verbose than the extension mechanism.
3.  **Default MCP is Surprisingly Good:** Even without the detailed context, the base `godoctor-mcp` had a 93.3% adoption rate and was significantly faster (125s) and cheaper (1.12M tokens). This implies the tool definitions themselves are descriptive enough for the model to pick them up most of the time, though the detailed context adds that extra reliability.
4.  **Generic Prompting is Less Effective:** The `custom-context` ("use specialized tools") had the lowest adoption rate (90%). Specific instructions on *which* tools to use and *why* (as in the Extension Context) are far superior to generic advice.

## Recommendation
Standardize on **GoDoctor via MCP** but **keep the detailed "Extension Context" instructions** as part of the system prompt or tool description. This combination (`godoctor-mcp-with-extension-context`) offers the highest reliability (96.7% success, 100% adoption) with better efficiency than the legacy extension.
