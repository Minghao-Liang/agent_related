import tempfile
import unittest
from pathlib import Path

from tools import execute_tool, get_tool_schemas
from tools.registry import initialize_tools


class ToolSystemTests(unittest.TestCase):
    def test_tool_schemas_expose_core_tools(self) -> None:
        names = {tool["name"] for tool in get_tool_schemas()}
        self.assertTrue(
            {
                "bash",
                "read_file",
                "write_file",
                "file_edit",
                "glob",
                "grep",
                "web_fetch",
            }.issubset(names)
        )

    def test_execute_tool_returns_unknown_tool_error(self) -> None:
        output = execute_tool("not_exists", {})
        self.assertIn("unknown tool", output)

    def test_file_edit_updates_file_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "demo.txt"
            file_path.write_text("hello world", encoding="utf-8")
            initialize_tools(Path(tmpdir))
            output = execute_tool(
                "file_edit",
                {
                    "path": "demo.txt",
                    "old_text": "world",
                    "new_text": "miniCoder",
                },
            )
            self.assertIn("Updated", output)
            self.assertEqual(file_path.read_text(encoding="utf-8"), "hello miniCoder")
            initialize_tools(Path(__file__).resolve().parent.parent)


if __name__ == "__main__":
    unittest.main()
