# -*- coding: utf-8 -*-
"""长线判断离线测试：均线趋势、区间边界、历史隔离。"""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ANALYSIS
from components.analysis.long_term import evaluate_long_term


class LongTermTests(unittest.TestCase):
    def setUp(self):
        self.stock = {"code": "a", "name": "合成股票"}
        self.quote = {"price": 121, "change_pct": 2.5, "time": "20260922150000"}
        self.day = "2026-09-22"
        self.bars = [{"date": (date(2026, 5, 1) + timedelta(days=i)).isoformat(),
                      "close": 100 + i * .2, "high": 101 + i * .2, "low": 99 + i * .2}
                     for i in range(100)]

    def evaluate(self):
        return evaluate_long_term(self.stock, self.quote, self.bars, ANALYSIS['long_term'], self.day)

    def test_uptrend_and_original_percentage(self):
        result = self.evaluate()
        self.assertEqual(result['status'], 'uptrend')
        self.assertEqual(result['change_pct'], 2.5)
        self.assertAlmostEqual(result['ma_medium'], sum(b['close'] for b in self.bars[-20:]) / 20)
        self.assertAlmostEqual(result['ma_long'], sum(b['close'] for b in self.bars[-60:]) / 60)

    def test_downtrend(self):
        for i, bar in enumerate(self.bars):
            bar['close'], bar['high'], bar['low'] = 120 - i * .2, 121 - i * .2, 119 - i * .2
        self.assertEqual(self.evaluate()['status'], 'downtrend')

    def test_flat_market_is_range(self):
        for bar in self.bars:
            bar['close'], bar['high'], bar['low'] = 100, 101, 99
        self.assertEqual(self.evaluate()['status'], 'range')

    def test_historical_range_not_current_quote(self):
        self.quote['price'] = 500
        result = self.evaluate()
        self.assertAlmostEqual(result['support'], self.bars[-20]['low'])
        self.assertAlmostEqual(result['resistance'], self.bars[-1]['high'])
        self.assertEqual(result['as_of'], self.bars[-1]['date'])

    def test_partial_current_day_candle_ignored(self):
        before = self.evaluate()
        self.bars.append({'date': self.day, 'close': 1, 'high': 1000, 'low': 1})
        self.assertEqual(self.evaluate(), before)

    def test_incomplete_history_is_not_a_trend(self):
        self.bars = self.bars[:59]
        self.assertEqual(self.evaluate()['status'], 'insufficient')

    def test_wrong_day_and_invalid_data(self):
        self.quote['time'] = '20260921150000'
        self.assertEqual(self.evaluate()['status'], 'insufficient')
        self.quote['time'] = '20260922150000'
        self.quote['price'] = float('nan')
        self.assertEqual(self.evaluate()['status'], 'insufficient')


if __name__ == '__main__':
    unittest.main()
