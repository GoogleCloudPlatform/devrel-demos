import os
import sys

from unittest.mock import MagicMock

# Hack: Mock markitdown to bypass dependency issues on Python 3.14.
sys.modules["markitdown"] = MagicMock()

from sqlite_rag import SQLiteRag
from sqlite_rag.models.document_result import DocumentResult

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
        top_k           Number of top results to search in both semantic and FTS
                        search. Number of documents may be higher.

    Returns:
        One or more chunks of data containing the related table schemas.
    """

    results = schema_rag.search(search_terms, top_k=top_k)
    return results

