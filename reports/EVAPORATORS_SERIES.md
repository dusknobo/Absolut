# 两个蒸发器制冷剂侧串联测试

模型：`Absolut.FluidBased.Dynamic.Components.Validation.EvaporatorsSeries_heatport`。

液体进入第一级；第一级蒸汽出口经绝热线性压降元件接到第二级蒸汽入口；第二级蒸汽出口经另一压降元件接到 1200 Pa 边界。
第二级没有持续补液，依靠初始液体存量蒸发。测试为 0–1200 s 的有限时长工况，不等同于通用两相流贯通蒸发管。

| 工况 | Modelica 4.0.0 | Modelica 4.1.0 | 激励 |
|---|---|---|---|
| Nominal | PASS | PASS | Q1=1000 W，Q2=800 W，供液 0.0004 kg/s |
| HeatStep | PASS | PASS | 300 s：Q1→1400 W；600 s：Q2→1100 W |
| FeedStep | PASS | PASS | 600 s：供液量减半至 0.0002 kg/s |

六组均采用 DASSL、容差 1e-8，完成完整 1200 s。检查显式初始化、全部保存值有限、逐级及整体质量/能量库存、串联接口流量抵消、液位有效范围和激励前后的响应。

| 残差 | 六组最大绝对值 | 预设阈值 |
|---|---:|---:|
| `r_mass1` | 2.2599977e-14 | 1e-05 |
| `r_mass2` | 3.7608805e-14 | 1e-05 |
| `r_massTotal` | 4.0190073e-14 | 1e-05 |
| `r_energy1` | 1.8699211e-09 | 2 |
| `r_energy2` | 2.579327e-09 | 2 |
| `r_energyTotal` | 2.1173037e-09 | 2 |
| `r_seriesMass` | 0 | 1e-10 |
| `r_seriesEnergy` | 0 | 1e-05 |

质量库存残差单位为 kg，能量库存残差为 J，接口流量残差为 kg/s、W。

## 查看结果

OMEdit 中使用案例默认实验设置，绘制 `eva1.T`、`eva2.T`、`eva1.p`、`eva2.p`、`m_series`、`m_out`、`eva1.level`、`eva2.level`、`eva1.Qb_flow`、`eva2.Qb_flow` 及 `r_*`。

以下 CSV 导出关键变量的原始保存值，未插值、未平滑或舍入。完整 CSV 可通过测试脚本生成，其校验值仍保留在机器报告中。
- 4.0.0 / EvaporatorsSeriesFeedStep：[CSV](artifacts/4.0.0/EvaporatorsSeriesFeedStep/selected_results.csv) · [日志](artifacts/4.0.0/EvaporatorsSeriesFeedStep/omc.log)
- 4.0.0 / EvaporatorsSeriesHeatStep：[CSV](artifacts/4.0.0/EvaporatorsSeriesHeatStep/selected_results.csv) · [日志](artifacts/4.0.0/EvaporatorsSeriesHeatStep/omc.log)
- 4.0.0 / EvaporatorsSeriesNominal：[CSV](artifacts/4.0.0/EvaporatorsSeriesNominal/selected_results.csv) · [日志](artifacts/4.0.0/EvaporatorsSeriesNominal/omc.log)
- 4.1.0 / EvaporatorsSeriesFeedStep：[CSV](artifacts/4.1.0/EvaporatorsSeriesFeedStep/selected_results.csv) · [日志](artifacts/4.1.0/EvaporatorsSeriesFeedStep/omc.log)
- 4.1.0 / EvaporatorsSeriesHeatStep：[CSV](artifacts/4.1.0/EvaporatorsSeriesHeatStep/selected_results.csv) · [日志](artifacts/4.1.0/EvaporatorsSeriesHeatStep/omc.log)
- 4.1.0 / EvaporatorsSeriesNominal：[CSV](artifacts/4.1.0/EvaporatorsSeriesNominal/selected_results.csv) · [日志](artifacts/4.1.0/EvaporatorsSeriesNominal/omc.log)

[4.0.0 报告](evaporators_series_msl_4_0_0.json) · [4.1.0 报告](evaporators_series_msl_4_1_0.json) · [导出校验](series_evidence.json)

源码 SHA-256：`abb1525064244fc19fade165e465d4558bea960f72aaffd9a9cffb4f33e437a1`。数值与模型一致性检查不代替实验验证。
