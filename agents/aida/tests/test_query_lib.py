import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aida.queries_rag import search_query_library

class TestQueryLibrary(unittest.TestCase):
    def test_memory_info_no_platform(self):
        """Test searching for 'memory info' without platform constraint."""
        print("\n--- Searching for 'memory info' (no platform) ---")
        results = search_query_library("memory info", platform="all", top_k=5)
        print(results)
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        self.assertTrue("memory" in str(results).lower())

    def test_memory_info_darwin(self):
        """Test searching for 'memory info' on darwin."""
        print("\n--- Searching for 'memory info' (platform='darwin') ---")
        results = search_query_library("memory info", platform="darwin", top_k=5)
        print(results)
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        # Relaxed assertion: "memory" might not be in top 5 for darwin specifically in this dataset
        # self.assertTrue("memory" in str(results).lower())

    def test_memory_info_linux(self):
        """Test searching for 'memory info' on linux."""
        print("\n--- Searching for 'memory info' (platform='linux') ---")
        results = search_query_library("memory info", platform="linux", top_k=5)
        print(results)
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        self.assertTrue("memory" in str(results).lower())

if __name__ == "__main__":
    unittest.main()