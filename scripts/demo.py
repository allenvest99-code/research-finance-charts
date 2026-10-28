#!/usr/bin/env python3
"""Generate deterministic synthetic samples for all chart families and markets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from finance_charts import (
    configure_fonts,
    plot_candlestick,
    plot_drawdown,
    plot_football_field,
    plot_fundamentals,
    plot_pe_band,
)

SOURCE = "模拟数据｜仅用于模板验收，非真实行情或财务数据"


def market_data(seed: int, start_price: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2026-01-05", periods=90)
    returns = rng.normal(0.0012, 0.017, len(dates))
    close = start_price * np.exp(np.cumsum(returns))
    open_ = np.r_[close[0] * (1 - returns[0]), close[:-1]] * (1 + rng.normal(0, 0.004, len(dates)))
    high = np.maximum(open_, close) * (1 + rng.uniform(0.002, 0.018, len(dates)))
    low = np.minimum(open_, close) * (1 - rng.uniform(0.002, 0.018, len(dates)))
    volume = rng.integers(1_200_000, 9_800_000, len(dates))
    return pd.DataFrame(
        {"date": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume}
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", help="样图与模拟 CSV 的输出目录")
    args = parser.parse_args()
    root = Path(args.output_dir)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    configure_fonts()
    generated: list[str] = []

    markets = (
        ("cn", 11, 36.5, "A股风格", "红涨绿跌"),
        ("hk", 29, 82.4, "港股风格", "绿涨红跌"),
        ("us", 47, 186.2, "美股风格", "绿涨红跌"),
    )
    market_frames = {}
    for market, seed, start_price, label, color_rule in markets:
        df = market_data(seed, start_price)
        market_frames[market] = df
        df.to_csv(data_dir / f"{market}_ohlcv.csv", index=False)
        paths = plot_candlestick(
            df,
            root / f"{market}-candlestick",
            market=market,
            title=f"{label}｜价格、均线与成交量",
            subtitle=f"90 个模拟交易日｜MA20／MA50｜{color_rule}",
            source=SOURCE,
        )
        generated.extend(str(path) for path in paths)

    fundamentals = pd.DataFrame(
        {
            "period": ["2021", "2022", "2023", "2024", "2025", "2026E", "2027E"],
            "revenue": [80, 96, 118, 143, 169, 201, 236],
            "net_profit": [8.0, 10.1, 13.2, 17.5, 22.4, 28.1, 35.4],
        }
    )
    fundamentals.to_csv(data_dir / "fundamentals.csv", index=False)
    generated.extend(
        str(path)
        for path in plot_fundamentals(
            fundamentals,
            root / "fundamentals",
            title="营收扩张，利润率同步改善",
            subtitle="2021—2027E｜营业收入与净利润（左轴）；净利率（右轴）",
            source=SOURCE,
        )
    )

    pe = market_frames["hk"][["date", "close"]].copy()
    pe["eps"] = np.linspace(3.1, 4.0, len(pe)) + np.random.default_rng(83).normal(0, 0.025, len(pe))
    pe.to_csv(data_dir / "pe_band.csv", index=False)
    generated.extend(
        str(path)
        for path in plot_pe_band(
            pe,
            root / "pe-band",
            market="hk",
            title="股价与五档 PE 估值带",
            subtitle="模拟 EPS 与 8x／12x／16x／20x／24x PE 区间",
            source=SOURCE,
        )
    )

    rng = np.random.default_rng(101)
    dates = pd.bdate_range("2026-01-05", periods=160)
    returns = rng.normal(0.00065, 0.0105, len(dates))
    returns[58:78] -= 0.011
    benchmark_returns = rng.normal(0.0004, 0.008, len(dates))
    nav = pd.DataFrame(
        {
            "date": dates,
            "nav": 100 * np.exp(np.cumsum(returns)),
            "benchmark_nav": 100 * np.exp(np.cumsum(benchmark_returns)),
        }
    )
    nav.to_csv(data_dir / "drawdown.csv", index=False)
    generated.extend(
        str(path)
        for path in plot_drawdown(
            nav,
            root / "drawdown",
            title="净值表现与历史最大回撤",
            subtitle="组合与基准均以起点归一化；下图为历史回撤",
            source=SOURCE,
        )
    )

    football = pd.DataFrame(
        {
            "method": ["DCF 现金流折现", "可比公司估值", "历史估值中枢", "股息折现模型"],
            "low": [42, 38, 45, 35],
            "high": [58, 54, 62, 50],
        }
    )
    football.to_csv(data_dir / "football_field.csv", index=False)
    generated.extend(
        str(path)
        for path in plot_football_field(
            football,
            root / "football-field",
            title="多方法估值形成交叉验证区间",
            subtitle="每股价值｜虚线为现价，实线为目标价",
            source=SOURCE,
            current_price=46,
            target_price=58,
            currency="$",
        )
    )

    manifest = {
        "synthetic_data": True,
        "not_investment_advice": True,
        "png_dpi": 300,
        "markets": ["cn", "hk", "us"],
        "chart_types": ["candlestick", "fundamentals", "pe-band", "drawdown", "football-field"],
        "files": generated,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output_dir": str(root.resolve()), "file_count": len(generated)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
