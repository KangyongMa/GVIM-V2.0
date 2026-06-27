# Agent-Advantage Native Public Benchmarks

This directory now contains only published chemistry/materials benchmark tasks for GVIM/DeerFlow front-end evaluation. The former local custom workflow tasks, gold files, logs, and scoring rubric have been removed.

## Composition

| Suite | Count | Native scoring rule |
|---|---:|---|
| ChemBench-Mini | 236 | Official ChemBench package/parser/metrics only |
| MaScQA | 84 | Published answer-key accuracy for the MaScQA question types |
| ChemLLMBench | 40 | Task-specific metrics from the official ChemLLMBench definitions |

Total public queue: 360 tasks.

The separate 40-task small evaluation is in `../../workflow40-agent-evaluation/native-published-40.jsonl`. It is a stratified subset of these same published sources: 14 ChemBench-Mini, 13 MaScQA, and 13 ChemLLMBench tasks.

## Files

- `questions.jsonl`: 360-task published-benchmark submission queue. No local custom workflow tasks are included.
- `questions.csv`: spreadsheet-friendly view of the same queue.
- `answer_key.jsonl`: held-out answer-key references. Do not read during submission.
- `manifest.json`: source revisions, counts, selection policy, and logging requirements.
- `pilot_questions.jsonl`: 15-task pilot set, five from each public suite.
- `pilot_answer_key.jsonl`: held-out pilot answer-key references.
- `native_published_submit.mjs`: submits a queue through the real logged-in front end and records raw evidence.

## Scoring Policy

Report scores separately by published source before any descriptive aggregate:

1. ChemBench-Mini: official ChemBench parser and metrics only.
2. MaScQA: published answer-key accuracy.
3. ChemLLMBench: task-specific answer-key metrics following the official task definitions.

No local tool-trace rubric, no `FINAL_RESULT` completion marker requirement, and no custom weighted score are used.

## Submission

Run submission through the logged-in GVIM/DeerFlow front end. Do not bypass the Agent by calling backend APIs directly for the full-system condition.

```powershell
node benchmarks\agent-advantage-400\native_published_submit.mjs --questions workflow40-agent-evaluation\native-published-40.jsonl --limit 40
```

Use a fresh browser profile for the `kangyongmaAgent@gmail.com` account when comparing against previous failed local-custom runs.
