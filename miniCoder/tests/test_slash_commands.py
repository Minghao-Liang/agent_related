import unittest

from agent_loop import SessionStats, handle_slash_command


class SlashCommandTests(unittest.TestCase):
    def test_non_slash_is_not_handled(self) -> None:
        history = [{"role": "user", "content": "hello"}]
        stats = SessionStats(turns=1, input_tokens=10, output_tokens=20)
        result = handle_slash_command("hello", history, stats)
        self.assertFalse(result.handled)
        self.assertEqual(len(history), 1)
        self.assertEqual(stats.turns, 1)

    def test_help_command_returns_supported_commands(self) -> None:
        result = handle_slash_command("/help", [], SessionStats())
        self.assertTrue(result.handled)
        self.assertIn("/clear", result.output)
        self.assertIn("/cost", result.output)
        self.assertIn("/exit", result.output)

    def test_clear_command_clears_history_and_resets_stats(self) -> None:
        history = [{"role": "user", "content": "hello"}]
        stats = SessionStats(turns=2, input_tokens=30, output_tokens=40)
        result = handle_slash_command("/clear", history, stats)
        self.assertTrue(result.handled)
        self.assertEqual(history, [])
        self.assertEqual(stats.turns, 0)
        self.assertEqual(stats.input_tokens, 0)
        self.assertEqual(stats.output_tokens, 0)

    def test_cost_command_reports_session_stats(self) -> None:
        stats = SessionStats(turns=3, input_tokens=120, output_tokens=240)
        result = handle_slash_command("/cost", [], stats)
        self.assertTrue(result.handled)
        self.assertIn("Turns: 3", result.output)
        self.assertIn("Input tokens: 120", result.output)
        self.assertIn("Output tokens: 240", result.output)

    def test_exit_command_requests_termination(self) -> None:
        result = handle_slash_command("/exit", [], SessionStats())
        self.assertTrue(result.handled)
        self.assertTrue(result.should_exit)


if __name__ == "__main__":
    unittest.main()
