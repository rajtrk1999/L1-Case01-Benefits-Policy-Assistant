"""Run the assistant against a sample benefits question."""
import json

from src.assistant import answer_question


def main():
    query = "I'm on the Bronze HDHP - how much does the company put into my HSA for family coverage?"
    result = answer_question(query, experiment_name="baseline")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
