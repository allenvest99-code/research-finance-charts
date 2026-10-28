---
name: research-finance-charts
description: 生成专业、可审计的金融投研图表，覆盖 A股、港股、美股场景。用于用户要求制作或重绘 K线/OHLC、成交量与均线、营收利润与利润率、PE Band/估值带、净值与最大回撤、估值 Football Field 时；适合研报、财报点评、投委会材料、投研笔记和看盘材料。提供严格 CSV 数据校验、A股红涨绿跌与港美股绿涨红跌、中文排版、300 DPI PNG 和可编辑 SVG 输出。用户只给标的而未提供数据时，先通过可靠金融数据源取数并注明日期、口径和来源，不要把本 skill 当作行情数据库。
---

# Research Finance Charts

## 工作流

1. **锁定数据口径**：确认市场、币种、单位、日期范围、复权方式、实际值／预测值和数据来源。缺少这些口径且会改变图表含义时先询问；不要编数。
2. **准备 CSV**：按 [references/chart-schemas.md](references/chart-schemas.md) 的字段契约整理数据。模拟数据必须在来源中明确写“模拟数据”。
3. **选择图表**：

| 图表 | `chart_type` | 适用问题 |
|---|---|---|
| K线＋成交量＋均线 | `candlestick` | 价格趋势、量价配合、均线位置 |
| 营收＋净利润＋净利率 | `fundamentals` | 增长质量、历史与预测财务表现 |
| PE Band | `pe-band` | 当前价格相对不同 PE 倍数的位置 |
| 净值＋回撤 | `drawdown` | 收益路径、基准比较、最大回撤 |
| 估值 Football Field | `football-field` | 多估值方法交叉验证、现价与目标价对照 |

4. **渲染**：在 skill 根目录执行，输出基名不要带扩展名；默认同时生成 PNG 和 SVG。

```bash
python scripts/finance_charts.py candlestick input.csv output/cn-price \
  --market cn --title "价格、均线与成交量" \
  --subtitle "前复权日线｜2026-01-01 至 2026-06-30" \
  --source "来源：iFinD，2026-06-30；前复权"
```

```bash
python scripts/finance_charts.py football-field valuation.csv output/valuation \
  --current-price 46 --target-price 58 --currency "$" \
  --source "来源：估值模型，2026-06-30"
```

5. **验收**：检查脚本报错信息；逐张打开 PNG，核对标题、单位、图例、来源、极值标注、文字裁切和数据是否合理。不要仅凭文件存在就宣布完成。

## 市场与视觉规则

- `cn`：红涨绿跌，默认人民币符号；`hk`／`us`：绿涨红跌，分别为港元／美元符号。
- 采用结论式标题、解释性副标题、底部来源；预测期在 period 中用 `E` 明示。
- 使用暖白底、克制配色、轻网格，不使用 3D、阴影或装饰性渐变。
- PNG 固定 300 DPI；SVG 保留可编辑文字。详细规则见 [references/visual-style.md](references/visual-style.md)。

## 演示与测试

生成全部 5 类图表及 A股／港股／美股 3 套 K线样图：

```bash
python scripts/demo.py <output-dir>
```

运行校验与渲染测试：

```bash
python -m unittest discover -s scripts -p "test_*.py" -v
```

## 质量门槛

- 数据来源、日期、币种、单位和复权／EPS／净值口径完整。
- OHLC 关系、日期唯一性、正 EPS、正净值及估值区间通过脚本校验。
- 实际值与预测值可区分；A股与港美股涨跌颜色不混用。
- 每张最终 PNG 均经过视觉检查；模拟样图不得被表述为真实行情或投资结论。
