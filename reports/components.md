# 组件独立测试结果

生成时间：2026-09-23T13:35:04.465586+00:00。编译器：`OpenModelica v1.27.0-dev-390-g7f4d387df9 (64-bit)`。Modelica：`4.0.0`。

库源码 SHA-256：`abb1525064244fc19fade165e465d4558bea960f72aaffd9a9cffb4f33e437a1`。测试包 SHA-256：`e6b01682ed445d2715f59915eca1a89d1b9f46f5c4e35f3f97cf3debb1e0c764`。

本次执行 60 个工况，涉及 45 个组件/基类；工况通过 60、失败 0；组件通过 45、失败 0。

“通过”要求编译运行成功、覆盖完整仿真时间、所有保存值有限，且独立物理残差与范围检查全部通过。没有把未能编译的模型、恢复后仍不守恒的运行或缺少结果的运行算作通过。

测试范围为全部可复用叶组件及具体化后的换热基类；8 个整机组装模型、参考常数、函数和包单独列在 JSON 清单中。已有整机/物性案例报告不能替代此处的组件测试。

## 各组件与工况

| 组件 | 工况 | 结果 | 失败原因 |
|---|---|---|---|
| `Basic.Blocks.CarnotSingleEffectAHP` | `CarnotSingleEffectAHP` | pass |  |
| `Basic.Blocks.DDT_AHT` | `DDT_AHT` | pass |  |
| `Basic.Blocks.EER_CarnotSingleEffectAHP` | `EER_CarnotSingleEffectAHP` | pass |  |
| `Basic.Blocks.EER_DoubleEffectAHP` | `EER_DoubleEffectAHP` | pass |  |
| `Basic.Blocks.EER_HalfEffectAHP` | `EER_HalfEffectAHP` | pass |  |
| `Basic.Blocks.EER_SingleEffectAHP` | `EER_SingleEffectAHP` | pass |  |
| `Basic.Blocks.EER_TripleEffectAHP` | `EER_TripleEffectAHP` | pass |  |
| `Basic.Blocks.Tfiring` | `Tfiring` | pass |  |
| `Basic.Blocks.ZeroOrderSingleEffectAHP` | `ZeroOrderSingleEffectAHP` | pass |  |
| `Basic.Blocks.ZeroOrderSingleEffectAHP_ext` | `ZeroOrderSingleEffectAHP_ext` | pass |  |
| `FluidBased.Dynamic.Components.AbsorberDyn_heatport` | `AbsorberDyn_heatportClosed` | pass |  |
| `FluidBased.Dynamic.Components.AbsorberDyn_heatport` | `AbsorberDyn_heatportThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.AbsorberDyn_internalHEX` | `AbsorberDyn_internalHEXClosed` | pass |  |
| `FluidBased.Dynamic.Components.AbsorberDyn_internalHEX` | `AbsorberDyn_internalHEXThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.CondenserDyn_heatport` | `CondenserDyn_heatportClosed` | pass |  |
| `FluidBased.Dynamic.Components.CondenserDyn_heatport` | `CondenserDyn_heatportThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.CondenserDyn_internalHEX` | `CondenserDyn_internalHEXClosed` | pass |  |
| `FluidBased.Dynamic.Components.CondenserDyn_internalHEX` | `CondenserDyn_internalHEXThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_heatport` | `EvaporatorDyn_heatportClosed` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_heatport` | `EvaporatorDyn_heatportThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_heatport` | `EvaporatorsSeriesFeedStep` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_heatport` | `EvaporatorsSeriesHeatStep` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_heatport` | `EvaporatorsSeriesNominal` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_internalHEX` | `EvaporatorDyn_internalHEXClosed` | pass |  |
| `FluidBased.Dynamic.Components.EvaporatorDyn_internalHEX` | `EvaporatorDyn_internalHEXThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.GeneratorDyn_heatport` | `GeneratorDyn_heatportClosed` | pass |  |
| `FluidBased.Dynamic.Components.GeneratorDyn_heatport` | `GeneratorDyn_heatportThroughFlow` | pass |  |
| `FluidBased.Dynamic.Components.GeneratorDyn_internalHEX` | `GeneratorDyn_internalHEXClosed` | pass |  |
| `FluidBased.Dynamic.Components.GeneratorDyn_internalHEX` | `GeneratorDyn_internalHEXThroughFlow` | pass |  |
| `FluidBased.Static.BaseClasses.ChenMTD` | `Base_ChenMTD` | pass |  |
| `FluidBased.Static.BaseClasses.LMTD` | `Base_LMTD` | pass |  |
| `FluidBased.Static.BaseClasses.MTD` | `Base_MTD` | pass |  |
| `FluidBased.Static.BaseClasses.MTD` | `Base_MTDChen` | pass |  |
| `FluidBased.Static.BaseClasses.MTD` | `Base_MTDEvents` | pass |  |
| `FluidBased.Static.BaseClasses.MTD` | `Base_MTDHomotopy` | pass |  |
| `FluidBased.Static.Components.Compressor` | `Compressor` | pass |  |
| `FluidBased.Static.Components.Compressor` | `CompressorUnityRatio` | pass |  |
| `FluidBased.Static.Components.FlashingLiBr` | `FlashingLiBr` | pass |  |
| `FluidBased.Static.Components.FlashingWater` | `FlashingWater` | pass |  |
| `FluidBased.Static.Components.HEX.ConstantEffectiveness` | `HEX_ConstantEffectiveness` | pass |  |
| `FluidBased.Static.Components.HEX.PlateHeatExchangerEffectivenessNTU` | `HEX_PlateHeatExchangerEffectivenessNTU` | pass |  |
| `FluidBased.Static.Components.HEX.simpleHX` | `HEX_simpleHX` | pass |  |
| `FluidBased.Static.Components.Pump` | `Pump` | pass |  |
| `FluidBased.Static.Components.PumpW` | `PumpW` | pass |  |
| `FluidBased.Static.DoubleEffect.CondenserStatic_de_UAfix` | `DoubleEffect_CondenserStatic_de_UAfix` | pass |  |
| `FluidBased.Static.DoubleEffect.LowGeneratorStatic` | `DoubleEffect_LowGeneratorStatic` | pass |  |
| `FluidBased.Static.DoubleEffect.LowGeneratorStatic_serie` | `DoubleEffect_LowGeneratorStatic_serie` | pass |  |
| `FluidBased.Static.Resorption.AbsorberStatic_wHT_UAfix_Resorption_ext` | `Resorption_AbsorberStatic_wHT_UAfix_Resorption_ext` | pass |  |
| `FluidBased.Static.SingleEffect_UAfixed.AbsorberStatic_wHT_UAfix` | `SingleEffect_UAfixed_AbsorberStatic_wHT_UAfix` | pass |  |
| `FluidBased.Static.SingleEffect_UAfixed.CondenserStatic_wHT_UAfix` | `SingleEffect_UAfixed_CondenserStatic_wHT_UAfix` | pass |  |
| `FluidBased.Static.SingleEffect_UAfixed.EvaporatorStatic_wHT_UAfix` | `SingleEffect_UAfixed_EvaporatorStatic_wHT_UAfix` | pass |  |
| `FluidBased.Static.SingleEffect_UAfixed.GeneratorStatic_wHT_UAfix` | `SingleEffect_UAfixed_GeneratorStatic_wHT_UAfix` | pass |  |
| `FluidBased.Static.SingleEffect_intern.AbsorberStatic` | `SingleEffect_intern_AbsorberStatic` | pass |  |
| `FluidBased.Static.SingleEffect_intern.CondenserStatic` | `SingleEffect_intern_CondenserStatic` | pass |  |
| `FluidBased.Static.SingleEffect_intern.EvaporatorStatic` | `SingleEffect_intern_EvaporatorStatic` | pass |  |
| `FluidBased.Static.SingleEffect_intern.GeneratorStatic` | `SingleEffect_intern_GeneratorStatic` | pass |  |
| `FluidBased.Static.TypeII.AbsorberStatic_wHT_UAfix_TypeII` | `TypeII_AbsorberStatic_wHT_UAfix_TypeII` | pass |  |
| `FluidBased.Static.TypeII.AbsorberStatic_wHT_UAfix_TypeII_ext` | `TypeII_AbsorberStatic_wHT_UAfix_TypeII_ext` | pass |  |
| `FluidBased.Static.TypeII.EvaporatorStatic_wHT_UAfix_TypeII` | `TypeII_EvaporatorStatic_wHT_UAfix_TypeII` | pass |  |
| `FluidBased.Static.TypeII.GeneratorStatic_wHT_UAfix_TypeII` | `TypeII_GeneratorStatic_wHT_UAfix_TypeII` | pass |  |

## 如何复现

在 `OpenModelica` 目录执行：

```powershell
python component_tests.py --jobs 2
python component_tests.py --case FlashingLiBr
```

OMEdit 中依次加载 Modelica 4.0.0、Buildings 12.0.0、`Absolut/package.mo` 和 `tests/Components.mo`，在 `ComponentTests` 包内选择具体工况并仿真。测试夹具只输出残差，完整的通过/失败判定由 Python 脚本按 `tests/components.json` 中的预设阈值执行。

## 判据与局限

静态设备从连接器的质量流量、实际流向焓和组分计算残差；动态设备将边界通量积分，与实际库存变化比较。压缩机采用绝热焓升功率，泵同时检查液体功率、电功率效率及出口温度。换热器在恒定比热介质下对照解析换热量；基础模块使用解析参考点与热力学恒等式。具体阈值、最大残差、工况参数和警告保存在 JSON。

这些是数值与模型一致性测试，不能代替实验验证。覆盖预设正向工况及列出的边界变化，并非穷举全部介质、倒流、失效和参数组合；所有输出量有限也不代表未采样时间处没有问题。

组件内部仍须闭合其守恒关系；连接点的守恒方程只约束连接点，不能替代容器内部方程。参见 [Modelica Fluid 组件定义](https://doc.modelica.org/Modelica%204.0.0/Resources/helpDymola/Modelica_Fluid_UsersGuide_ComponentDefinition.html) 和 [Modelica 3.6 方程平衡规范](https://specification.modelica.org/maint/3.6/class-predefined-types-and-declarations.html#balanced-models)。
