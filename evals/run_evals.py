"""
Simple local evaluation runner for the Kopilkin multi-agent system.

Usage:
1. Start auth/transaction/agent services and Docker infra.
2. Make sure the user_id below has sample transactions, or replace it.
3. Run: python evals/run_evals.py
"""
import json
import time
from pathlib import Path

import requests

AGENT_URL = "http://127.0.0.1:8004/chat"
USER_ID = "9c22bfe5-4453-4a82-94d4-a7ede65b97ae"


def contains_all(text: str, words: list[str]) -> bool:
    low = text.lower()
    return all(word.lower() in low for word in words)


def main() -> None:
    cases = json.loads(Path(__file__).with_name("test_cases.json").read_text(encoding="utf-8"))
    results = []

    for case in cases:
        start = time.perf_counter()
        try:
            r = requests.post(
                AGENT_URL,
                json={"user_id": USER_ID, "message": case["message"]},
                timeout=360,
            )
            latency = round(time.perf_counter() - start, 2)
            ok_http = r.status_code == 200
            data = r.json() if ok_http else {"response": r.text}
            response_text = data.get("response", "")
            passed = ok_http and contains_all(response_text, case.get("must_reference", []))
        except Exception as e:
            latency = round(time.perf_counter() - start, 2)
            ok_http = False
            response_text = str(e)
            passed = False

        results.append({
            "id": case["id"],
            "passed": passed,
            "latency_seconds": latency,
            "expected_route": case.get("expected_route"),
            "expected_language": case.get("expected_language"),
            "response_preview": response_text[:500],
        })

    report = {
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "failed": sum(1 for r in results if not r["passed"]),
        "results": results,
    }

    out = Path(__file__).with_name("last_eval_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
