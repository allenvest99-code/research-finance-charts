#!/usr/bin/env python3
"""Professional financial charts for research reports.

Dependencies: Python 3.10+, matplotlib, pandas, numpy.
Run: python finance_charts.py <chart-type> <input.csv> <output-base> --source "..."
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Rectangle
import numpy as np
import pandas as pd

BG = "#FCFAF5"
INK = "#252A30"
MUTED = "#6E747B"
GRID = "#DDD9D0"
BLUE = "#276A9B"
GOLD = "#C38B32"
TEAL = "#2E8378"
RED = "#B74A4A"
PURPLE = "#75658D"
PALE_BLUE = "#A9C4D6"

MARKETS = {
    "cn": {"up": "#C84343", "down": "#17805C", "currency": "¥", "name": "A股"},
    "hk": {"up": "#16865C", "down": "#C84A4A", "currency": "HK$", "name": "港股"},
    "us": {"up": "#16865C", "down": "#C84A4A", "currency": "$", "name": "美股"},
}

CHART_TYPES = ("candlestick", "fundamentals", "pe-band", "drawdown", "football-field")


def configure_fonts() -> None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    candidates = (
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    )
    selected = next((name for name in candidates if name in available), "DejaVu Sans")
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": [selected, "DejaVu Sans"],
            "axes.unicode_minus": False,
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "svg.fonttype": "none",
        }
    )


def _frame(title: str, subtitle: str, source: str, width: float, height: float):
    if not source.strip():
        raise ValueError("必须提供数据来源；模拟数据须明确标注为模拟数据")
    fig = plt.figure(figsize=(width, height), facecolor=BG)
    fig.text(0.07, 0.955, title, fontsize=18, fontweight="bold", color=INK, va="top")
    if subtitle:
        fig.text(0.07, 0.895, subtitle, fontsize=10.5, color=MUTED, va="top")
    fig.text(0.07, 0.035, source, fontsize=8.5, color=MUTED, va="bottom")
    return fig


def _style_axis(ax, grid_axis: str = "y") -> None:
    ax.set_facecolor(BG)
    ax.grid(axis=grid_axis, color=GRID, linewidth=0.7, linestyle=(0, (2, 3)), alpha=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, labelsize=9)


def _save(fig, output: str | Path, formats: str = "both") -> list[Path]:
    base = Path(output)
    if base.suffix.lower() in (".png", ".svg"):
        base = base.with_suffix("")
    base.parent.mkdir(parents=True, exist_ok=True)
    suffixes = ("png", "svg") if formats == "both" else (formats,)
    paths: list[Path] = []
    for suffix in suffixes:
        path = base.with_suffix(f".{suffix}")
        kwargs = {"facecolor": BG, "bbox_inches": "tight", "pad_inches": 0.16}
        if suffix == "png":
            kwargs["dpi"] = 300
        fig.savefig(path, **kwargs)
        paths.append(path)
    plt.close(fig)
    return paths


def _read_csv(path: str | Path, required: Iterable[str], date_column: str | None = None) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise ValueError(f"找不到输入文件：{csv_path}")
    df = pd.read_csv(csv_path)
    if df.empty:
        raise ValueError("输入 CSV 没有数据行")
    required = list(required)
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"CSV 缺少字段：{', '.join(missing)}")
    if date_column:
        df[date_column] = pd.to_datetime(df[date_column], errors="raise")
        if df[date_column].duplicated().any():
            raise ValueError(f"{date_column} 存在重复日期")
        df = df.sort_values(date_column).reset_index(drop=True)
    return df


def _numbers(df: pd.DataFrame, columns: Iterable[str], positive: Iterable[str] = ()) -> None:
    positive = set(positive)
    for column in columns:
        df[column] = pd.to_numeric(df[column], errors="raise")
        values = df[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"{column} 含空值或非有限数值")
        if column in positive and (values <= 0).any():
            raise ValueError(f"{column} 必须全部大于 0")


def _dates_axis(ax) -> None:
    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


def plot_candlestick(
    df: pd.DataFrame,
    output: str | Path,
    *,
    market: str = "cn",
    title: str = "价格、均线与成交量",
    subtitle: str = "日线｜OHLC 与成交量",
    source: str,
    formats: str = "both",
    ma_windows: tuple[int, ...] = (20, 50),
) -> list[Path]:
    required = ("date", "open", "high", "low", "close", "volume")
    _numbers(df, required[1:], positive=("open", "high", "low", "close"))
    if (df["volume"] < 0).any():
        raise ValueError("volume 不能为负数")
    if (df["high"] < df[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("存在 high 小于 open／close／low 的记录")
    if (df["low"] > df[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("存在 low 大于 open／close／high 的记录")
    if market not in MARKETS:
        raise ValueError(f"不支持的市场：{market}")
    for window in ma_windows:
        if window <= 0:
            raise ValueError("均线窗口必须为正整数")

    style = MARKETS[market]
    fig = _frame(title, subtitle, source, 11, 7.2)
    grid = fig.add_gridspec(
        2, 1, height_ratios=(3.2, 1), left=0.08, right=0.95, bottom=0.16, top=0.79, hspace=0.06
    )
    ax = fig.add_subplot(grid[0])
    volume_ax = fig.add_subplot(grid[1], sharex=ax)
    _style_axis(ax)
    _style_axis(volume_ax)
    x = mdates.date2num(df["date"].dt.to_pydatetime())
    width = 0.66
    colors = np.where(df["close"] >= df["open"], style["up"], style["down"])

    for xi, (_, row), color in zip(x, df.iterrows(), colors):
        ax.vlines(xi, row["low"], row["high"], color=color, linewidth=0.85, zorder=2)
        body_bottom = min(row["open"], row["close"])
        body_height = max(abs(row["close"] - row["open"]), row["close"] * 0.0006)
        ax.add_patch(
            Rectangle(
                (xi - width / 2, body_bottom), width, body_height,
                facecolor=color, edgecolor=color, linewidth=0.6, zorder=3,
            )
        )
    volume_ax.bar(x, df["volume"], width=width, color=colors, alpha=0.72)

    ma_colors = (GOLD, PURPLE, TEAL)
    for index, window in enumerate(ma_windows):
        if len(df) >= window:
            ax.plot(
                df["date"], df["close"].rolling(window).mean(),
                color=ma_colors[index % len(ma_colors)], linewidth=1.35, label=f"MA{window}",
            )
    if len(df) >= min(ma_windows):
        ax.legend(loc="upper left", frameon=False, fontsize=9, ncol=len(ma_windows))
    ax.set_ylabel(f"价格（{style['currency']}）", fontsize=9)
    volume_ax.set_ylabel("成交量", fontsize=9)
    volume_ax.yaxis.set_major_formatter(lambda value, _: f"{value / 1e6:.0f}M" if value >= 1e6 else f"{value:,.0f}")
    plt.setp(ax.get_xticklabels(), visible=False)
    ax.xaxis.get_offset_text().set_visible(False)
    _dates_axis(volume_ax)
    ax.set_xlim(x[0] - 2, x[-1] + 2)
    return _save(fig, output, formats)


def plot_fundamentals(
    df: pd.DataFrame,
    output: str | Path,
    *,
    title: str = "营收、净利润与净利率",
    subtitle: str = "历史与预测财务表现",
    source: str,
    unit: str = "亿元",
    formats: str = "both",
) -> list[Path]:
    _numbers(df, ("revenue", "net_profit"))
    if (df["revenue"] == 0).any():
        raise ValueError("revenue 不能为 0，否则无法计算净利率")
    periods = df["period"].astype(str)
    x = np.arange(len(df))
    width = 0.34
    margin = df["net_profit"] / df["revenue"] * 100

    fig = _frame(title, subtitle, source, 10.5, 6.2)
    ax = fig.add_axes((0.08, 0.18, 0.84, 0.62))
    _style_axis(ax)
    revenue_bars = ax.bar(x - width / 2, df["revenue"], width, color=BLUE, label="营业收入")
    profit_bars = ax.bar(x + width / 2, df["net_profit"], width, color=GOLD, label="净利润")
    ax.set_xticks(x, periods)
    ax.set_ylabel(f"金额（{unit}）", fontsize=9)
    margin_ax = ax.twinx()
    margin_ax.plot(x, margin, color=INK, marker="o", markersize=3.5, linewidth=1.5, label="净利率")
    margin_ax.set_ylabel("净利率（%）", fontsize=9, color=MUTED)
    margin_ax.tick_params(length=0, labelsize=9, colors=MUTED)
    for side in ("top", "right", "left", "bottom"):
        margin_ax.spines[side].set_visible(False)
    handles = [revenue_bars, profit_bars, margin_ax.lines[0]]
    ax.legend(handles, [h.get_label() for h in handles], loc="upper left", frameon=False, fontsize=9, ncol=3)
    ax.bar_label(revenue_bars, fmt="%.0f", padding=2, fontsize=7.5, color=MUTED)
    ax.bar_label(profit_bars, fmt="%.0f", padding=2, fontsize=7.5, color=MUTED)
    return _save(fig, output, formats)


def plot_pe_band(
    df: pd.DataFrame,
    output: str | Path,
    *,
    market: str = "cn",
    title: str = "股价与 PE Band",
    subtitle: str = "价格与不同市盈率倍数对应的估值区间",
    source: str,
    bands: tuple[float, ...] = (8, 12, 16, 20, 24),
    formats: str = "both",
) -> list[Path]:
    _numbers(df, ("close", "eps"), positive=("close", "eps"))
    if market not in MARKETS:
        raise ValueError(f"不支持的市场：{market}")
    if not bands or any(band <= 0 for band in bands):
        raise ValueError("PE 倍数必须全部大于 0")
    bands = tuple(sorted(set(bands)))
    colors = ("#B8CFDC", "#8FB2C7", "#6294B1", "#376F91", "#234E70", PURPLE, GOLD)
    fig = _frame(title, subtitle, source, 10.8, 6.2)
    ax = fig.add_axes((0.08, 0.18, 0.82, 0.62))
    _style_axis(ax)
    ax.plot(df["date"], df["close"], color=INK, linewidth=1.8, label="股价", zorder=5)
    for index, band in enumerate(bands):
        color = colors[index % len(colors)]
        values = df["eps"] * band
        ax.plot(df["date"], values, color=color, linewidth=1.15, label=f"{band:g}x")
        ax.text(df["date"].iloc[-1], values.iloc[-1], f"  {band:g}x", color=color, fontsize=8.5, va="center")
    ax.set_ylabel(f"价格（{MARKETS[market]['currency']}）", fontsize=9)
    ax.legend(loc="upper left", frameon=False, fontsize=8.5, ncol=min(len(bands) + 1, 6))
    _dates_axis(ax)
    return _save(fig, output, formats)


def drawdown_series(nav: pd.Series) -> pd.Series:
    values = pd.to_numeric(nav, errors="raise").astype(float)
    if values.empty or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("nav 必须全部大于 0 且不能含空值")
    return values / values.cummax() - 1


def plot_drawdown(
    df: pd.DataFrame,
    output: str | Path,
    *,
    title: str = "净值表现与最大回撤",
    subtitle: str = "期初归一化净值与历史回撤",
    source: str,
    formats: str = "both",
) -> list[Path]:
    _numbers(df, ("nav",), positive=("nav",))
    has_benchmark = "benchmark_nav" in df.columns
    if has_benchmark:
        _numbers(df, ("benchmark_nav",), positive=("benchmark_nav",))
    drawdown = drawdown_series(df["nav"])
    normalized = df["nav"] / df["nav"].iloc[0]
    max_date = df["date"].iloc[int(drawdown.idxmin())]
    max_drawdown = float(drawdown.min())

    fig = _frame(title, subtitle, source, 10.8, 7.0)
    grid = fig.add_gridspec(
        2, 1, height_ratios=(2.2, 1.2), left=0.08, right=0.94, bottom=0.16, top=0.79, hspace=0.12
    )
    ax = fig.add_subplot(grid[0])
    dd_ax = fig.add_subplot(grid[1], sharex=ax)
    _style_axis(ax)
    _style_axis(dd_ax)
    ax.plot(df["date"], normalized, color=BLUE, linewidth=1.7, label="组合／标的")
    if has_benchmark:
        benchmark = df["benchmark_nav"] / df["benchmark_nav"].iloc[0]
        ax.plot(df["date"], benchmark, color=MUTED, linewidth=1.25, label="基准")
    ax.axhline(1, color=GRID, linewidth=0.8)
    ax.set_ylabel("期初净值 = 1", fontsize=9)
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    plt.setp(ax.get_xticklabels(), visible=False)

    dd_ax.fill_between(df["date"], drawdown * 100, 0, color=RED, alpha=0.22)
    dd_ax.plot(df["date"], drawdown * 100, color=RED, linewidth=1.25)
    dd_ax.scatter([max_date], [max_drawdown * 100], color=RED, s=22, zorder=5)
    dd_ax.annotate(
        f"最大回撤 {max_drawdown:.1%}",
        xy=(max_date, max_drawdown * 100), xytext=(12, -2), textcoords="offset points",
        fontsize=9, color=RED, va="center",
    )
    dd_ax.set_ylabel("回撤（%）", fontsize=9)
    _dates_axis(dd_ax)
    return _save(fig, output, formats)


def plot_football_field(
    df: pd.DataFrame,
    output: str | Path,
    *,
    title: str = "估值 Football Field",
    subtitle: str = "不同估值方法对应的每股价值区间",
    source: str,
    current_price: float | None = None,
    target_price: float | None = None,
    currency: str = "¥",
    formats: str = "both",
) -> list[Path]:
    _numbers(df, ("low", "high"), positive=("low", "high"))
    if (df["low"] > df["high"]).any():
        raise ValueError("估值区间存在 low > high")
    for name, value in (("current_price", current_price), ("target_price", target_price)):
        if value is not None and (not np.isfinite(value) or value <= 0):
            raise ValueError(f"{name} 必须大于 0")
    labels = df["method"].astype(str)
    y = np.arange(len(df))[::-1]
    palette = (BLUE, GOLD, TEAL, PURPLE, PALE_BLUE, MUTED)
    fig = _frame(title, subtitle, source, 10.5, max(5.4, 1.0 + len(df) * 0.62))
    ax = fig.add_axes((0.20, 0.18, 0.72, 0.62))
    _style_axis(ax, grid_axis="x")
    label_pad = float((df["high"].max() - df["low"].min()) * 0.01)
    for index, (_, row) in enumerate(df.iterrows()):
        yi = y[index]
        color = palette[index % len(palette)]
        ax.barh(yi, row["high"] - row["low"], left=row["low"], height=0.5, color=color, alpha=0.88)
        ax.text(row["low"] - label_pad, yi + 0.32, f"{currency}{row['low']:g}", fontsize=8, color=MUTED, ha="right")
        ax.text(row["high"] + label_pad, yi + 0.32, f"{currency}{row['high']:g}", fontsize=8, color=MUTED, ha="left")
    ax.set_yticks(y, labels)
    ax.set_xlabel(f"每股价值（{currency}）", fontsize=9)
    if current_price is not None:
        ax.axvline(current_price, color=RED, linestyle=(0, (4, 3)), linewidth=1.4, label=f"现价 {currency}{current_price:g}")
    if target_price is not None:
        ax.axvline(target_price, color=INK, linewidth=1.4, label=f"目标价 {currency}{target_price:g}")
    if current_price is not None or target_price is not None:
        ax.legend(loc="upper left", frameon=False, fontsize=9)
    return _save(fig, output, formats)


def _float_tuple(value: str) -> tuple[float, ...]:
    try:
        return tuple(float(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("应为逗号分隔的数字，例如 8,12,16,20,24") from exc


def _int_tuple(value: str) -> tuple[int, ...]:
    try:
        return tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError("应为逗号分隔的整数，例如 20,50") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chart_type", choices=CHART_TYPES)
    parser.add_argument("input", help="输入 CSV；字段见 references/chart-schemas.md")
    parser.add_argument("output", help="输出文件基名，可省略扩展名")
    parser.add_argument("--source", required=True, help="数据来源与日期；模拟数据必须明确标注")
    parser.add_argument("--title", default=None)
    parser.add_argument("--subtitle", default=None)
    parser.add_argument("--market", choices=tuple(MARKETS), default="cn")
    parser.add_argument("--format", choices=("png", "svg", "both"), default="both")
    parser.add_argument("--bands", type=_float_tuple, default=(8, 12, 16, 20, 24))
    parser.add_argument("--ma", type=_int_tuple, default=(20, 50))
    parser.add_argument("--unit", default="亿元")
    parser.add_argument("--current-price", type=float)
    parser.add_argument("--target-price", type=float)
    parser.add_argument("--currency", default="¥")
    return parser


def main() -> None:
    configure_fonts()
    args = build_parser().parse_args()
    common = {
        "output": args.output,
        "source": args.source,
        "formats": args.format,
    }
    optional = {}
    if args.title is not None:
        optional["title"] = args.title
    if args.subtitle is not None:
        optional["subtitle"] = args.subtitle
    try:
        if args.chart_type == "candlestick":
            df = _read_csv(args.input, ("date", "open", "high", "low", "close", "volume"), "date")
            paths = plot_candlestick(df, market=args.market, ma_windows=args.ma, **common, **optional)
        elif args.chart_type == "fundamentals":
            df = _read_csv(args.input, ("period", "revenue", "net_profit"))
            paths = plot_fundamentals(df, unit=args.unit, **common, **optional)
        elif args.chart_type == "pe-band":
            df = _read_csv(args.input, ("date", "close", "eps"), "date")
            paths = plot_pe_band(df, market=args.market, bands=args.bands, **common, **optional)
        elif args.chart_type == "drawdown":
            df = _read_csv(args.input, ("date", "nav"), "date")
            paths = plot_drawdown(df, **common, **optional)
        else:
            df = _read_csv(args.input, ("method", "low", "high"))
            paths = plot_football_field(
                df, current_price=args.current_price, target_price=args.target_price,
                currency=args.currency, **common, **optional,
            )
    except (ValueError, KeyError, pd.errors.ParserError) as exc:
        raise SystemExit(f"输入或渲染错误：{exc}") from exc
    for path in paths:
        print(path.resolve())


if __name__ == "__main__":
    main()
