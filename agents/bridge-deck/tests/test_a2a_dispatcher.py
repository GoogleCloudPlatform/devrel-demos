#!/usr/bin/env python3
"""
Unit tests for core/a2a_dispatcher.py
"""

import unittest
from pathlib import Path
from unittest.mock import MagicMock
from core.a2a_dispatcher import A2ADispatcher


class TestA2ADispatcher(unittest.TestCase):
    def setUp(self):
        self.mock_router = MagicMock()
        self.mock_router.manifests = {
            "lumen": {"name": "Lumen", "role": "Scientific Advisor"},
            "nexus": {"name": "Nexus", "role": "Autonomous Systems Specialist"},
            "rhen": {"name": "Rhen", "role": "Research Specialist"},
            "astra": {"name": "Astra", "role": "Bridge Deck Lead"},
            "vector": {"name": "Vector", "role": "Implementation Lead"}
        }

        self.dispatcher = A2ADispatcher(
            bridge_dir=Path("/tmp"),
            agent_router=self.mock_router,
            load_history_fn=lambda p: {"transactions": []},
            save_history_fn=lambda d, p: None,
            load_projects_fn=lambda: {"projects": []},
            build_messages_fn=lambda *args, **kwargs: ([], ""),
            build_self_context_fn=lambda *args, **kwargs: "",
            max_depth=5
        )

    def tearDown(self):
        self.dispatcher.stop()

    def test_parse_mentions_basic(self):
        text = "@lumen could you review the findings from @rhen?"
        targets = self.dispatcher.parse_mentions(text, sender_id="astra")
        self.assertEqual(targets, ["lumen", "rhen"])

    def test_parse_mentions_filters_sender_self_mention(self):
        text = "Hello @lumen, this is @lumen updating."
        targets = self.dispatcher.parse_mentions(text, sender_id="lumen")
        self.assertEqual(targets, [])

    def test_parse_mentions_filters_human_and_system(self):
        text = "@lead @team @all check in with @nexus please."
        targets = self.dispatcher.parse_mentions(text, sender_id="astra")
        self.assertEqual(targets, ["nexus"])

    def test_pause_and_resume(self):
        self.assertFalse(self.dispatcher.is_paused("proj_1"))
        self.dispatcher.pause("proj_1")
        self.assertTrue(self.dispatcher.is_paused("proj_1"))
        self.assertFalse(self.dispatcher.is_paused("proj_2"))

        self.dispatcher.resume("proj_1")
        self.assertFalse(self.dispatcher.is_paused("proj_1"))

        self.dispatcher.pause()  # Global pause
        self.assertTrue(self.dispatcher.is_paused("proj_1"))
        self.assertTrue(self.dispatcher.is_paused("proj_2"))
        self.dispatcher.resume()
        self.assertFalse(self.dispatcher.is_paused("proj_1"))

    def test_enqueue_if_mentions(self):
        text = "@nexus please coordinate with @rhen."
        enqueued = self.dispatcher.enqueue_if_mentions(
            text=text,
            sender_id="astra",
            sender_name="Astra",
            sender_role="Lead",
            project_id="proj_test"
        )
        self.assertEqual(enqueued, ["nexus", "rhen"])
        self.assertEqual(self.dispatcher.task_queue.qsize(), 2)

        cleared = self.dispatcher.clear_queue()
        self.assertEqual(cleared, 2)
        self.assertEqual(self.dispatcher.task_queue.qsize(), 0)


if __name__ == "__main__":
    unittest.main()
