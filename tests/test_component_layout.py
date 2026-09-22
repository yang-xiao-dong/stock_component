# -*- coding: utf-8 -*-
"""组件排序的持久化、兼容与保存失败回归测试，不操作窗口。"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components.base import AppApi
from core.component_layout import ComponentLayoutStore, normalize_order


class ComponentLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'data' / 'layout.json'
        self.ids = ['analysis', 'group', 'stock']
        self.store = ComponentLayoutStore(self.path)

    def test_first_start_uses_discovery_order(self):
        self.assertEqual(self.store.load(self.ids), self.ids)
        self.assertFalse(self.path.exists())

    def test_order_survives_new_store_instance(self):
        order = ['stock', 'analysis', 'group']
        self.assertTrue(self.store.save(order, self.ids))
        self.assertEqual(ComponentLayoutStore(self.path).load(self.ids), order)
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), {'order': order})

    def test_removed_duplicate_and_new_components(self):
        saved = ['stock', 'old', 'stock', None, {}, 'analysis']
        self.assertEqual(normalize_order(saved, self.ids), ['stock', 'analysis', 'group'])

    def test_bad_file_falls_back_without_breaking_startup(self):
        self.path.parent.mkdir()
        for text in ('not JSON', 'null', '[]', '{"order": "stock"}', '{"unknown": 1}'):
            with self.subTest(text=text):
                self.path.write_text(text, encoding='utf-8')
                with patch('core.component_layout.logger.warning'):
                    self.assertEqual(self.store.load(self.ids), self.ids)

    def test_invalid_request_preserves_previous_file(self):
        self.assertTrue(self.store.save(self.ids, self.ids))
        previous = self.path.read_bytes()
        for invalid in (None, 'stock', ['stock'], ['stock', 'stock', 'group'],
                        ['stock', 'group', 'unknown'], ['stock', 'group', {}]):
            with self.subTest(invalid=invalid):
                self.assertFalse(self.store.save(invalid, self.ids))
                self.assertEqual(self.path.read_bytes(), previous)

    def test_atomic_replace_failure_keeps_previous_order(self):
        self.assertTrue(self.store.save(self.ids, self.ids))
        with patch('core.component_layout.os.replace', side_effect=PermissionError), \
                patch('core.component_layout.logger.warning'):
            self.assertFalse(self.store.save(list(reversed(self.ids)), self.ids))
        self.assertEqual(self.store.load(self.ids), self.ids)
        self.assertEqual(list(self.path.parent.glob('.layout-*.tmp')), [])

    def test_api_save_restart_and_default_restore(self):
        components = [SimpleNamespace(id=key, title=key) for key in self.ids]
        api = AppApi(components, self.store)
        order = list(reversed(self.ids))
        self.assertTrue(api.set_component_order(order))
        self.assertEqual(api.get_component_order(), order)
        restarted = AppApi(components, ComponentLayoutStore(self.path))
        self.assertEqual(restarted.get_component_order(), order)
        returned = restarted.get_component_order()
        returned.clear()
        self.assertEqual(restarted.get_component_order(), order)
        self.assertTrue(restarted.set_component_order(self.ids))
        self.assertEqual(self.store.load(self.ids), self.ids)

    def test_api_does_not_change_current_order_if_save_fails(self):
        components = [SimpleNamespace(id=key, title=key) for key in self.ids]
        api = AppApi(components, self.store)
        with patch.object(self.store, 'save', return_value=False):
            self.assertFalse(api.set_component_order(list(reversed(self.ids))))
        self.assertEqual(api.get_component_order(), self.ids)


if __name__ == '__main__':
    unittest.main()
