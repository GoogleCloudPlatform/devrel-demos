import os
import sys
from unittest.mock import MagicMock

# Hack: Mock markitdown to bypass dependency issues on Python 3.14 if present, 
# though standard python usage might not need it. Keeping for safety.
sys.modules["markitdown"] = MagicMock()

from sqlite_rag import SQLiteRag  # noqa: E402
from sqlite_rag.models.document_result import DocumentResult  # noqa: E402

# Calculate PROJECT_ROOT relative to this file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_DB_PATH = os.path.join(PROJECT_ROOT, "schema.db")

# open the RAG database
schema_rag = SQLiteRag.create(
    SCHEMA_DB_PATH, require_existing=True
)


def discover_schema(search_terms: str, top_k: int) -> list[DocumentResult]:
    """
    Queries the osquery schema documentation using RAG and returns all
    table candidates to support the provided search_terms.

    Arguments:
        search_terms    Can be either a table name, like "system_info", or one
                        or more search terms like "system information darwin".
        top_k           (Optional) Number of top results to search in both semantic and FTS
                        search. Number of documents may be higher. Defaults to 10.

    Returns:
        One or more chunks of data containing the related table schemas.
    """

    if not top_k:
        top_k = 10

    results = schema_rag.search(search_terms, top_k=top_k)
    return results
