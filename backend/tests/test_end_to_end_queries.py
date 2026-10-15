import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

QUESTIONS = [
    ("What is ITC's value creation model?", "document"),
    ("Explain ITC's corporate governance structure.", "document"),
    ("What is ITC Next?", "document"),
    ("What are ITC's FMCG growth platforms?", "document"),
    ("What are ITC's sustainability priorities?", "document"),
    ("Explain ITC's approach to climate change.", "document"),
    ("Tell me about ITC's FMCG strategy.", "document"),
    ("According to the FMCG transformation presentation, how did ITC's categories and SKU scale change over time?", "document"),
    ("What is the current stock price and recent market capitalization of ITC Limited?", "web"),
    ("Who is Donald Trump?", "none"),  # Strict domain guardrail test
]

def main():
    print("============================================================")
    print("RUNNING ITC INSIGHT END-TO-END VALIDATION SUITE")
    print("============================================================\n")

    passed = 0
    total = len(QUESTIONS)

    for idx, (question, expected_source_type) in enumerate(QUESTIONS, 1):
        print(f"--- TEST {idx}/{total}: \"{question}\" ---")
        try:
            resp = client.post("/chat", json={"question": question})
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()

            answer = data.get("answer", "")
            citations = data.get("citations", [])
            source_type = data.get("source_type", "")
            visual_used = data.get("visual_context_used", False)

            assert len(answer) > 40, "Answer should be substantive"
            assert source_type == expected_source_type, f"Expected source_type '{expected_source_type}', got '{source_type}'"

            if expected_source_type == "none":
                assert len(citations) == 0, "Off-topic query must have zero citations"
                assert "dedicated exclusively to ITC Limited" in answer or "ITC" in answer, "Must decline off-topic query politely"

            print(f"Status: PASS")
            print(f"Source Type: {source_type.upper()}")
            print(f"Visual Context Used: {visual_used}")
            print(f"Citations Count: {len(citations)}")
            for c in citations[:2]:
                if c.get("source_type") == "document":
                    print(f"  [DOC] {c.get('title')} (Page {c.get('page_number')})")
                else:
                    url = c.get('url') or ''
                    print(f"  [WEB] {c.get('title')} ({url[:60]}...)")
            preview = answer[:260].encode('ascii', 'ignore').decode()
            print(f"Answer Preview:\n{preview}...\n")
            passed += 1

        except Exception as e:
            print(f"Status: FAIL - {e}\n")

    print(f"============================================================")
    print(f"VALIDATION SUMMARY: {passed}/{total} Passed")
    print(f"============================================================")
    if passed != total:
        sys.exit(1)

if __name__ == "__main__":
    main()
