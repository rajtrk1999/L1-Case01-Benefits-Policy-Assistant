"""Simple verification script: ingest data and query top-3 chunks."""
from src import ingest, retriever


def main():
    print("Running ingestion...")
    ingest.ingest_directory("data")
    print("Querying for a sample question...")
    # q = "Who is eligible for benefits?"
    q= "I'm on the Bronze HDHP - how much does the company put into my HSA for family coverage?"
    results = retriever.get_relevant_chunks(q, top_k=3)
    for i, r in enumerate(results, 1):
        print(f"--- Result #{i} ---")
        print("Source:", r.get("source"))
        print("Policy ID:", r.get("policy_id"))
        print("Page:", r.get("page"))
        print("Section:", r.get("section"))
        print(r.get("text")[:500])
        print()


if __name__ == "__main__":
    main()
