import json
import os
import glob
import sys
import re
import sqlite3
from unittest.mock import MagicMock

# Hack: Mock markitdown to bypass dependency issues on Python 3.14.
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
            content = re.sub(r"\\s*\n", " ", content)
            data = json.loads(content)

        pack_platform = data.get("platform", "all")
        queries = data.get("queries", {})

        count = 0
        for query_name, query_data in queries.items():
            sql = query_data.get("query")
            desc = query_data.get("description", "")
            val = query_data.get("value", "")
            # Inherit from pack if not specified in query
            platform = query_data.get("platform", pack_platform)

            # Prepend platform to text for better semantic matching
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
                count += 1
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    print(f"    - Skipping duplicate query: {query_name}")
                else:
                    print(f"    - Error adding query {query_name}: {e}")
            except Exception as e:
                print(f"    - Error adding query {query_name}: {e}")

        print(f"  - Ingested {count} queries from {pack_name}")

    except Exception as e:
        print(f"  - ERROR: Failed to parse {pack_name}: {e}")


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    print(f"Initializing RAG database at {DB_PATH}...")
    rag = SQLiteRag.create(DB_PATH, settings={"quantize_scan": True})

    pack_files = glob.glob(os.path.join(PACKS_DIR, "*.conf")) + glob.glob(
        os.path.join(PACKS_DIR, "*.json")
    )

    if not pack_files:
        print(f"No pack files found in {PACKS_DIR}")
        rag.close()
        return

    for pack_file in pack_files:
        ingest_pack(rag, pack_file)

    print(f"Finished ingesting {len(pack_files)} query pack files.")

    print("Quantizing vectors...")
    rag.quantize_vectors()

    print("Query library ingestion complete.")
    rag.close()


if __name__ == "__main__":
    main()