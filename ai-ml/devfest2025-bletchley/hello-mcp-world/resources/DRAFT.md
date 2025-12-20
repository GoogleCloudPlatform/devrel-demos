+++
date = '2025-11-03T09:00:00Z'
draft = false
title = 'How to Build an Offline Agent with ADK, Ollama and SQLite'
tags = ['ai', 'python', 'tutorial', 'rag', 'gemini', 'adk']
categories = ['AI & Development']
summary = "Learn how to make your AI agent completely offline. We walk through swapping the cloud model for a local Qwen 2.5 via Ollama, and building a local RAG knowledge base using SQLite and `sqlite-rag` to query Osquery schemas and packs."
+++

In [our last post]({{< ref "/posts/20251031-building-aida/index.md" >}}), we focused on building a custom client interface for our agent. It was a great step in making the agent more usable, but it was still lacking a key feature: what happens when the network is down?

While I think this would be a problem for any agent, the nuance here is that we are building an "Emergency Diagnostic Agent" - what good is an emergency diagnostic agent if you cannot use it when the network is offline?

This led me to think about a fallback mechanism - what if we could run diagnostics with only local dependencies? This would involve not only replacing the core model, but also devising a new RAG strategy.

The benefits are clear: while connected we can use the most capable online models, but in a degraded scenario, we can fallback to a local model until we are back to a healthy state. Not only this, it also enables use cases where this agent is used in silo'ed environments or where privacy is a concern.

In this article we are going to focus on the features required to make a local diagnostic agent possible.

## Swapping the cloud model for a local one

One of the most widely adopted ways of running local models is through [**Ollama**](https://ollama.com/). If you are running your code on a Mac you can install Ollama using [Homebrew](https://brew.sh/) (if not, you should check the official Homebrew website for the installation steps for your OS):

```bash
brew install ollama
```

Once Ollama is installed you can download models using `ollama pull`. For example:

```bash
ollama pull qwen2.5
```

You can pull models based on their names alone (which will pull the "default" version), or use specific tags for different versions. It is very common that a model family like [`qwen2.5`](https://ollama.com/library/qwen2.5) provides different sizes of models, like 1B, 2B, 7B, etc., and also fine-tuned versions for certain use cases (text, image processing, etc).

To check which models are available and what are their sizes and capabilities you should access the [Ollama library](https://ollama.com/library).

For our use case, naturally the smarter the model it would be better, but bigger models also require a more powerful hardware. We also need to make sure that the model we select has native tool calling capabilities, as it needs to be able to coordinate different tool calls to [**Osquery**](https://osquery.io/) and our RAG tool.

After evaluating a few models, I decided to use Qwen 2.5 7B. You can see its capabilities by running `ollama show`:

```bash
$ ollama show qwen2.5
  Model
    architecture        qwen2     
    parameters          7.6B      
    context length      32768     
    embedding length    3584      
    quantization        Q4_K_M    

  Capabilities
    completion    
    tools
```

### Why Qwen 2.5?
I tested a few options to see which could handle AIDA's tool-calling requirements:

*   **GPT-OSS:** Provided rich conversation but was very naive at tool calling. For example, it often got stuck in loops, requesting `SELECT * FROM system_info` (and variations of this query) repeatedly without making progress.
*   **Llama 3.1:** Struggled both with conversational flow and tool calling.
*   **Qwen 2.5:** Best local model for tool calling while keeping a nice conversation flow.

It's not quite at the level of [**Gemini 2.5 Flash**](https://deepmind.google/technologies/gemini/flash/) for complex query planning, but for a completely offline model, it is sufficient.

### Running local models with LiteLLM

To connect Qwen to agent the we use [**LiteLLM**](https://www.litellm.ai/), a library that provides a unified interface for LLM providers. This allows us to swap out the model with a single line of code:

```python
# aida/agent.py
from google.adk.models.lite_llm import LiteLlm

# ... inside the agent definition ...
# Instead of a hardcoded string like "gemini-2.5-flash",
# we create a LiteLLM object with the model string
MODEL = LiteLlm(model="ollama_chat/qwen2.5")

# ... and pass MODEL to the root agent:
root_agent = Agent(
    model=MODEL,
    name="aida",
    description="The emergency diagnostic agent",
    # ... instructions and tool definitions omitted ...
)
```

**Note:** the first part of the model string is the LiteLLM "provider" (e.g. `ollama_chat` in `ollama_chat/qwen2.5`). While `ollama` is a valid provider, it is recommended to use `ollama_chat` for [better responses](https://docs.litellm.ai/docs/providers/ollama).

This is everything you need to run a local model in ADK. You can test the agent and see how it responds. You may also want to compare the responses with the `gemini-2.5-flash` model we were using before.

<video controls width="100%" src="aida_demo_hd.mov">
  Your browser does not support the video tag.
</video>
<p style="text-align: center; font-style: italic; opacity: 0.8; margin-top: 0.5rem;">AIDA running first with Gemini 2.5 Flash and then Qwen2.5. Gemini is notably faster and requires less tool calls. Qwen's response time is highly dependent on local hardware - this demo is running on an Apple MacBook Pro M4 with 48GB of RAM.</p>

Great, we have the model running local! It's now time to tackle our next cloud dependency: [**Vertex AI RAG**](https://cloud.google.com/vertex-ai/docs/generative-ai/grounding/overview).

## Building an offline knowledge base with SQLite RAG

To be honest, while using Vertex AI RAG made a complex part of the project manageable, Vertex AI RAG was an overkill. Vertex AI RAG is designed for large enterprise use cases where you are dealing with massive amounts of data.

For this agent we just need a basic schema retrieval mechanism. The osquery schema is also very stable, meaning once you build it you will hardly touch it ever again. Given these characteristics it is very hard to justify using Vertex AI RAG to host it... it's like using a cannon to kill a fly.

Since we are already in the [**SQLite**](https://www.sqlite.org/) ecosystem due to Osquery, the natural step was to look for a RAG solution using SQLite as a backend. After a Google search I found a very promising project: **[`sqlite-rag`](https://github.com/sqliteai/sqlite-rag)**.

Of course, as is often the case in development, it wasn't quite that simple.

### Challenge: Python 3.14 dependency problems

SQLite has the concept of extensions to augment its capabilities, and `sqlite-rag` is built with this in mind.

One issue I had when initially testing `sqlite-rag` is that the default Python installation on Mac OS comes with a version of the SQLite package that has extensions disabled (for security reasons).

To work around this limitation, my solution was to install a new version of Python (3.14) with Homebrew. This also required a bit of fiddling with the symlinks for the `python3` command to make sure I was using the Homebrew version of Python and not the system one.

If you face a similar challenge, make sure you are using the right version of Python by comparing the output of these two commands (and adjust your PATH variable if they are not):

```bash
$ which python3
/Users/petruzalek/homebrew/opt/python@3.14/libexec/bin/python3
$ brew info python3
==> python@3.14: stable 3.14.0
...
==> Caveats
Python is installed as
  /Users/petruzalek/homebrew/bin/python3

Unversioned symlinks `python`, `python-config`, `pip` etc. pointing to
`python3`, `python3-config`, `pip3` etc., respectively, are installed into
  /Users/petruzalek/homebrew/opt/python@3.14/libexec/bin

See: https://docs.brew.sh/Homebrew-and-Python
```

With 3.14 (aka pi-thon) installed, I tried to use `sqlite-rag` as it is, but it was failing due to one of the dependencies not being available on 3.14 yet: `sqlite-rag` depends on [`markitdown`](https://github.com/microsoft/markitdown), `markitdown` depends on [`magika`](https://google.github.io/magika/), which in turn depends on [`onnxruntime`](https://onnxruntime.ai/), but `onnxruntime` lacked pre-built wheels for Python 3.14 on macOS ARM64, causing the install to fail. >.<

Since AIDA only needs to ingest plain text `.table` files right now, I didn't actually *need* `markitdown`'s document parsing capabilities. Rather than downgrading my entire Python environment, I chose a quick and dirty hack: mocking the offending module before `sqlite-rag` could try to import it.

```python
import sys
from unittest.mock import MagicMock

# PRE-FLIGHT HACK:
# 'markitdown' depends on 'onnxruntime', which fails to install/load
# on Python 3.14 on macOS ARM64.
#
# Since we only use plain text ingestion, we mock it out to bypass the crash.
sys.modules["markitdown"] = MagicMock()

from sqlite_rag import SQLiteRag
```

It's not pretty, but it works. This should not stay forever in the code, but unblocks us until the dependency problems are fixed.

### Populating the RAG with osquery schemas

With `sqlite-rag` working, the next step was to ingest the Osquery schema. This is done with a script, `ingest_osquery.py`, that walks through the schema directory and add each `.table` file to the RAG database:

```python
# ingest_osquery.py
import os
# ... markitdown hack omitted ...
from sqlite_rag import SQLiteRag

DB_PATH = os.path.abspath("schema.db")
SPECS_DIR = os.path.abspath("osquery_data/specs")


def ingest(rag: SQLiteRag, file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    rel_path = os.path.relpath(file_path, SPECS_DIR)
    rag.add_text(content, uri=rel_path, metadata={"source": "osquery_specs"})


if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    print(f"Initializing RAG database at {DB_PATH}...")
    rag = SQLiteRag.create(DB_PATH, settings={"quantize_scan": True})

    print(f"Scanning {SPECS_DIR} for .table files...")
    files_to_ingest = []
    for root, _, files in os.walk(SPECS_DIR):
        for file in files:
            if file.endswith(".table"):
                files_to_ingest.append(os.path.join(root, file))

    total_files = len(files_to_ingest)
    print(f"Found {total_files} files to ingest.")

    for i, file_path in enumerate(files_to_ingest):
        ingest(rag, file_path)

        if (i + 1) % 50 == 0:
            print(f"Ingested {i + 1}/{total_files}...")

    print(f"Finished ingesting {total_files} files.")

    print("Quantizing vectors...")
    rag.quantize_vectors()

    print("Quantization complete.")
    rag.close()
```

After ingestion, there is a quantization step. For those unfamiliar, quantization is a technique to compress the high-dimensional vector embeddings, converting them from large 32-bit floating-point numbers into compact 8-bit integers.

This is important for a local setup. Without quantization, storing high-dimensional vectors would bloat the SQLite database, and similarity searches would become sluggish on a standard laptop. By quantizing, we sacrifice a bit of precision for a massive gain in speed and storage efficiency.

### Enabling the agent to query the schemas RAG

Now we need to implement the `schema_discovery` tool using `SQLiteRag`:

```python
# aida/schema_rag.py
import os
# ... markitdown hack omitted ...
from sqlite_rag import SQLiteRag
from sqlite_rag.models.document_result import DocumentResult

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DB_PATH = os.path.join(PROJECT_ROOT, "schema.db")

# open the RAG database
schema_rag = SQLiteRag.create(
    SCHEMA_DB_PATH, require_existing=True
)


def discover_schema(search_terms: str, top_k: int = 5) -> list[DocumentResult]:
    """
    Queries the osquery schema documentation using RAG and returns all
    table candidates to support the provided search_terms.

    Arguments:
        search_terms    Can be either a table name, like "system_info", or one
                        or more search terms like "system information darwin".
        top_k           Number of top results to search in both semantic and FTS
                        search. Number of documents may be higher.

    Returns:
        One or more chunks of data containing the related table schemas.
    """

    results = schema_rag.search(search_terms, top_k=top_k)
    return results
```

With the RAG in place, AIDA can now look up table definitions on its own.

![Screenshot of AIDA](image-1.png "Query 'run schema discovery for battery' using Qwen")

Schema discovery works, but we still have a problem.

## Closing the intelligence gap with expert knowledge

Developing for a local model like Qwen 2.5 (7B parameters) is very different from developing for a cloud model like Gemini 2.5 Flash.

First, there's the **context window**. Gemini gives you a 1 million token context window, allowing you to dump entire documentation sets into the prompt or be very verbose with your instructions. Qwen 2.5 has a comparatively tiny 32k context window, so you have to be much more selective about what you feed to the model.

Second, Qwen is not a **thinking model** like Gemini 2.5 Flash, which means it won't refine the answer by itself, often needing more guidance than Gemini 2.5 Flash.

To bridge this gap, we need to be smarter about how we structure the agent's instructions and tools.

### A simplified system prompt

To save some tokens, we are going to provide simplified instructions, stripping components that would consume many tokens like the name of available tables. Now we are going to rely purely on our tools to build the best queries.

```python
root_agent = Agent(
    model=MODEL,
    name="aida",
    description="The emergency diagnostic agent",
    instruction="""
[IDENTITY]
You are AIDA, the Emergency Diagnostic Agent. You are a cute, friendly, and highly capable expert.
Your mission is to help the user identify and resolve system issues efficiently.

[OPERATIONAL WORKFLOW]
1. DISCOVER: Use `discover_schema` to find relevant tables and understand their columns.
2. EXECUTE: Use `run_osquery` to execute the chosen or constructed query.
    """,
    tools=[
        discover_schema,
        run_osquery,
    ],
)
```

The `discover_schema` tools can do pretty well if the search terms are very close to the actual table schema, but what if we could do better and provide entire queries based on a known knowledge base instead?

### A new RAG for well-known queries

Fortunately, we don't need to teach it everything from scratch. The Osquery community has a great knowledge base of what queries are useful for certain types of diagnostics. Even better, they provide those queries as open source "query packs" that can be installed in any Osquery system for proactive monitoring. We have query packs for all sorts of things, like threat detection and compliance auditing, which sounds exactly like the kind of knowledge we want AIDA to have.

The thing is that query packs are meant to be installed in an Osquery daemon that monitors the system in background. Those queries have a certain pre-configured frequency and can trigger alerts for monitoring dashboards. We don't want to install the queries as monitoring tools, but enable AIDA to use those queries on demand. So, instead of installing the packs with the normal process, we are going to give them as text to AIDA in the form of a second RAG.

The Osquery repository has a few [example packs](https://github.com/osquery/osquery/tree/master/packs) we can use to get started.

Here is the new ingestion script, `ingest_packs.py`, very similar to the previous one, but for processing the query packs:

```python
# ingest_packs.py
import json
import os
import glob
import sys
import re
import sqlite3
from unittest.mock import MagicMock

sys.modules["markitdown"] = MagicMock()
from sqlite_rag import SQLiteRag

DB_PATH = os.path.abspath("packs.db")
PACKS_DIR = "osquery_data/packs"

def ingest_pack(rag, pack_path):
    pack_name = os.path.basename(pack_path).replace(".conf", "").replace(".json", "")
    print(f"Ingesting pack: {pack_name}...")

    try:
        with open(pack_path, "r") as f:
            content = f.read()
            content = re.sub(r"\s*\n", " ", content)
            data = json.loads(content)

        pack_platform = data.get("platform", "all")
        queries = data.get("queries", {})

        for query_name, query_data in queries.items():
            sql = query_data.get("query")
            desc = query_data.get("description", "")
            val = query_data.get("value", "")
            platform = query_data.get("platform", pack_platform)

            text_to_embed = f"Platform: {platform}\nName: {query_name}\nDescription: {desc}\nRationale: {val}\nSQL: {sql}"
            metadata = {
                "name": query_name,
                "pack": pack_name,
                "query": sql,
                "description": desc,
                "value": val,
                "platform": platform,
            }
            try:
                rag.add_text(text_to_embed, metadata=metadata)
            except sqlite3.IntegrityError:
                pass # Skip duplicates

    except Exception as e:
        print(f"  - ERROR: Failed to parse {pack_name}: {e}")

def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    rag = SQLiteRag.create(DB_PATH, settings={"quantize_scan": True})
    pack_files = glob.glob(os.path.join(PACKS_DIR, "*.conf")) + glob.glob(
        os.path.join(PACKS_DIR, "*.json")
    )

    for pack_file in pack_files:
        ingest_pack(rag, pack_file)

    rag.quantize_vectors()
    rag.close()

if __name__ == "__main__":
    main()
```

The tool definition also follows pretty much the same pattern as the schema discovery:

```python
# aida/queries_rag.py
import os
# ... markitdown hack omitted ...
from sqlite_rag import SQLiteRag
from sqlite_rag.models.document_result import DocumentResult

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKS_DB_PATH = os.path.join(PROJECT_ROOT, "packs.db") 

queries_rag = SQLiteRag.create(
    PACKS_DB_PATH, require_existing=True
)

def search_query_library(search_terms: str, platform: str = "all", top_k: int = 5) -> list[DocumentResult]:
    """
    Search the query pack library to find relevant queries corresponding to the
    search terms. For better response quality, use the platform argument to
    specify which platform you are currently investigating (e.g. darwin) 

    Arguments:
        search_terms    Can be either a table name, like "system_info", or one
                        or more search terms like "malware detection".
        platform        One of "linux", "darwin", "windows" or "all"
        top_k           Number of top results to search in both semantic and FTS
                        search. Number of documents may be higher.

    Returns:
        One or more chunks of data containing the related queries.
    """

    if platform == "all" or platform is None:
        search_terms += " windows linux darwin"
    else:
        search_terms += " " + platform

    results = queries_rag.search(search_terms, top_k=top_k)
    return results
```

Finally, we need to make the agent aware of the new tool and teach it when to use with the system instructions:

```python
# aida/agent.py
root_agent = Agent(
    # ...
    instruction="""
[OPERATIONAL WORKFLOW]
Follow this sequence for most investigations to ensure efficiency and accuracy:
1. SEARCH: For high-level tasks (e.g., "check for rootkits"), FIRST use `search_query_library`.
2. DISCOVER: If no suitable pre-made query is found, use `discover_schema` to find relevant tables and understand their columns.
3. EXECUTE: Use `run_osquery` to execute the chosen or constructed query.
    """,
    tools=[
        search_query_library,
        discover_schema,
        run_osquery,
    ],
)
```

And here is it in action:

![Screenshot of AIDA](image-2.png "AIDA running a malware check. Note how it searched the query library for relevant queries as it is shown in the logs.")

The fun part is that this tool not only helps Qwen2.5 to become more useful, but even Gemini 2.5 Flash can benefit from it. It is one of those cases where optimising for the lowest common denominator actually improves the system as a whole.

## Conclusion

We have now a proper emergency diagnostic agent that is capable of diagnosing computer problems even without access to the internet. That is... assuming you have a beefy enough machine to run the model! I guess nothing is perfect, right? :)

This article only captures a few of the improvements I've added to AIDA over the past couple of days. For the full project, please check out [AIDA on Github](https://github.com/danicat/aida).

## References

*   [Gemini 2.5 Flash](https://deepmind.google/technologies/gemini/flash/)
*   [LiteLLM](https://www.litellm.ai/)
*   [Ollama](https://ollama.com/)
*   [Osquery](https://osquery.io/)
*   [Qwen 2.5 (Ollama Library)](https://ollama.com/library/qwen2.5)
*   [SQLite](https://www.sqlite.org/)
*   [sqlite-rag](https://github.com/sqliteai/sqlite-rag)
*   [Vertex AI RAG](https://cloud.google.com/vertex-ai/docs/generative-ai/grounding/overview)