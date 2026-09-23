# 发布版本验证

日期：2026-09-23T13:50:27.679698+00:00。
编译器：`OpenModelica v1.27.0-dev-390-g7f4d387df9 (64-bit)`；Buildings 12.0.0。
库源码 SHA-256：`abb1525064244fc19fade165e465d4558bea960f72aaffd9a9cffb4f33e437a1`。

| 验证 | 通过 | 范围 |
|---|---:|---|
| 全库 checkModel | 107 | 包括新增串联案例及实验模型的结构检查 |
| 完整组件测试 | 60 | Modelica 4.0.0，45 个组件/基类 |
| 串联案例补充版本测试 | 3 | Modelica 4.1.0；4.0.0 已包含在完整组件测试中 |
| heatport 初始化与完整轨迹 | 6 | 三个变体 × Modelica 4.0.0/4.1.0，均到达 86400 s |
| 其他动态变体 | 2 | internalHEX、pump_extended，均到达 86400 s |
| 数值回归 | 4 | Gibbs 二阶导数、物性反算、LMTD 极限、闪蒸守恒 |
| 守恒保护负向测试 | 2 | 错误质量/组分配置被预期断言拒绝 |

检查机器报告中的源哈希与当前发布文件一致；仿真成功还要求到达预定时间、保存数值有限及相应物理判据通过。
完整组件报告中的 60 个工况均在本次发布源码上重新运行。

扩展 heatport 的一次 Modelica 4.0.0 并行编译因内存不足失败，随后在同一源码上单独重跑通过。
部分复杂 AHP 案例仍有状态选择、别名初值和恢复后的非线性重试警告；通过不表示没有警告。
实验数据未公开的两个 LabValidation 模型仅完成结构检查，未伪造数据运行；本次也没有将历史全部示例仿真误记为重新全量执行。

- [模型检查](check.json)
- [组件报告](components.md) / [JSON](components.json)
- [初始化与守恒](initialization.json)
- [数值回归](regression.json)
- [其他动态变体](dynamic_variants.json)
- [负向保护](closed_loop_guards.json)
- [两个蒸发器串联](EVAPORATORS_SERIES.md)

JSON 中 build/ 路径对应脚本生成的完整日志/结果。仓库另提供串联案例的关键变量 CSV 和原始日志；
编译器、Buildings 依赖、可执行程序及其余完整轨迹不作为源码提交。
这些结果验证模型与数值计算的一致性，不代替实验验证或 Dymola 逐点对比。
