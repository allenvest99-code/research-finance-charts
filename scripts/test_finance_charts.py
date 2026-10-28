#!/usr/bin/env python3
"""Validation and rendering smoke tests; run with python -m unittest -v."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from finance_charts import (
    MARKETS,
    _read_csv,
    configure_fonts,
    drawdown_series,
    plot_candlestick,
    plot_football_field,
    plot_fundamentals,
    plot_pe_band,
)

SOURCE = "模拟数据｜单元测试"


class FinanceChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        configure_fonts()

    def test_market_color_conventions(self) -> None:
        self.assertNotEqual(MARKETS["cn"]["up"], MARKETS["cn"]["down"])
        self.assertEqual(MARKETS["hk"]["up"], MARKETS["us"]["up"])
        self.assertNotEqual(MARKETS["cn"]["up"], MARKETS["us"]["up"])

    def test_candlestick_rejects_invalid_ohlc(self) -> None:
        df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-05"]),
                "open": [10], "high": [9], "low": [8], "close": [10.5], "volume": [1000],
            }
        )
        with self.assertRaisesRegex(ValueError, "high"):
            plot_candlestick(df, "unused", source=SOURCE, formats="png")

    def test_drawdown_formula(self) -> None:
        result = drawdown_series(pd.Series([100, 50, 75, 125]))
        np.testing.assert_allclose(result.to_numpy(), [0, -0.5, -0.25, 0])

    def test_pe_band_rejects_nonpositive_eps(self) -> None:
        df = pd.DataFrame({"date": pd.to_datetime(["2026-01-05"]), "close": [20], "eps": [0]})
        with self.assertRaisesRegex(ValueError, "eps"):
            plot_pe_band(df, "unused", source=SOURCE, formats="png")

    def test_football_field_rejects_inverted_range(self) -> None:
        df = pd.DataFrame({"method": ["DCF"], "low": [60], "high": [50]})
        with self.assertRaisesRegex(ValueError, "low > high"):
            plot_football_field(df, "unused", source=SOURCE, formats="png")

    def test_csv_reports_missing_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("date,close\n2026-01-05,10\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "eps"):
                _read_csv(path, ("date", "close", "eps"), "date")

    def test_fundamentals_png_smoke(self) -> None:
        df = pd.DataFrame({"period": ["2025", "2026E"], "revenue": [100, 120], "net_profit": [10, 15]})
        with tempfile.TemporaryDirectory() as directory:
            paths = plot_fundamentals(df, Path(directory) / "chart", source=SOURCE, formats="png")
            self.assertEqual(len(paths), 1)
            self.assertTrue(paths[0].is_file())
            self.assertGreater(paths[0].stat().st_size, 10_000)


if __name__ == "__main__":
    unittest.main()
