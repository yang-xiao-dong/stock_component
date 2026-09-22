# -*- coding: utf-8 -*-
"""预警组件缓存与模式隔离测试：不联网、不启动窗口。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components.analysis.component import AnalysisApi


class AlertComponentTests(unittest.TestCase):
    def test_short_term_failure_does_not_hide_long_term(self):
        api = AnalysisApi()
        with patch('components.analysis.component.STOCKS', [{'code': 'a', 'name': 'A'}]), \
                patch.object(api, '_mode_key', return_value=('offline', '2026-09-22')), \
                patch('components.analysis.component.data_source.get_realtime_batch', return_value={'a': {'price': 10}}), \
                patch('components.analysis.component.data_source.get_kline', return_value=[{'close': 10}]), \
                patch('components.analysis.component.evaluate_long_term', return_value={'status': 'uptrend'}), \
                patch('components.analysis.component.data_source.get_minute_data', side_effect=OSError):
            api._refresh()
            board = api.get_analysis()
        self.assertEqual(board['long_term'][0]['status'], 'uptrend')
        self.assertEqual(board['short_term'][0]['status'], 'insufficient')

    def test_refresh_registered_with_shared_scheduler(self):
        class Scheduler:
            def add(self, *args, **kwargs):
                self.args, self.kwargs = args, kwargs
        scheduler = Scheduler()
        AnalysisApi(scheduler)
        self.assertEqual(scheduler.args[0], 'analysis.scan')
        self.assertTrue(scheduler.kwargs['immediate'])

    def test_mode_switch_hides_previous_board(self):
        api = AnalysisApi()
        with patch('components.analysis.component.data_source.get_mode', return_value={
            'mode': 'offline', 'date': '2026-09-21',
        }), patch('components.analysis.component.data_source.get_realtime_batch', return_value={}):
            api._refresh()
            self.assertEqual(api.get_analysis()['status'], 'ready')
        with patch('components.analysis.component.data_source.get_mode', return_value={
            'mode': 'offline', 'date': '2026-09-22',
        }):
            board = api.get_analysis()
            self.assertEqual(board['status'], 'loading')
            self.assertEqual(board['short_term'], [])

    def test_failure_clears_old_signals(self):
        api = AnalysisApi()
        with patch.object(api, '_mode_key', return_value=('offline', '2026-09-22')):
            api._source_key = ('offline', '2026-09-22')
            api._board = {'status': 'ready', 'short_term': [{'status': 'signal'}]}
            with patch('components.analysis.component.data_source.get_realtime_batch', side_effect=OSError):
                api._refresh()
            self.assertEqual(api.get_analysis()['status'], 'error')
            self.assertEqual(api.get_analysis()['short_term'], [])

    def test_mode_changed_while_scanning_discards_result(self):
        api = AnalysisApi()
        with patch.object(api, '_mode_key', side_effect=[('offline', '2026-09-21'), ('offline', '2026-09-22')]), \
                patch('components.analysis.component.data_source.get_realtime_batch', return_value={}):
            api._refresh()
        self.assertIsNone(api._board)


if __name__ == '__main__':
    unittest.main()
