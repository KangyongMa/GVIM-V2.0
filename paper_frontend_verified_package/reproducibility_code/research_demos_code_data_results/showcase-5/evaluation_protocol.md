# 五个化学/材料 Demo 的严格评估流程

## 0. 评估原则

本展示不使用自定义评分，不使用主观人工打分，不把“是否跑完流程”包装成科研指标。

每个 Demo 必须满足：

1. 从 DeerFlow 前端发起；
2. 使用公开数据、官方 split、论文公开标签或专家标注作为金标准；
3. DeerFlow 只看到输入数据，不能看到隐藏测试标签；
4. 独立 evaluator 读取 DeerFlow 输出和隐藏 gold；
5. 最终报告只使用已有框架或公认指标。

运行状态可以记录在日志中，例如 thread_id、run_id、生成文件路径、耗时、错误原因。
这些是实验记录，不是评分指标。

## 1. Demo 1：Matbench 实验带隙预测

任务：`matbench_expt_gap`。

公开依据：

- Matbench v0.1；
- 数据集：实验带隙 `gap expt`；
- 官方 split 规则：`KFold(n_splits=5, shuffle=True, random_state=18012019)`；
- 回归任务官方主分数：mean-fold MAE。

前端输入：

- `matbench_expt_gap_5fold_manifest.json`；
- `matbench_expt_gap_fold0_train.csv` 到 `matbench_expt_gap_fold4_train.csv`；
- `matbench_expt_gap_fold0_test_unlabeled.csv` 到 `matbench_expt_gap_fold4_test_unlabeled.csv`。

隐藏金标准：

- `matbench_expt_gap_5fold_gold.csv`。

DeerFlow 输出：

- `predictions.csv`，字段必须包含 `fold,row_id,composition,predicted_gap_eV`；
- `metrics.json`；
- `model_report.md`；
- 可选 `parity_plot.png`。

独立 evaluator：

- `research-demos/evaluators/evaluate_matbench_expt_gap.py`。

最终指标：

- MAE；
- RMSE；
- R2。

其中 MAE 是 Matbench 回归任务主指标；RMSE 和 R2 是公认回归指标。

## 2. Demo 2：Matbench Discovery 材料稳定性筛选

公开依据：

- Matbench Discovery；
- 官方稳定性/能量标签；
- 官方排名和分类评价方式。

前端输入：

- 候选材料结构或特征表；
- 公开任务定义中允许的描述符或模型分数；
- 不包含隐藏稳定性标签。

隐藏金标准：

- Matbench Discovery 的 DFT 参考稳定性或能量标签。

最终指标：

- F1；
- precision；
- recall；
- MAE；
- RMSE；
- R2；
- DAF。

这些指标来自材料发现、分类、回归和排序评价惯例，不额外定义主观分数。

## 3. Demo 3：MoleculeNet 分子性质预测

公开依据：

- MoleculeNet；
- DeepChem 常用数据拆分；
- 官方分子性质标签。

前端输入：

- SMILES 表；
- 训练标签；
- 测试集 SMILES；
- split 信息。

隐藏金标准：

- MoleculeNet 官方任务标签。

最终指标：

分类任务：

- ROC-AUC；
- PR-AUC；
- F1；
- accuracy。

回归任务：

- RMSE；
- MAE；
- R2。

## 4. Demo 4：IR/Raman 光谱到结构参数预测

公开依据：

- `Paper/d5sc08794e.pdf`；
- 论文中使用二面角预测误差和相关性评价模型。

前端输入：

- IR/Raman 光谱矩阵；
- 训练标签；
- 测试光谱；
- split 信息。

隐藏金标准：

- 论文或公开数据中的 C-N=N-C 二面角。

最终指标：

- MAE；
- RMSE；
- R2；
- Pearson r。

## 5. Demo 5：MatSci-NLP / SOFC-Exp 文献抽取

公开依据：

- SOFC-Exp；
- MatSci-NLP；
- 专家标注实体、关系或 slot。

前端输入：

- 公开 benchmark 中的材料文献文本；
- 抽取 schema；
- 不包含隐藏标注。

隐藏金标准：

- SOFC-Exp 或 MatSci-NLP 专家标注。

最终指标：

- precision；
- recall；
- micro-F1；
- macro-F1；
- exact match。

## 6. 统一执行方式

每个 Demo 的执行链固定为：

```text
公开数据/官方 split
→ 生成前端输入包
→ DeerFlow 前端发起任务
→ DeerFlow 生成预测或抽取结果
→ 独立 evaluator 读取结果和隐藏 gold
→ 输出标准指标
```

不允许在最终结果表中加入以下内容作为评分：

- workflow success；
- artifact completeness；
- run success rate；
- 人工主观完整性评分；
- 自定义综合分；
- 自定义权重平均分。

可以在附录记录运行日志，但不进入科研指标表。

## 7. 第一个 Demo 当前状态

第一个 Demo 已准备为严格版：

- 数据：`research-demos/data/matbench_expt_gap/matbench_expt_gap.json.gz`；
- 前端输入包：`research-demos/showcase-5/runtime/matbench_materials_property_modeling/input`；
- 隐藏 gold：`research-demos/showcase-5/runtime/matbench_materials_property_modeling/gold/matbench_expt_gap_5fold_gold.csv`；
- 独立 evaluator：`research-demos/evaluators/evaluate_matbench_expt_gap.py`；
- 本地参考结果：`research-demos/results/matbench_materials_property_modeling/evaluation_metrics.json`。
