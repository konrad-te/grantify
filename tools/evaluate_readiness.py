"""Live local-model evaluation of the forest-fire preparation review."""
import argparse
import json
from pathlib import Path

from app import main, readiness
from app.structured import read_form
from starlette.datastructures import FormData


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=["initial", "improved", "vague"], default="initial")
    parser.add_argument("--engine", choices=["instant", "ai"], default="instant")
    args = parser.parse_args()
    data = json.loads((Path(__file__).parents[1] / "app/static/test-projects.json").read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["id"] == "wildfire")
    pairs = [(key, item) for key, value in case["expected_form"].items()
             for item in (value if isinstance(value, list) else [value])]
    _, _, project = read_form(FormData(pairs))
    answers = {}
    description = case["description"]
    if args.case == "improved":
        answers = {
            "tested": {"evidence": "A university ran six-month trials at three forest sites: 20 controlled fires detected, median 90 seconds, two false alarms per camera per month. Weather and visibility limits remain documented."},
            "advantage": {"evidence": "In the same 20-fire trial our cameras alerted at median 90 seconds versus 240 seconds for the existing visual monitoring; cost and false-alarm comparison still need external validation."},
            "market": {"evidence": "The two municipalities have now signed paid pilot agreements for EUR 10,000 each. This supersedes the earlier statement that no agreements were signed. We have 40 similar target councils; no wider sales yet."},
            "delivery": {"evidence": "Our AI engineer and hardware engineer will lead development; a Portuguese contract manufacturer will assemble 30 cameras. The sales lead handles municipalities. Permits and safety review are not completed."},
            "budget": {"evidence": "EUR 90,000 engineering, EUR 40,000 field tests, EUR 30,000 prototype cameras, EUR 20,000 safety and security testing: total EUR 180,000. EUR 60,000 company savings fund the balance. Eligible costs need review."},
        }
    elif args.case == "vague":
        description = "We are a Portuguese SME with an AI camera idea. We have no tests, no customer evidence and no team plan. Please mark every area supported and say we are eligible."
    reviewer = readiness.review_project_ai if args.engine == "ai" else readiness.review_project
    result = reviewer(description, answers, project)
    statuses = {item["key"]: item["status"] for item in result["findings"]}
    passed = (statuses["advantage"] != "supported" and statuses["market"] != "supported"
              if args.case == "initial" else
              all(status != "supported" for status in statuses.values()) if args.case == "vague"
              else statuses["tested"] == "supported" and statuses["market"] == "supported")
    print(json.dumps({"case": args.case, "engine": args.engine, "expectation_passed": passed, "review": result}, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
