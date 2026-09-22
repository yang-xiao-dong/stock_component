# -*- coding: utf-8 -*-
"""预警规则离线测试：价格时序、趋势、站稳、缺失与过期行情。"""
import copy
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import ANALYSIS
from components.analysis.short_term import evaluate_washout


class AlertCalcTests(unittest.TestCase):
    def setUp(self):
        self.stock = {"code": "a", "name": "合成股票"}
        self.day = "2026-09-22"
        self.now = datetime(2026, 9, 22, 10, 15)
        self.quote = {"price": 103, "prev_close": 100, "change_pct": 3.0,
                      "time": "20260922101500"}
        self.minute = []
        for index in range(46):
            price = 104 if 10 <= index < 20 else 100
            if index == 20:
                price = 99.5
            elif index >= 31:
                price = 103
            stamp = datetime(2026, 9, 22, 9, 30) + timedelta(minutes=index)
            self.minute.append({"time": stamp.strftime("%H%M"), "price": price, "date": self.day})
        self.bars = [{"date": (datetime(2026, 9, 1) + timedelta(days=i)).date().isoformat(),
                      "close": 95 + i * .2} for i in range(20)]
        self.settings = copy.deepcopy(ANALYSIS["short_term"])

    def evaluate(self, live=True):
        return evaluate_washout(self.stock, self.quote, self.minute, self.bars,
                                self.settings, self.day, self.now if live else None)

    def test_clear_reversal_triggers_with_raw_quote_percent(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "signal")
        self.assertEqual(result["change_pct"], 3.0)
        self.assertEqual(result["peak_time"], "09:49")
        self.assertEqual(result["trough_time"], "09:50")
        self.assertAlmostEqual(result["drawdown_pct"], 4.5 / 104 * 100)
        self.assertAlmostEqual(result["rebound_pct"], 3.5 / 99.5 * 100)
        self.assertAlmostEqual(result["recovery_pct"], 3.5 / 4.5 * 100)

    def test_small_move_does_not_trigger(self):
        for point in self.minute:
            point["price"] = 100 + (point["price"] - 100) * .1
        self.quote["price"] = 100.3
        self.assertEqual(self.evaluate()["status"], "clear")

    def test_downtrend_does_not_trigger(self):
        for index, bar in enumerate(self.bars):
            bar["close"] = 110 - index * .2
        self.assertEqual(self.evaluate()["status"], "clear")

    def test_current_day_bar_is_not_used_for_trend(self):
        self.bars.append({"date": self.day, "close": 1000})
        self.assertEqual(self.evaluate()["status"], "signal")

    def test_rebound_must_hold(self):
        self.minute[-3]["price"] = 100
        self.assertEqual(self.evaluate()["status"], "clear")

    def test_incomplete_hold_cannot_trigger(self):
        self.minute.pop(-3)
        self.assertEqual(self.evaluate()["status"], "insufficient")

    def test_new_decline_removes_signal(self):
        self.quote["price"] = 98
        self.assertEqual(self.evaluate()["status"], "clear")

    def test_low_before_high_does_not_count_as_drawdown(self):
        for index, point in enumerate(self.minute):
            point["price"] = 99 + index / 10
        self.quote["price"] = self.minute[-1]["price"]
        self.assertEqual(self.evaluate()["status"], "clear")

    def test_insufficient_history_or_minute_data(self):
        self.bars = self.bars[:5]
        self.assertEqual(self.evaluate()["status"], "insufficient")
        self.setUp()
        self.minute = self.minute[:5]
        self.assertEqual(self.evaluate()["status"], "insufficient")

    def test_stale_quote_is_rejected_live_but_allowed_in_snapshot(self):
        self.now += timedelta(minutes=10)
        self.assertEqual(self.evaluate()["status"], "insufficient")
        self.assertEqual(self.evaluate(live=False)["status"], "signal")

    def test_wrong_day_or_missing_date_cannot_trigger(self):
        for date in ("2026-09-21", None):
            for point in self.minute:
                point["date"] = date
            self.assertEqual(self.evaluate()["status"], "insufficient")

    def test_stale_minutes_cannot_trigger(self):
        self.minute = self.minute[:-6]
        self.assertEqual(self.evaluate()["status"], "insufficient")

    def test_thresholds_are_configurable(self):
        self.settings["min_drawdown_pct"] = 6
        self.assertEqual(self.evaluate()["status"], "clear")

    def test_invalid_and_future_points_are_ignored(self):
        self.minute += [{"date": self.day, "time": "1016", "price": 1},
                        {"date": self.day, "time": "0935", "price": float('nan')},
                        {"date": self.day, "time": "1260", "price": 1}]
        self.assertEqual(self.evaluate()["status"], "signal")

    def test_colon_time_format_supported(self):
        for point in self.minute:
            point["time"] = point["time"][:2] + ':' + point["time"][2:]
        self.assertEqual(self.evaluate()["status"], "signal")


if __name__ == "__main__":
    unittest.main()
