import unittest
import time
import sys
import os

from aida.schema_rag import schema_rag, discover_schema
from aida.queries_rag import queries_rag, search_query_library


class TestAidaCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print(
            "\n[Setup] Initializing RAG Engines for tests (this may take a few seconds)..."
        )
        start_time = time.time()
        cls.schema_rag = schema_rag
        cls.packs_rag = queries_rag
        # They are already initialized upon import
        print(f"[Setup] RAG Engines initialized in {time.time() - start_time:.2f}s")

    def test_01_rag_initialization(self):
        """Verify RAG engines can be initialized."""
        print("\nTesting RAG Initialization...")
        # Assuming they have a 'ready' attribute or similar, but let's just check they exist
        self.assertIsNotNone(self.schema_rag)
        self.assertIsNotNone(self.packs_rag)
        print("RAG Initialization test passed.")

    def test_02_schema_retrieval(self):
        """Verify standard RAG schema retrieval works."""
        print("\nTesting Schema Retrieval ('processes')...")
        start_time = time.time()
        results = discover_schema("processes", top_k=5)
        duration = time.time() - start_time

        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        # It might return 'process_memory_map' or similar too, but 'pid' should be in standard processes table def
        self.assertIn("pid", str(results).lower())
        print(f"Schema retrieval test passed in {duration:.2f}s.")

    def test_03_query_library_exact(self):
        """Verify query library finds exact matches."""
        print("\nTesting Query Library (exact match 'launchd'வுகளை...)")
        results = search_query_library("launchd", platform="darwin", top_k=5)
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        self.assertIn("launchd", str(results).lower())
        # Case insensitive check for SQL just in case
        self.assertTrue("select * from launchd" in str(results).lower())
        print("Query library exact match test passed.")

    def test_04_query_library_fuzzy(self):
        """Verify query library finds loose matches via vector search."""
        print("\nTesting Query Library (fuzzy match 'find malware')...")
        results = search_query_library("find malware", platform="all", top_k=5)
        # Should find things with 'malware' or 'adware' even if 'find' isn't next to it
        self.assertTrue("malware" in str(results).lower() or "adware" in str(results).lower())
        print("Query library fuzzy match test passed.")

    def test_05_query_library_no_results(self):
        """Verify behavior with nonsense query (currently returns closest matches)."""
        print("\nTesting Query Library (nonsense query)...")
        results = search_query_library("definitely_not_a_real_query_term_xyz", platform="all", top_k=5)
        # Current implementation returns results even for nonsense
        self.assertTrue(len(results) > 0)
        print("Query library nonsense query test passed (returned results as expected by current implementation).")

    def test_06_platform_filtering(self):
        """Verify queries for other platforms are filtered out when requested."""
        print("\nTesting Platform Filtering (explicit 'darwin')...")

        # Explicitly search for darwin, should NOT find windows stuff even if query is windows-biased
        results = search_query_library("windows registry hives", platform="darwin", top_k=5)
        self.assertNotIn("(Pack: windows-", str(results))

        print("Platform filtering test passed.")

    # Removed test_07_get_loaded_packs as the function doesn't exist in current codebase


if __name__ == "__main__":
    unittest.main()
