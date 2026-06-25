# 外部基准对齐与严格 Demo 选择

## 核心口径

Demo 的可信度来自公开数据、公开金标准、官方 split 和已有指标，而不是我们自己设计的评分。

正式结果表只报告：

- MAE；
- RMSE；
- R2；
- ROC-AUC；
- PR-AUC；
- accuracy；
- precision；
- recall；
- F1；
- top-k accuracy；
- Pearson r；
- DAF。

运行日志可以记录前端是否完成、产物是否生成、耗时和错误原因，但这些不进入科研评分表。

## 最终推荐 5 个 Demo

| Demo | 外部依据 | 金标准 | 指标 |
|---|---|---|---|
| Matbench 实验带隙预测 | Matbench v0.1 | 官方标签和官方 5-fold | MAE, RMSE, R2 |
| Matbench Discovery 稳定性筛选 | Matbench Discovery | DFT 稳定性/能量标签 | F1, precision, recall, MAE, RMSE, R2, DAF |
| MoleculeNet 分子性质预测 | MoleculeNet | 官方分子性质标签 | ROC-AUC, PR-AUC, F1, accuracy, RMSE, MAE |
| IR/Raman 光谱到结构参数 | `d5sc08794e.pdf` | 论文/公开数据中的二面角标签 | MAE, RMSE, R2, Pearson r |
| MatSci-NLP / SOFC-Exp 文献抽取 | MatSci-NLP, SOFC-Exp | 专家标注实体、关系或 slot | precision, recall, micro-F1, macro-F1, exact match |

## 第一个 Demo 的严格定义

第一个 Demo 使用 `matbench_expt_gap`，不再采用临时 fold 或自定义拆分。

数据来源：

- Matbench 静态数据：`https://ml.materialsproject.org/projects/matbench_expt_gap.json.gz`。

官方规则：

- `KFold(n_splits=5, shuffle=True, random_state=18012019)`。

隐藏 gold：

- 由上述官方 fold 规则生成 5 个测试 fold 的 `gap_expt` 标签；
- DeerFlow 前端运行时不上传隐藏 gold。

评价方式：

- DeerFlow 输出 `predictions.csv`；
- 独立 evaluator 合并 `predictions.csv` 和 hidden gold；
- 按 fold 分别计算 MAE、RMSE、R2；
- 报告 mean-fold MAE、RMSE、R2。

其中 mean-fold MAE 是 Matbench 回归任务主分数；RMSE 和 R2 是公认回归指标。

## 外部依据

### Matbench

Matbench 是材料性质预测 benchmark，提供清洗后的监督学习任务、官方任务定义和评分规则。它适合作为材料 ML Demo 的主依据。

### Matbench Discovery

Matbench Discovery 面向材料稳定性筛选和发现任务，提供公开标签、排行榜和材料发现相关指标。它比自建 XRD 鉴相更适合作为论文主表定量 Demo。

### MoleculeNet

MoleculeNet 是分子机器学习公开基准。分类任务通常使用 ROC-AUC、PR-AUC、F1、accuracy；回归任务使用 RMSE、MAE 等指标。

### ScienceAgentBench / ChemCrow / Coscientist / ChemToolBench

这些工作说明，化学/材料智能体的价值应体现在任务规划、工具调用和可执行结果上。评分只落到最终公开任务指标。

### MatSci-NLP / SOFC-Exp

这类材料文本挖掘 benchmark 提供专家标注，适合用 precision、recall、micro-F1、macro-F1 衡量文献抽取结果。

## 参考来源

- ScienceAgentBench: https://osu-nlp-group.github.io/ScienceAgentBench/
- ChemCrow: https://www.nature.com/articles/s42256-024-00832-8
- Coscientist: https://www.nature.com/articles/s41586-023-06792-0
- ChemToolAgent: https://osu-nlp-group.github.io/ChemToolAgent/
- CheMatAgent / ChemToolBench: https://arxiv.org/html/2506.07551v2
- Matbench: https://docs.materialsproject.org/services/ml-and-ai-applications/matbench
- Matbench Discovery: https://matbench-discovery.materialsproject.org/
- MoleculeNet: https://pubs.rsc.org/en/content/articlehtml/2018/sc/c7sc02664a
- SOFC-Exp: https://aclanthology.org/2020.acl-main.116/
- MatSci-NLP: https://aclanthology.org/2023.acl-long.201.pdf
