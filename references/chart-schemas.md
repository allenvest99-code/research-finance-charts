# 数据契约与命令

所有 CSV 使用 UTF-8。字段名必须完全一致；空值、无穷值和非数值会报错。日期支持 ISO `YYYY-MM-DD`，同一序列不得重复。

## candlestick

字段：`date,open,high,low,close,volume`

- 使用同一复权口径；成交量单位须在副标题或来源中说明。
- `high` 不得低于 open／close／low，`low` 不得高于 open／close／high。
- 建议 20—250 根 K线；过长时间序列先聚合为周线或月线。
- `--ma 20,50` 修改均线窗口；`--market cn|hk|us` 修改市场样式。

```bash
python scripts/finance_charts.py candlestick ohlcv.csv output/price \
  --market us --ma 20,50 --source "来源：Yahoo Finance，2026-06-30；后复权"
```

## fundamentals

字段：`period,revenue,net_profit`

- period 为字符串，例如 `2024`、`2025Q4`、`2026E`；预测期必须带 `E`。
- revenue 与 net_profit 使用同一币种和金额单位；净利率由脚本计算。
- `--unit` 默认“亿元”，可改为“百万美元”“亿港元”等。

```bash
python scripts/finance_charts.py fundamentals financials.csv output/financials \
  --unit "百万美元" --source "来源：公司年报及模型，2026-06-30"
```

## pe-band

字段：`date,close,eps`

- close 与 eps 必须大于 0；EPS 口径必须一致，例如固定使用同一forward EPS或滚动EPS。
- EPS 与股价的币种一致；不同市场会计准则或汇率换算需在来源中说明。
- `--bands 8,12,16,20,24` 修改倍数。

```bash
python scripts/finance_charts.py pe-band pe.csv output/pe-band \
  --market hk --bands 8,12,16,20,24 --source "来源：iFinD及模型，2026-06-30"
```

## drawdown

必需字段：`date,nav`；可选字段：`benchmark_nav`

- nav 与 benchmark_nav 必须大于 0；可为净值、指数或总资产价值，但不要混用口径。
- 脚本分别将组合与基准起点归一化为 1；最大回撤按 `nav / 历史最高nav - 1` 计算。
- 若使用总回报指数，注明分红再投资口径。

```bash
python scripts/finance_charts.py drawdown nav.csv output/drawdown \
  --source "来源：组合回测，2026-06-30；费后总回报"
```

## football-field

字段：`method,low,high`

- low 与 high 为每股价值且必须大于 0，low 不得大于 high。
- `--current-price`、`--target-price` 可选；`--currency` 默认 `¥`。
- 不同方法须使用同一估值日期、股本口径和币种。

```bash
python scripts/finance_charts.py football-field valuation.csv output/valuation \
  --current-price 46 --target-price 58 --currency "$" \
  --source "来源：估值模型，2026-06-30"
```

## 通用参数

- `--title`／`--subtitle`：覆盖默认标题。
- `--source`：必填，写来源、数据日期及必要口径。
- `--format png|svg|both`：默认 `both`；PNG 为 300 DPI。
