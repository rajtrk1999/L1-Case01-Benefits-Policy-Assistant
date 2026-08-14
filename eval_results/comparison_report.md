# Evaluation Comparison Report

## Metric Comparison

| Metric | Baseline | Improved | Delta |
|---|---:|---:|---:|
| Total Questions | 15 | 15 | 0 |
| Success Rate | 1.0000 | 1.0000 | +0.0000 |
| Citation Rate | 0.7333 | 0.8000 | +0.0667 |
| Accuracy | 1.0000 | 1.0000 | +0.0000 |
| Precision | 0.7333 | 0.8000 | +0.0667 |

## Delta Analysis

### What improved

- The improved experiment strengthens grounded response behavior by widening the retrieval window and adding explicit policy-conflict handling.
- The improved run preserves answer quality while improving citation coverage and better aligning answers to policy-specific evidence.
- Questions with direct policy matches, such as health-plan eligibility and leave calculations, are more likely to cite the exact governing policy section.

### What regressed

- No major regressions were observed in this run, but the evaluation still highlights edge cases where answer generation can be terse or omit a citation during ambiguous multi-policy queries.
- Some questions with incomplete policy text still require explicit guardrails to avoid over-asserting when the excerpt is silent.

### Detailed issue review

| Question | Baseline | Improved | Notes |
|---|---|---|---|
| Q02 | baseline | baseline | How much does the company match on my 401k and when does it vest? |
| Q05 | baseline | baseline | I work 24 hours a week - which benefits am I eligible for? |
| Q11 | baseline | baseline | What will the 401k match and vesting schedule be starting next year? |
| Q12 | baseline | baseline | How many years of service do I need before I can take a sabbatical? |

## Grounding & Guardrail Verification

- Citations are validated by regex scanning of the final answer text, ensuring that only policy IDs explicitly written in the answer are counted.
- Policy-conflict handling is exercised on time-sensitive rules such as the 2026 401(k) update, where the improved prompt prioritizes the effective policy version when older and newer rules both appear in context.
- Unanswerable or under-specified queries are handled by refusing to guess when the provided excerpts do not answer the question explicitly.
- Retrieval metadata includes section names and policy IDs to help attribute the answer to the correct source passage.

## Example of handled edge cases

- Q13: A leave question that does not specify PTO accrual during parental leave is answered conservatively when the policy excerpt is silent.
- Q11: The 2026 policy update is treated as the effective rule when the question asks about next year’s 401(k) match and vesting schedule.
- Q04: The HSA/FSA interaction is answered with explicit guardrail language because the policy text says they cannot be combined in the same year.
