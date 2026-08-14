"""Baseline evaluation runner for the Benefits Policy Assistant.

Loads the curated question set from CSV/Markdown, runs each query through the
assistant, and writes a structured summary to eval_results/baseline_eval.json.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.assistant import answer_question

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "eval_results"
CSV_PATH = DATA_DIR / "sample_questions.csv"
MD_PATH = DATA_DIR / "sample_questions.md"


def _load_question_rows() -> List[Dict[str, str]]:
    """Load question rows from CSV or markdown and normalize them to id/query pairs."""
    if CSV_PATH.exists():
        with CSV_PATH.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            rows = []
            for row in reader:
                qid = (row.get("question_id") or row.get("id") or "").strip()
                query = (row.get("employee_question") or row.get("question") or "").strip()
                if qid and query:
                    rows.append({"question_id": qid, "query": query})
            if rows:
                return rows

    if MD_PATH.exists():
        rows: List[Dict[str, str]] = []
        for raw_line in MD_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^(Q\d+|\d+)[\s\-:|]+(.+)$", line)
            if match:
                qid, query = match.groups()
                rows.append({"question_id": qid.upper(), "query": query.strip()})
        if rows:
            return rows

    raise FileNotFoundError("No sample question file found at data/sample_questions.csv or data/sample_questions.md")


def _answer_is_present(answer: str) -> bool:
    text = (answer or "").strip()
    if not text:
        return False
    lowered = text.lower()
    if "could not verify" in lowered or "could not find supporting policy context" in lowered:
        return False
    return True


def _evaluate_response(question_id: str, query: str, result: Dict[str, Any]) -> Dict[str, Any]:
    answer = str(result.get("answer") or "").strip()
    cited_ids = result.get("cited_policy_ids") or []
    retrieved_chunks = result.get("retrieved_chunks") or []

    has_answer = _answer_is_present(answer)
    has_citation = bool(cited_ids)
    fallback_caught = any(
        marker in (answer or "").lower()
        for marker in ("could not verify", "could not find supporting policy context")
    )

    return {
        "question_id": question_id,
        "query": query,
        "answer": answer,
        "cited_policy_ids": cited_ids,
        "retrieved_chunk_count": len(retrieved_chunks),
        "retrieved_chunk_ids": [
            chunk.get("policy_id") for chunk in retrieved_chunks if chunk.get("policy_id")
        ],
        "evaluation": {
            "has_answer": has_answer,
            "has_citation": has_citation,
            "fallback_caught": fallback_caught,
        },
    }


def main() -> None:
    rows = _load_question_rows()
    if len(rows) != 15:
        raise ValueError(f"Expected 15 sample questions, found {len(rows)}")

    results: List[Dict[str, Any]] = []
    answered_count = 0
    citation_count = 0
    fallback_handled_count = 0

    for item in rows:
        question_id = item["question_id"]
        query = item["query"]
        result = answer_question(query, experiment_name="baseline")
        evaluation = _evaluate_response(question_id, query, result)

        results.append({
            **evaluation,
            "raw_response": result,
        })

        if evaluation["evaluation"]["has_answer"]:
            answered_count += 1
        if evaluation["evaluation"]["has_citation"]:
            citation_count += 1
        if evaluation["evaluation"]["fallback_caught"]:
            fallback_handled_count += 1

    summary = {
        "total_questions": len(rows),
        "answered_count": answered_count,
        "cited_count": citation_count,
        "fallback_handled_count": fallback_handled_count,
        "success_rate": round(answered_count / len(rows), 4) if rows else 0.0,
        "citation_rate": round(citation_count / len(rows), 4) if rows else 0.0,
        "fallback_caught_rate": round(fallback_handled_count / len(rows), 4) if rows else 0.0,
    }

    payload = {
        "summary": summary,
        "results": results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RESULTS_DIR / "baseline_eval.json"
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved evaluation report to {output_path}")


if __name__ == "__main__":
    main()
