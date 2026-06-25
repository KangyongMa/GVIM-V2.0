# GVIM Chemistry and Materials Agent Paper Strategy

> Date: 2026-06-02
>
> Purpose: Evaluate the current GVIM chemistry/materials research agent system, identify publication-critical gaps, and define a paper strategy that can be supported with published public benchmarks instead of expert scoring.

## 1. Executive Summary

The current system is strongest as an **evidence-bounded, artifact-centric scientific agent workspace** for chemistry and materials research. It should not yet be framed as a fully autonomous scientist. The safer and more defensible paper claim is:

> GVIM is a chemistry and materials science agent harness that combines LLM-based task understanding with verified scientific tools, native scientific artifacts, and evidence-aware workflow control to support reproducible dry-lab research workflows.

The current project already has meaningful system contributions:

- A DeerFlow-based long-horizon agent runtime with skills, MCP tools, sandbox execution, memory, file uploads, and optional subagents.
- A GVIM science MCP extension backed by RDKit, pymatgen, Materials Project, PubChem, XRD utilities, Ketcher canvas preparation, and science artifact contracts.
- Domain skills for chemistry structure resolution, Ketcher drawing, RDKit molecular analysis, materials-core workflows, and Materials Project evidence.
- Frontend artifact rendering for Ketcher, 3Dmol, and materials results.
- Middleware that prevents final responses from omitting requested native science artifacts.

However, the system still lacks the evidence package expected by a strong journal submission:

- No systematic benchmark results yet.
- No quantitative comparison with LLM-only, generic agent, or tool-use baselines.
- No ablation proving that science artifacts, evidence rules, PubChem fallback, Ketcher command contracts, and completion middleware matter.
- No closed-loop automatic research benchmark showing iterative hypothesis generation, computation, evidence retrieval, ranking, and report generation.
- No formal hallucination and unsupported-claim evaluation.
- No reproducibility/evaluation harness that packages tasks, model settings, tool traces, artifacts, and scoring outputs.

The best immediate paper target is **Digital Discovery**. The second tier is **Journal of Cheminformatics** or **Journal of Chemical Information and Modeling**, depending on whether the paper emphasizes software/workflow reproducibility or chemical informatics evaluation.

## 2. Current System Positioning

### 2.1 What GVIM Currently Is

GVIM is not just a chat interface. In the current repository, it is a domain-extended scientific agent platform:

- `extensions_config.json` enables the `gvim-science` MCP server and science skills.
- `skills/public/chemistry-studio-ketcher/SKILL.md` defines natural-language molecule/reaction drawing through Ketcher commands.
- `skills/public/chemistry-structure-resolution/SKILL.md` defines evidence-aware name/identifier/SMILES resolution.
- `skills/public/rdkit-molecular-analysis/SKILL.md` defines RDKit-backed descriptors, similarity, standardization, fragments, reaction QC, and conformers.
- `skills/public/materials-core/SKILL.md` defines formula analysis, structure parsing, XRD simulation/matching, precursor planning, and materials descriptors.
- `skills/public/materials-evidence-project/SKILL.md` defines Materials Project and database-backed evidence workflows.
- `backend/packages/harness/gvim_v2/science_executor.py` registers whitelisted chemistry and materials tools and wraps results as science artifacts.
- `backend/packages/harness/deerflow/agents/middlewares/science_artifact_completion_middleware.py` enforces artifact completion before final answers.
- `frontend/src/components/workspace/messages/science-artifact.tsx` renders native Ketcher, 3D, and materials artifacts.

This gives the paper a real systems contribution: **LLM orchestration is constrained by scientific tools and artifact contracts**. That is a stronger claim than "we built a chemistry chatbot."

### 2.2 Recommended Paper Identity

Use this identity:

> An evidence-bounded, artifact-centric research agent framework for chemistry and materials workflows.

Avoid these claims for the first paper:

- "Fully autonomous scientist"
- "Autonomous discovery system"
- "End-to-end robotic laboratory"
- "New material discovery system"
- "Validated synthesis planner"

Use these claims instead:

- "Dry-lab autonomous workflow support"
- "Closed-loop computational research assistant"
- "Evidence-gated scientific tool orchestration"
- "Native artifact generation for chemical and materials workflows"
- "Reproducible agent traces for chemistry/materials tasks"

## 3. Main Shortcomings in the Current Project

### 3.1 The System Contribution Is Clearer Than the Scientific Evidence

The architecture is credible, but the evaluation is not yet journal-grade. Current tests mostly verify internal correctness:

- Ketcher command normalization and rejection of unsupported browser-coordinate actions.
- Reaction annotation extraction and preservation.
- XRD label selection for dense patterns.
- Science artifact extraction and completion middleware behavior.

These are important engineering tests, but they do not answer reviewer questions:

- Does GVIM solve chemistry/materials tasks more accurately than LLM-only baselines?
- Does tool orchestration reduce hallucination?
- Does the artifact-first interface improve scientific correctness or reproducibility?
- Does the system make better candidate-selection decisions in materials discovery tasks?
- Does it complete multi-step workflows reliably under realistic task instructions?

### 3.2 Current "Autonomy" Is Tool Routing, Not Research Closure

GVIM can route a user request to Ketcher, RDKit, pymatgen, Materials Project, XRD matching, or PubChem. That is useful, but full automatic research requires a loop:

1. Convert user goal into measurable objectives and constraints.
2. Generate hypotheses or candidate molecules/materials.
3. Choose computations or database queries.
4. Execute tools.
5. Evaluate results against objectives.
6. Critique evidence and uncertainty.
7. Decide whether to stop or run another iteration.
8. Produce a provenance-backed report.

The current system has many pieces of this loop, but the loop itself is not yet formalized as a benchmarked module.

### 3.3 Evidence Rules Exist but Are Not Quantitatively Validated

The skills explicitly tell the agent not to invent ADMET, spectra, synthesis feasibility, stability, or safety conclusions. This is a good product rule. For a paper, it needs a measurable result:

- Unsupported-claim rate before and after evidence rules.
- Refusal accuracy on impossible or under-specified scientific requests.
- Rate of correctly distinguishing database-computed values, deterministic calculations, and model inference.
- Rate of preserving source fields and structured evidence arrays.

### 3.4 Artifact Quality Is a Major Innovation but Needs Metrics

The Ketcher/3D/materials artifact layer is one of the most distinctive parts of the system. It is currently supported by code and tests, but reviewers will expect metrics such as:

- Ketcher artifact generation success rate.
- Correct structure loaded rate.
- Reaction command validity rate.
- 3D conformer generation success rate.
- Materials artifact completeness rate.
- Artifact-field preservation rate from tool result to frontend rendering.

Without these metrics, artifact-first design risks being seen as UI polish rather than a scientific contribution.

### 3.5 Public Benchmark Integration Is Missing

Because expert scoring is unavailable, the paper must rely on published public benchmarks. The current repository does not yet include:

- A benchmark runner for chemistry/materials QA.
- A benchmark runner for molecular/property/material discovery tasks.
- A trace schema for tool calls and science artifacts.
- A scoring layer that produces paper-ready CSV/JSON tables.
- Reproducible prompts and model configurations.

This is the most important engineering gap to close before writing the paper.

### 3.6 Materials Discovery Claims Need Stronger Grounding

The system can query Materials Project and analyze structures, but "materials discovery" requires a benchmark such as Matbench Discovery or a curated retrospective discovery task. Otherwise the paper can only claim "materials data analysis support."

To support "automatic dry-lab research", the system must show it can:

- Generate or retrieve candidate materials.
- Filter candidates with stability/property criteria.
- Rank candidates under a fixed compute/tool budget.
- Produce evidence-backed explanations.
- Beat simple baselines such as random selection, formula heuristics, LLM-only ranking, or generic agent routing.

### 3.7 Reproducibility Needs to Be Elevated

For Digital Discovery, Journal of Cheminformatics, or SoftwareX, reproducibility will be central. The current system should add:

- Frozen benchmark inputs.
- Model and tool version metadata.
- Environment metadata.
- Per-task trace logs.
- Tool outputs and artifact payloads.
- Deterministic scoring scripts.
- A single command to reproduce all paper tables.

## 4. Recommended Paper Thesis

### 4.1 One-Sentence Claim

> We present GVIM, an evidence-bounded scientific agent harness that turns natural-language chemistry and materials research requests into verified tool calls and native scientific artifacts, improving task completion, artifact generation, and unsupported-claim control across published chemistry and materials benchmarks.

### 4.2 Core Contributions

Use four contributions:

1. **Science-aware agent harness**
   - A long-horizon agent runtime extended with domain skills, MCP tools, sandbox execution, and context management for chemistry and materials workflows.

2. **Evidence-bounded tool orchestration**
   - LLMs select and compose whitelisted scientific tools, while RDKit, pymatgen, Materials Project, PubChem, and XRD utilities perform the scientific computation.

3. **Native scientific artifact contract**
   - Tool results preserve structured payloads for Ketcher, 3Dmol, and materials artifacts instead of collapsing scientific outputs into prose.

4. **Benchmark-based evaluation without expert scoring**
   - A reproducible evaluation suite built from published chemistry/materials/agent benchmarks and automatic scoring.

### 4.3 What Not to Claim

Do not claim:

- GVIM discovers new materials.
- GVIM validates wet-lab synthesis.
- GVIM replaces expert chemists.
- GVIM is generally autonomous across all scientific domains.
- GVIM predicts properties beyond the evidence returned by tools.

Instead claim:

- GVIM enables reproducible dry-lab workflows.
- GVIM reduces unsupported scientific claims.
- GVIM improves multi-step task completion over generic LLM and generic agent baselines.
- GVIM produces inspectable artifacts that connect agent reasoning to scientific representations.

## 5. Recommended Public Benchmarks

The evaluation should use published and externally maintained benchmarks wherever possible. The following set avoids dependence on local expert scoring.

### 5.1 Core Benchmarks

| Benchmark | Domain | Why it fits GVIM | Scoring |
|---|---|---|---|
| ChemBench | Chemistry QA and reasoning | Tests chemical knowledge/reasoning; useful for LLM-only vs GVIM comparison | Accuracy, exact match, multiple-choice accuracy |
| MaScQA | Materials science QA | Tests materials science concepts with 650 questions | Accuracy by question type/subdomain |
| Matbench | Materials property prediction | Tests composition/structure-based materials prediction tasks | MAE, RMSE, ROC-AUC depending on task |
| Matbench Discovery | Materials stability/discovery | Best fit for "automatic materials screening" | Precision, recall, F1, discovery acceleration, stability ranking |
| MoleculeNet | Molecular ML/property prediction | Tests molecular property workflows and molecular data processing | ROC-AUC, PRC-AUC, RMSE/MAE |
| ScienceAgentBench | Scientific agent automation | Tests data-driven scientific discovery agents on paper-derived tasks | Task success, code/execution success, result accuracy |

### 5.2 Optional Benchmarks

| Benchmark | Use only if | Caveat |
|---|---|---|
| USPTO-50K / USPTO reaction datasets | You add reaction prediction/retrosynthesis baselines | Current GVIM reaction support is QC-oriented, not a full retrosynthesis model |
| GuacaMol / MOSES | You add molecular generation or optimization | Current GVIM does not yet include a dedicated molecule generation model |
| MaCBench / MACBENCH | You want multimodal chemistry/materials evaluation | Treat as secondary unless final publication status and license are confirmed |
| QCBench or SciBench chemistry subsets | You want quantitative chemistry calculation tasks | Useful for reasoning, less directly tied to current artifact workflows |

### 5.3 Recommended Minimal Benchmark Suite

For the first paper, do not over-expand. Use:

1. ChemBench for chemistry reasoning.
2. MaScQA for materials reasoning.
3. Matbench Discovery for automatic materials screening.
4. A small MoleculeNet subset for molecular property workflows.
5. ScienceAgentBench subset for agentic scientific workflow automation.

This suite is broad enough to support a systems paper, but not so broad that evaluation becomes unmanageable.

## 6. Benchmark-to-System Mapping

### 6.1 ChemBench

Purpose:

- Show whether GVIM improves chemical task reliability when tools are available.

GVIM components tested:

- Chemistry structure resolution.
- RDKit descriptor tools.
- Reaction QC.
- Evidence rules.
- Tool selection.

Baselines:

- LLM-only.
- LLM with generic Python tool.
- Vanilla DeerFlow without GVIM science skills.
- GVIM without evidence rules.
- Full GVIM.

Metrics:

- Overall accuracy.
- Accuracy by chemistry topic.
- Tool-use accuracy.
- Unsupported-claim rate.
- Refusal quality for under-specified questions.

### 6.2 MaScQA

Purpose:

- Evaluate materials science knowledge and reasoning without needing local experts.

GVIM components tested:

- materials-core skill.
- materials-evidence-project skill.
- Materials Project search/profile/deep profile.
- Formula analysis.
- Unit conversion.
- Structure/property evidence handling.

Metrics:

- Accuracy by question type: MCQ, numeric, matching, multi-answer.
- Accuracy by subdomain: thermodynamics, characterization, phase transitions, mechanical behavior, electrical properties, etc.
- Evidence-grounding rate.
- Tool-use rate on questions requiring computation or database evidence.

### 6.3 Matbench

Purpose:

- Evaluate whether GVIM can organize reproducible materials-property workflows.

GVIM components tested:

- composition_features.
- structure_analysis.
- model/data workflow orchestration.
- report generation.

Recommended approach:

- Do not claim GVIM is a new state-of-the-art materials ML model unless you add real model training.
- Instead evaluate whether GVIM can automatically set up and execute a standard baseline workflow from the benchmark inputs.

Metrics:

- Pipeline completion rate.
- Correct data split handling.
- Correct metric calculation.
- MAE/RMSE/ROC-AUC compared with simple baselines.
- Trace reproducibility.

### 6.4 Matbench Discovery

Purpose:

- This is the strongest benchmark for the "automatic dry-lab materials discovery" claim.

GVIM components tested:

- Candidate selection.
- Materials Project evidence retrieval.
- Composition/structure analysis.
- Iterative ranking.
- Evidence-backed reporting.

Evaluation design:

- Fixed budget: each system can inspect only N candidates or N tool calls.
- Input: candidate pool and target objective.
- Output: ranked candidate list and evidence report.
- Compare against random ranking, LLM-only ranking, formula heuristic ranking, and GVIM full workflow.

Metrics:

- Precision@k.
- Recall@k.
- F1.
- Discovery acceleration factor.
- Stable candidate hit rate.
- Evidence completeness.
- Cost per stable hit.

### 6.5 MoleculeNet

Purpose:

- Evaluate molecular workflow handling and property-prediction support.

GVIM components tested:

- SMILES validation.
- RDKit descriptors.
- Standardization.
- Fragment/scaffold handling.
- Similarity.

Recommended approach:

- Use small subsets first: BBBP, ESOL, FreeSolv, ClinTox, Tox21.
- If no model training is implemented, use MoleculeNet to evaluate data processing, descriptor generation, and baseline model orchestration rather than claiming property prediction novelty.

Metrics:

- Valid SMILES processing rate.
- Descriptor generation success rate.
- Baseline model metric reproduction.
- Pipeline completion rate.

### 6.6 ScienceAgentBench

Purpose:

- Evaluate GVIM as an agent, not just as a chemistry/materials tool wrapper.

GVIM components tested:

- Long-horizon planning.
- Code execution.
- File handling.
- Tool use.
- Scientific result generation.
- Trace reproducibility.

Recommended approach:

- Select tasks relevant to chemistry, materials, data analysis, and scientific Python.
- Compare generic agent vs GVIM science-enabled agent.

Metrics:

- Task completion.
- Code execution success.
- Correct final result.
- Number of recoverable failures.
- Cost and wall-clock time.

## 7. Baselines

Use baselines that reviewers will understand.

### 7.1 Required Baselines

1. **LLM-only**
   - Same base model, no tools.
   - Tests whether tools and orchestration matter.

2. **LLM + generic code execution**
   - Same base model with Python/sandbox but no GVIM skills or science tool routing.
   - Tests whether domain tools matter beyond generic coding.

3. **Vanilla DeerFlow**
   - Existing harness without `gvim-science` MCP and science skills.
   - Tests the value of science customization.

4. **GVIM without evidence rules**
   - Keep tools but remove or disable strict evidence instructions.
   - Tests hallucination control.

5. **GVIM without science artifact completion middleware**
   - Tests whether completion middleware prevents intermediate-only answers.

6. **Full GVIM**
   - Complete system.

### 7.2 Optional Baselines

- Human-written simple scripts for selected tasks.
- Published benchmark baseline models for Matbench/MoleculeNet.
- Random candidate selection for Matbench Discovery.
- Formula heuristic candidate selection for Matbench Discovery.
- LLM-only ranking for candidate screening.

## 8. Ablation Studies

Reviewers will ask which system pieces actually matter. Recommended ablations:

| Ablation | Remove/disable | Expected measurable effect |
|---|---|---|
| No science skills | Disable chemistry/materials skills | Lower tool selection accuracy and workflow completion |
| No PubChem fallback | Disable PubChem resolution path | Lower name-to-structure success, especially common names |
| No Ketcher contract | Replace structured commands with prose | Lower artifact render success |
| No artifact completion middleware | Disable completion middleware | More final answers that omit requested artifacts |
| No evidence rules | Remove "do not invent" instructions | Higher unsupported-claim rate |
| No Materials Project tools | Disable MP tools | Lower database-evidence completeness |
| No structured traces | Do not preserve tool/artifact payloads | Lower reproducibility and artifact extraction rate |

Minimal ablation set for the first paper:

1. Full GVIM.
2. No science artifact completion middleware.
3. No evidence rules.
4. No PubChem fallback.
5. No Ketcher command contract.
6. No Materials Project evidence tools.

## 9. Metrics

### 9.1 General Task Metrics

- Task success rate.
- Exact match or multiple-choice accuracy.
- Numeric tolerance accuracy.
- Average tool calls per task.
- Average wall-clock time.
- Average token cost.
- Failure recovery rate.
- Reproducibility across repeated runs.

### 9.2 Chemistry Metrics

- Canonical SMILES exact match.
- Valid SMILES rate.
- RDKit descriptor availability rate.
- Reaction SMILES parse success.
- Reaction element/charge balance correctness.
- Atom-map coverage where applicable.
- Tanimoto similarity for near-match structure outputs.

### 9.3 Materials Metrics

- Formula parse success.
- Structure parse success.
- Space group/lattice field extraction correctness.
- XRD peak position MAE.
- XRD top-k match accuracy.
- Materials Project ID retrieval accuracy.
- Formation energy / band gap evidence availability.
- Stability classification accuracy.
- Discovery precision@k, recall@k, F1, discovery acceleration factor.

### 9.4 Artifact Metrics

- Ketcher artifact generated rate.
- Ketcher command validity rate.
- Correct structure loaded rate.
- 3Dmol artifact generated rate.
- Materials artifact generated rate.
- Artifact payload preservation rate.
- Frontend extraction/rendering success rate.

### 9.5 Safety and Evidence Metrics

- Unsupported-claim rate.
- Overconfident wrong-answer rate.
- Correct refusal rate.
- Evidence-source citation completeness.
- Correct distinction between database values, deterministic calculations, and model inference.
- Hallucinated property/spectrum/synthesis claim count.

## 10. Evaluation Harness Needed

Add a paper evaluation layer under a new directory, for example:

```text
evals/gvim_science/
  README.md
  configs/
    models.yaml
    benchmark_subsets.yaml
  datasets/
    README.md
    chembench_loader.py
    mascqa_loader.py
    matbench_discovery_loader.py
    moleculenet_loader.py
    scienceagentbench_loader.py
  runners/
    run_llm_only.py
    run_vanilla_deerflow.py
    run_gvim.py
  scorers/
    qa.py
    chemistry.py
    materials.py
    artifacts.py
    evidence.py
  traces/
    schema.json
  outputs/
    .gitkeep
```

Each benchmark run should emit:

```json
{
  "task_id": "string",
  "benchmark": "chembench",
  "system": "gvim_full",
  "model": "deepseek-or-other",
  "input": {},
  "final_answer": "string",
  "tool_calls": [],
  "science_artifacts": [],
  "scores": {},
  "errors": [],
  "cost": {},
  "wall_time_seconds": 0,
  "timestamp": "ISO-8601"
}
```

This trace schema is important because the paper's central claim is not only final-answer accuracy. GVIM also claims structured tool use and artifact generation.

## 11. Proposed Experiments

### Experiment 1: Chemistry QA and Reasoning

Benchmark:

- ChemBench subset or full ChemBench if runtime allows.

Systems:

- LLM-only.
- LLM + generic code.
- Vanilla DeerFlow.
- Full GVIM.

Metrics:

- Accuracy.
- Tool-use accuracy.
- Unsupported-claim rate.
- Cost/time.

Expected paper figure:

- Bar chart by chemistry topic.
- Table of overall scores.
- Error taxonomy.

### Experiment 2: Materials QA and Evidence Retrieval

Benchmark:

- MaScQA.

Systems:

- LLM-only.
- Vanilla DeerFlow.
- GVIM without Materials Project evidence tools.
- Full GVIM.

Metrics:

- Accuracy by subdomain.
- Evidence completeness.
- Unsupported-claim rate.
- Numeric tolerance accuracy.

Expected paper figure:

- Heatmap of performance by MaScQA subdomain and question type.

### Experiment 3: Native Artifact Completion

Benchmark:

- Build a deterministic task set from published benchmark molecules/materials and common tasks:
  - name-to-Ketcher
  - reaction SMILES-to-Ketcher
  - SMILES-to-3D conformer
  - CIF-to-XRD artifact
  - formula-to-Materials Project profile

Ground truth:

- Structures and formulas are from benchmark datasets or public databases.
- Scoring is automatic: artifact present, command valid, RDKit parse success, expected canonical SMILES when applicable.

Systems:

- Full GVIM.
- GVIM without artifact completion middleware.
- GVIM without Ketcher command contract.

Metrics:

- Artifact generation rate.
- Correct structure loaded rate.
- Intermediate-only failure rate.
- Payload preservation rate.

Expected paper figure:

- Sankey or stacked bar showing requested artifact -> tool output -> extracted artifact -> rendered artifact.

### Experiment 4: Automatic Materials Screening

Benchmark:

- Matbench Discovery.

Task:

- Given a candidate pool and objective, rank materials likely to be stable under a fixed budget.

Systems:

- Random ranking.
- Formula heuristic.
- LLM-only ranking.
- Vanilla DeerFlow.
- Full GVIM.

Metrics:

- Precision@k.
- Recall@k.
- F1.
- Discovery acceleration factor.
- Cost per hit.
- Evidence completeness.

Expected paper figure:

- Precision/recall curves.
- Top-k stable hit rate.
- Cost vs discovery gain.

### Experiment 5: Molecular Workflow Reproducibility

Benchmark:

- MoleculeNet selected subsets.

Task:

- Standardize molecules, generate RDKit descriptors, and execute a baseline model or analysis pipeline.

Systems:

- LLM + generic code.
- Vanilla DeerFlow.
- Full GVIM.

Metrics:

- Valid molecule processing rate.
- Descriptor completion rate.
- Baseline metric reproduction.
- Trace reproducibility.

Expected paper figure:

- Pipeline completion table.

### Experiment 6: Agentic Scientific Workflow

Benchmark:

- ScienceAgentBench relevant subset.

Systems:

- Generic coding agent.
- Vanilla DeerFlow.
- Full GVIM.

Metrics:

- Task success.
- Correct result.
- Executable code success.
- Number of recovery attempts.
- Cost/time.

Expected paper figure:

- Task completion and result-correctness table.

## 12. Error Taxonomy

Classify failures into:

1. Intent routing error
   - Wrong tool selected or no tool selected.

2. Structure resolution error
   - Wrong molecule/material identity.

3. Tool execution error
   - Dependency missing, invalid input schema, API failure.

4. Artifact omission
   - Correct text answer but missing requested Ketcher/3D/materials artifact.

5. Artifact corruption
   - Payload produced but frontend cannot render it.

6. Evidence misuse
   - Tool returned evidence but final answer misrepresented it.

7. Unsupported claim
   - Answer states property, spectrum, ADMET, synthesis feasibility, or stability without tool/database support.

8. Numeric/computation error
   - Wrong unit conversion, formula calculation, XRD matching, metric calculation.

9. Non-reproducibility
   - Same setup produces materially different conclusion without stochastic explanation.

This taxonomy should appear in the Discussion or Error Analysis section.

## 13. Paper Structure

### Title Options

Preferred:

> GVIM: An Evidence-Bounded Scientific Agent Harness for Chemistry and Materials Workflows

Alternative:

> Artifact-Centric Tool Orchestration for Chemistry and Materials Research Agents

More autonomous but still safe:

> Toward Closed-Loop Dry-Lab Research Agents for Chemistry and Materials Science

Avoid:

> A Fully Autonomous Chemistry and Materials Scientist

### Abstract Skeleton

Use this structure:

1. Chemistry and materials research increasingly depends on heterogeneous tools, databases, and scientific representations.
2. LLM agents can coordinate such workflows, but unconstrained tool use risks unsupported claims and prose-only outputs that are difficult to verify.
3. We introduce GVIM, an evidence-bounded scientific agent harness that connects LLM planning with RDKit, pymatgen, PubChem, Materials Project, XRD tools, Ketcher, and native artifact rendering.
4. GVIM uses domain skills, whitelisted scientific tools, structured artifact contracts, and completion middleware to ensure requested scientific deliverables are produced as inspectable outputs.
5. We evaluate GVIM on published chemistry, materials, molecular, and agent benchmarks, comparing against LLM-only and generic-agent baselines.
6. Results show improvements in task completion, artifact generation, evidence grounding, and unsupported-claim control.
7. The system provides a reproducible foundation for dry-lab chemistry and materials research agents.

Do not put results in the abstract until numbers are available.

### 1. Introduction

Recommended flow:

1. Modern chemistry/materials work spans databases, molecule editors, cheminformatics libraries, crystal toolkits, XRD analysis, and scientific reports.
2. LLMs are promising interfaces, but plain LLMs lack reliable grounding and often collapse scientific work into unverifiable prose.
3. Existing chemistry agents and autonomous labs show tool use and automation potential, but many systems either focus on narrow chemistry workflows, robotic wet labs, or text-only reasoning.
4. The gap: a general research-agent harness that produces inspectable chemistry/materials artifacts while enforcing evidence boundaries.
5. Introduce GVIM.
6. List contributions.

### 2. Related Work

Organize by theme:

1. LLMs for chemistry and materials reasoning.
2. Tool-augmented chemistry agents.
3. Autonomous laboratories and closed-loop materials discovery.
4. Chemistry/materials benchmarks.
5. Scientific workflow and reproducibility systems.

Positioning sentence:

> Unlike systems that evaluate only final textual answers, GVIM treats scientific artifacts and tool provenance as first-class outputs.

### 3. System Design

Suggested subsections:

3.1 Overview

- DeerFlow/GVIM harness.
- Lead agent, skills, MCP tools, sandbox, frontend.

3.2 Science Skill Layer

- Chemistry structure resolution.
- Ketcher drawing.
- RDKit analysis.
- Materials-core.
- Materials-evidence-project.

3.3 Tool Execution Layer

- Whitelisted tools in `science_executor.py`.
- LLM selects tools; scientific packages compute values.

3.4 Artifact Contract

- Ketcher commands.
- 3Dmol payloads.
- Materials artifact payloads.

3.5 Evidence and Safety Boundary

- Do not invent spectroscopy, ADMET, stability, synthesis feasibility.
- Preserve source and method type.

3.6 Completion Middleware

- Detect requested Ketcher/3D/materials artifacts.
- Prevent final answer until matching artifact/tool result exists.

### 4. Evaluation

Subsections:

4.1 Research Questions

- RQ1: Does GVIM improve chemistry/materials task accuracy over LLM-only and generic-agent baselines?
- RQ2: Does GVIM improve requested science artifact completion?
- RQ3: Does evidence-bounded orchestration reduce unsupported scientific claims?
- RQ4: Can GVIM support automatic dry-lab materials screening under published benchmark settings?

4.2 Benchmarks

- ChemBench.
- MaScQA.
- Matbench / Matbench Discovery.
- MoleculeNet.
- ScienceAgentBench.

4.3 Baselines

- LLM-only.
- LLM + generic code.
- Vanilla DeerFlow.
- Ablated GVIM.
- Full GVIM.

4.4 Metrics

- Accuracy, task success, artifact success, unsupported-claim rate, discovery metrics, cost/time.

4.5 Implementation Details

- Model versions.
- Tool versions.
- Hardware.
- API settings.
- Temperature.
- Max iterations.
- Retry policy.

### 5. Results

Recommended tables:

Table 1: Benchmark overview.

Table 2: Overall benchmark performance.

Table 3: Ablation results.

Table 4: Artifact completion results.

Table 5: Matbench Discovery screening results.

Recommended figures:

Figure 1: GVIM architecture.

Figure 2: Science artifact flow.

Figure 3: Performance by benchmark category.

Figure 4: Unsupported-claim reduction.

Figure 5: Discovery performance under fixed budget.

### 6. Discussion

Discuss:

- Why domain tools matter.
- Why artifacts matter.
- Where LLM reasoning still fails.
- Cost and latency.
- Public benchmark limitations.
- Why expert evaluation is future work, not required for the first result.

### 7. Limitations

Be direct:

- No wet-lab robotic validation.
- No claim of new material synthesis.
- Performance depends on external tools/API availability.
- Published benchmarks may not fully represent real exploratory research.
- Some tasks require proprietary database keys such as Materials Project.
- Multimodal chemistry/materials evaluation remains incomplete unless optional datasets are added.

### 8. Conclusion

Close with:

- GVIM provides a reproducible, evidence-bounded foundation for chemistry/materials research agents.
- Public benchmark evaluation shows where the system improves reliability and where autonomy remains limited.
- Future work will add active learning, wet-lab interfaces, and human-in-the-loop validation.

## 14. Target Journals

### 14.1 First Choice: Digital Discovery

Why:

- Scope explicitly covers chemistry/materials at the intersection of machine learning, AI, automation, databases, screening, and advanced data workflows.
- GVIM's digital workflow and reproducibility positioning fits well.

Paper angle:

> A reproducible AI/automation workflow system for chemistry and materials research agents.

What Digital Discovery will expect:

- Clear chemistry/materials relevance.
- Reproducible data/workflows.
- Benchmark-based evidence.
- Not just a software demo.

### 14.2 Second Choice: Journal of Cheminformatics

Why:

- Strong fit if the paper emphasizes open software, chemical information systems, molecular graphics, cheminformatics tools, and reproducibility.

Paper angle:

> Open-source cheminformatics and materials informatics agent platform with structured artifacts and reproducible evaluation.

Needs:

- Clean open-source release.
- Installation instructions.
- Example workflows.
- Software availability statement.

### 14.3 Third Choice: Journal of Chemical Information and Modeling

Why:

- Strong fit if the paper emphasizes molecular informatics, RDKit workflows, Ketcher, molecular descriptors, reaction QC, and molecular/material design support.

Risk:

- JCIM may expect deeper chemical informatics novelty or stronger molecular modeling results than a broad workflow system.

### 14.4 SoftwareX or JOSS

Use if:

- Benchmark results are not strong enough for Digital Discovery/JCIM.
- The core contribution is software infrastructure rather than scientific performance.

## 15. Minimum Publishable Package

For a credible first submission:

1. Benchmark runner for at least 3 public benchmarks:
   - ChemBench.
   - MaScQA.
   - Matbench Discovery or ScienceAgentBench subset.

2. At least 4 systems compared:
   - LLM-only.
   - Vanilla DeerFlow.
   - GVIM ablated.
   - Full GVIM.

3. At least 4 ablations:
   - No evidence rules.
   - No artifact completion middleware.
   - No PubChem fallback.
   - No Ketcher command contract.

4. Artifact evaluation:
   - 100-200 deterministic artifact tasks.

5. Error analysis:
   - At least 50 manually inspected failures, but not used as subjective expert scoring.

6. Reproducibility package:
   - Scripts.
   - Frozen prompts.
   - Config files.
   - Scoring outputs.
   - Trace schema.

## 16. Suggested 8-Week Execution Plan

### Week 1: Evaluation Scope and Benchmark Subsets

- Choose final benchmarks.
- Freeze task subsets.
- Define scoring metrics.
- Define trace schema.

Deliverable:

- `evals/gvim_science/README.md`
- benchmark subset manifest.

### Week 2: Baseline Runner

- Implement LLM-only runner.
- Implement vanilla DeerFlow runner.
- Implement full GVIM runner.

Deliverable:

- One command can run 20 smoke tasks per benchmark.

### Week 3: Chemistry and Materials QA Evaluation

- Run ChemBench subset.
- Run MaScQA.
- Produce first accuracy tables.

Deliverable:

- Draft Table 2.

### Week 4: Artifact Evaluation

- Build deterministic artifact task set.
- Score Ketcher, 3D, and materials artifact completion.
- Run ablations.

Deliverable:

- Draft artifact metrics and figure.

### Week 5: Materials Screening

- Implement Matbench Discovery evaluation or a carefully selected subset.
- Run random, heuristic, LLM-only, and GVIM systems.

Deliverable:

- Discovery metrics table.

### Week 6: ScienceAgentBench or Molecular Workflow Evaluation

- Run relevant ScienceAgentBench subset or MoleculeNet workflow reproduction.

Deliverable:

- Agentic workflow table.

### Week 7: Paper Draft

- Write system section.
- Write evaluation section.
- Add benchmark tables and figures.

Deliverable:

- Full first manuscript draft.

### Week 8: Internal Review and Submission Prep

- Run final reproducibility commands.
- Fill limitations.
- Polish figures.
- Prepare data/code availability statement.

Deliverable:

- Submission-ready manuscript for Digital Discovery or Journal of Cheminformatics.

## 17. Claim-Evidence Matrix

| Paper claim | Evidence required | Current status |
|---|---|---|
| GVIM is science-aware | Code and skills show domain tools | Mostly ready |
| GVIM produces native artifacts | Frontend/artifact contracts and tests | Needs benchmark metrics |
| GVIM reduces unsupported claims | Evidence rules exist | Needs hallucination/evidence benchmark |
| GVIM improves chemistry task reliability | ChemBench/ChemLLMBench results | Not yet available |
| GVIM improves materials task reliability | MaScQA/Matbench results | Not yet available |
| GVIM supports dry-lab automatic discovery | Matbench Discovery results | Not yet available |
| GVIM is reproducible | Evaluation harness and traces | Needs implementation |

## 18. Recommended Wording for the Manuscript

Use:

- "evidence-bounded"
- "artifact-centric"
- "native scientific artifacts"
- "tool-grounded scientific computation"
- "dry-lab workflow automation"
- "human-verifiable provenance"
- "closed-loop computational screening" only after Matbench Discovery results exist

Avoid:

- "fully autonomous scientist"
- "discovers new materials" unless experimentally validated
- "expert-level" unless benchmarked against expert/human baselines
- "predicts ADMET/spectra/stability" unless tool-backed and benchmarked
- "safe" without defining safety scope

## 19. References and Source Notes

Key public sources to cite or discuss:

- ChemBench: Nature Chemistry 2025 paper introducing an automated chemistry LLM evaluation framework with more than 2,700 question-answer pairs.
- MaScQA: Digital Discovery 2024 materials science QA benchmark with 650 challenging materials questions.
- Matbench: npj Computational Materials 2020 benchmark with 13 supervised materials property tasks.
- Matbench Discovery: Nature Machine Intelligence 2025 framework for evaluating crystal stability predictions.
- MoleculeNet: Chemical Science 2018 benchmark for molecular machine learning.
- ScienceAgentBench: ICLR 2025 benchmark for data-driven scientific discovery agents.
- Digital Discovery scope: RSC journal for AI, automation, data workflows, screening, and accelerated discovery in chemistry/materials.
- Journal of Cheminformatics scope: cheminformatics, software, databases, molecular graphics, molecular modeling, QSAR, data mining.
- JCIM scope: chemical informatics, molecular modeling, AI/ML applied to chemical and biological data, computer-aided design, and chemical software methods.

## 20. Final Recommendation

The best first paper is not "GVIM as a fully automatic researcher." The best first paper is:

> GVIM as a reproducible, evidence-bounded scientific agent harness for chemistry and materials workflows, evaluated on published benchmarks and native artifact completion tasks.

This paper is realistic, defensible, and aligned with the current codebase. After this paper, a second paper can target:

> Closed-loop autonomous dry-lab materials discovery with GVIM.

That second paper should add a formal research-goal manager, candidate generator, active-learning loop, result critic, and Matbench Discovery-centered evaluation.
