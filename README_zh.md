# Absolut 的 OpenModelica 版本

库入口：[Absolut/package.mo](Absolut/package.mo)。本版本包含 v1.0.0 迁移修复、
heatport 初始化与守恒修复，以及两个蒸发器制冷剂侧串联测试。
远端已有修改与本地迁移代码的合并说明见 [UPSTREAM_MERGE.md](reports/UPSTREAM_MERGE.md)。
原作者与资助声明保留在英文 README 和 LICENSE.md 中。

## 依赖与加载

- OpenModelica：本次验证使用 `v1.27.0-dev-390-g7f4d387df9 (64-bit)`。
- Modelica / ModelicaServices 4.0.0：完整组件测试的标准环境。
- Modelica 4.1.0：另外验证三个 heatport 变体和新增串联案例。
- Buildings 12.0.0：单独安装，不包含在本仓库中。

在 OMEdit 依次加载指定版本的 Modelica、Buildings 12.0.0 和 `Absolut/package.mo`。
更新库后请重新加载并重新编译。案例自带 `--preOptModules-=evalFunc` 翻译选项；
若界面未采用注解，请在 Simulation Setup → Translation Flags 中填写该选项。

## 运行 AHPse_Dyn_heatport

展开 `Absolut → FluidBased → Dynamic → Components → Validation → AHPse_Dyn_heatport`。
先用开始时间 0、结束时间 1000、DASSL、容差 `1e-7` 检查启动过程，
再把结束时间设为 86400 观察全天趋势。确认日志包含 `The simulation finished successfully`，
并确认结果终止时间达到设置值。

在 Plotting 视图的 Variables Browser 中勾选 `ahp.eva.T`、`ahp.abs.T`、
`ahp.gen.T`、`ahp.con.T`，以及各容器的 `Qb_flow`、`p`、`level` 和
吸收器/发生器的 `X_LiBr`。温度以 K 保存（减去 273.15 得到 ℃），
压力以 Pa 保存，热流以 W 保存；热流流入工质为正。

Homotopy/Newton 某次迭代失败后恢复，不等于整次仿真失败。当前复杂案例仍可能出现
非线性重试和别名初值警告；详细验证要求包括完整终止时间、有限数值以及守恒检查。

需要重现图片时，先运行 `tests/initialization.py` 生成与当前源码相符的结果及可执行程序，
再安装 matplotlib/numpy 并运行 `python plot_heatport.py --modelica 4.1.0`。

## 两个蒸发器制冷剂侧串联

打开 `Absolut → FluidBased → Dynamic → Components → Validation → EvaporatorsSeries_heatport`。
默认运行 0–1200 s，DASSL，容差 `1e-8`。

连接路径：第一级液体供给 → 蒸发器 1 → 蒸汽侧压降元件 → 蒸发器 2 → 蒸汽出口。
第二级液体入口封闭，使用初始液体存量继续蒸发；测试不会将蒸汽出口直接接到液体入口。

- 恒定工况：`useHeatStep=false, useFeedStep=false`。
- 热负荷阶跃（默认）：300 s 时 Q1 从 1000 W 增至 1400 W；600 s 时 Q2 从 800 W 增至 1100 W。
- 供液减半：`useHeatStep=false, useFeedStep=true`，600 s 时入口从 0.0004 降至 0.0002 kg/s。

建议绘制 `eva1.T`、`eva2.T`、`eva1.p`、`eva2.p`、`m_series`、`m_out`、
`eva1.level`、`eva2.level`、`eva1.Qb_flow`、`eva2.Qb_flow` 和 `r_*` 守恒残差。
结果说明与 CSV 见 [串联测试报告](reports/EVAPORATORS_SERIES.md)。

## 自动测试

从仓库根目录执行；按本机安装位置修改 `--omc` 和 `--buildings`：

```powershell
python verify.py check --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo"
python component_tests.py --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo" --jobs 2
python component_tests.py --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo" --modelica 4.1.0 --case EvaporatorsSeriesNominal --case EvaporatorsSeriesHeatStep --case EvaporatorsSeriesFeedStep --jobs 2 --report evaporators_series_msl_4_1_0
python verify.py regression --omc E:/OpenModelica/bin/omc.exe --buildings "../Buildings 12.0.0/package.mo"
```

完整组件清单是 45 个组件/基类、60 个工况。Python 脚本按 `tests/components.json`
中的预设阈值判定成败，不能仅凭 OMEdit 显示仿真完成代替这些检查。
筛选测试使用 `--case`；`--resume` 仅在源码、测试与编译器校验一致时复用结果。

要运行两个版本的完整初始化测试，把 Buildings 12.0.0 放在本仓库的相邻目录，
设置 `OPENMODELICAHOME` 后执行：

```powershell
$env:OPENMODELICAHOME = 'E:/OpenModelica'
python tests/initialization.py
python tests/closed_loop_guards.py
```

本次发布源码的实际结果见 [发布验证记录](reports/PUBLISH_VALIDATION.md)。
编译产物和完整运行数据生成于 `build/`，部分串联数据另存于 `reports/artifacts/`。
代码仓库保留汇总报告和必要证据，未包含本机编译器或 Buildings 依赖库。

## 验证范围

质量、组分和能量检查验证模型与数值计算的一致性，不代表已经完成实验验证，
也不表示与 Dymola 逐点等价。两个 LabValidation 示例依赖原版未公开的实验数据；
拿到数据后可通过 `verify.py --data-file` 指定原始文件。它们的模型检查与实际仿真分别记录。

原始 v1.0.0 与当前库的逐文件变化见 `MIGRATION.patch`，文件哈希见
`reports/source_manifest.json`。源码、测试参数和运行证据的校验信息保存在各 JSON 报告中。
