# Synthetic challenge set

`synthetic.jsonl` contains 210 entirely invented English examples: 15 each in 13
categories plus 15 context-dependent challenge cases. Source: `scripts/synthetic.py`.
Seed 42 controls ordering. Reproduce with `.venv/bin/python -m scripts.synthetic`.
There are no real private messages in this dataset. Labels are author judgments,
not independent human consensus. Some ambiguity is intentional and labels may be
contested. Category labels are supplied, but benchmark quality metrics evaluate
binary importance only.

This is a small, imbalanced, English-only engineering challenge set, not a
representative sample of Instagram. Scores do not establish real-world recall.
Do not tune a filter on the entire set then present results as held-out validation.
Use a separate locally labeled holdout set for credible product evaluation.

Private data belongs in `benchmarks/data/private/` (fully gitignored). Each JSONL
row uses the IncomingMessage schema plus `context` (list of strings), `label`
(`important`: boolean, `category`: enum), and `synthetic`: false. No model sees the
label. Every row has a unique external_id. Context is frozen identically for both
pipelines. Each row is independent; the benchmark does not derive context from
neighboring dataset rows.
