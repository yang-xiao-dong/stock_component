# -*- coding: utf-8 -*-
"""builder 模块离线测试。"""
import tempfile
import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from builder.build import discover_component_modules, parse_version, pyinstaller_args


class BuilderTests(unittest.TestCase):

    def test_parse_version(self):
        self.assertEqual(parse_version("1.2.3"), ("1.2.3", (1, 2, 3, 0)))
        self.assertEqual(parse_version("1.2.3.4"), ("1.2.3.4", (1, 2, 3, 4)))
        with self.assertRaises(ValueError):
            parse_version("v1.2")

    def test_discovers_current_components(self):
        self.assertEqual(
            discover_component_modules(),
            ["components.analysis.component", "components.group.component",
             "components.pe_compare.component", "components.stock.component"],
        )

    def test_arguments_create_versioned_single_file_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            args, output = pyinstaller_args("2.3.4", tmp)
        self.assertIn("--onefile", args)
        self.assertIn("--windowed", args)
        self.assertIn("components.group.component", args)
        self.assertEqual(output.name, "股票小组件-v2.3.4.exe")


if __name__ == "__main__":
    unittest.main()


class BuildIdentityTests(unittest.TestCase):
    def test_display_version_and_git_id(self):
        from builder.build import display_version, git_build_id
        self.assertEqual(display_version("1.2.6", "abc1234", False), "1.2.6+gabc1234")
        self.assertEqual(display_version("1.2.6", "abc1234", True), "1.2.6+gabc1234+dirty")
        short, full, dirty = git_build_id()
        self.assertTrue(short)

    def test_build_record_table_appends_rows_with_header(self):
        from builder.build import append_build_record
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            table = Path(tmp) / "发布版本.md"
            append_build_record("1.2.6", "1.2.6+gabc1234", "abcdef1234567890", False, "首例", table)
            append_build_record("1.2.7", "1.2.7+gabd9999+dirty", "abd9999aaaa", True, "", table)
            text = table.read_text(encoding="utf-8")
        self.assertIn("| 展示版本 | git |", text)
        self.assertIn("1.2.6+gabc1234", text)
        self.assertIn("含未提交改动", text)
        self.assertEqual(text.count("\n| 1.2"), 2)

    def test_version_file_carries_build_identity(self):
        from builder.build import pyinstaller_args
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pyinstaller_args("2.3.4", tmp, "2.3.4+gabc1234")
        info = (ROOT / "build" / "generated" / "version_info.txt").read_text(encoding="utf-8")
        self.assertIn("'2.3.4+gabc1234'", info)
