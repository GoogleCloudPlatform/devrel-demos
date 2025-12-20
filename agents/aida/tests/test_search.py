import unittest
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aida.schema_rag import discover_schema

class TestSearch(unittest.TestCase):
    def test_process_info_query(self):
        """Test querying for process information table."""
        query = "What table contains process information?"
        print(f"\nSearching for: '{query}'...")
        results = discover_schema(query, top_k=5)
        print(results)
        self.assertIsInstance(results, list)
        self.assertTrue(len(results) > 0)
        # Should contain 'processes' table definition
        self.assertTrue("processes" in str(results).lower())
        self.assertTrue("pid" in str(results).lower())

if __name__ == "__main__":
    unittest.main()

