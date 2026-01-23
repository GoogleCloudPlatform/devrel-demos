import os
from sqlite_rag import SQLiteRag
from sqlite_rag.models.document_result import DocumentResult

# Calculate PROJECT_ROOT relative to this file
# This file is in aida_v2/, so ".." is the project root (aicamp/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PACKS_DB_PATH = os.path.join(PROJECT_ROOT, "packs.db")

# open the RAG database
queries_rag = SQLiteRag.create(
    PACKS_DB_PATH, require_existing=True
)


def search_query_library(search_terms: str, platform: str, top_k: int) -> list[DocumentResult]:
    """
    Search the query pack library to find relevant queries corresponding to the
    search terms. For better response quality, use the platform argument to
    specify which platform you are currently investigating (e.g. darwin) 

    Arguments:
        search_terms    Can be either a table name, like "system_info", or one
                        or more search terms like "malware detection".
        platform        One of "linux", "darwin", "windows" or "all"
        top_k           (Optional) Number of top results to search in both semantic and FTS
                        search. Number of documents may be higher. Defaults to 10.

    Returns:
        One or more chunks of data containing the related queries.
    """
    
    query = search_terms
    if platform == "all" or platform is None:
        query += " windows linux darwin"
    else:
        query += " " + platform

    if not top_k:
        top_k = 10

    results = queries_rag.search(query, top_k=top_k)
    return results
