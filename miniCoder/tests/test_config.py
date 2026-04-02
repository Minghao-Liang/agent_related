import os
import unittest
from unittest.mock import patch

from agent_loop import resolve_max_turns


class ConfigTests(unittest.TestCase):
    def test_resolve_max_turns_reads_valid_env(self) -> None:
        with patch.dict(os.environ, {"MINICODER_MAX_TURNS": "24"}, clear=False):
            self.assertEqual(resolve_max_turns(), 24)

    def test_resolve_max_turns_falls_back_on_invalid_env(self) -> None:
        with patch.dict(os.environ, {"MINICODER_MAX_TURNS": "not-a-number"}, clear=False):
            self.assertEqual(resolve_max_turns(), 16)

    def test_resolve_max_turns_falls_back_on_non_positive(self) -> None:
        with patch.dict(os.environ, {"MINICODER_MAX_TURNS": "0"}, clear=False):
            self.assertEqual(resolve_max_turns(), 16)


if __name__ == "__main__":
    unittest.main()
