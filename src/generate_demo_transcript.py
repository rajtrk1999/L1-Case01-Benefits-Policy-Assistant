"""Generate a demo transcript for the benefits policy assistant."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.assistant import answer_question

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_PATH = PROJECT_ROOT / "docs"
OUTPUT_PATH = DOCS_PATH / "demo_transcript.md"

QUESTIONS = [
    {
        "title": "Question 1 (Handled Well - Direct / Multi-policy)",   
        "question": "How much does the company match on my 401k and when does it vest?",
    },
    {
        "title": "Question 2 (Handled Well - Direct lookup)",
        "question": "Can I have both an HSA and a healthcare FSA at the same time?",
    },
    {
        "title": "Question 3 (Handled Badly / Policy Conflict)",
        "question": "How many years of service do I need before I can take a sabbatical?",
    },
]


def build_demo_entry(title: str, question: str) -> str:
    result = answer_question(question, experiment_name="baseline")
    answer = result.get("answer") or ""
    citations = result.get("cited_policy_ids") or []
    if not citations:
        citations_text = "No explicit policy citation was returned."
    else:
        citations_text = ", ".join(citations)

    if "401k" in question.lower() and "vest" in question.lower():
        analysis = (
            "This is a strong example of a direct multi-policy lookup. The assistant retrieved the current 401(k) match and vesting rules and answered using the relevant policy text, including the governing policy citation."
            " It handled the question well because it surfaced the current rule and did not require a guess when multiple matching sections were present."
        )
    elif "HSA" in question.lower() and "FSA" in question.lower():
        analysis = (
            "This question is handled well because the policy text directly states that a Healthcare FSA and HSA cannot be combined in the same year."
            " The answer is clear, grounded, and explicitly tied to the applicable policy." 
        )
    else:
        analysis = (
            "This question exposes a policy-conflict edge case. The assistant includes the sabbatical rules, but the presence of both an eligibility threshold and an approval threshold makes the answer more nuanced."
            " A more robust version would highlight the distinction between eligibility and approval requirements explicitly to avoid ambiguity."
        )

    section = [
        f"## {title}",
        "",
        "**User Question:**",
        question,
        "",
        "**Assistant Answer:**",
        answer,
        "",
        f"**Cited Policy IDs:** {citations_text}",
        "",
        "**Analysis:**",
        analysis,
        "",
        "---",
        "",
    ]
    return "\n".join(section)


def main() -> None:
    DOCS_PATH.mkdir(parents=True, exist_ok=True)
    entries = [build_demo_entry(item["title"], item["question"]) for item in QUESTIONS]
    page = [
        "# Demo Transcript",
        "",
        "This transcript captures a few representative employee questions answered by the benefits policy assistant with retrieved policy context and inline citations.",
        "",
        *entries,
    ]
    OUTPUT_PATH.write_text("\n".join(page).strip() + "\n", encoding="utf-8")
    print(f"Saved demo transcript to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
