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
            ["components.group.component", "components.stock.component"],
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
