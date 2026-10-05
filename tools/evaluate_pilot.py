"""Run: python -m tools.evaluate_pilot [--live] [--limit 3].

--live calls configured Ollama and reports extraction differences without masking
errors. Without it, evaluate authored form inputs and deterministic shortlists.
"""
import argparse
import json
from datetime import date
from pathlib import Path

from starlette.datastructures import FormData

from app import ai_form, catalogue, llm
from app.structured import read_form


def evaluate(live=False, limit=None):
    data = json.loads((Path(__file__).resolve().parents[1] / 'app/static/test-projects.json').read_text(encoding='utf-8'))
    programmes = catalogue.load_demo_catalogue()
    reports = []
    for case in data['cases'][:limit]:
        differences = []
        values = case.get('manual_form', case['expected_form'])
        if live:
            try:
                draft = ai_form.extract_form(case['description'])
                values, _, missing, _ = ai_form.prepare_form(case['description'], draft)
                for key, expected in case['expected_form'].items():
                    actual = values.get(key)
                    if (sorted(actual or []) if isinstance(expected, list) else actual) != (sorted(expected) if isinstance(expected, list) else expected):
                        differences.append({'field': key, 'expected': expected, 'actual': actual})
                for key in case.get('expected_missing', []):
                    if key in values:
                        differences.append({'field': key, 'expected': 'missing', 'actual': values[key]})
                for key in set(values) - set(case['expected_form']):
                    differences.append({'field': key, 'expected': 'not provided', 'actual': values[key]})
            except llm.LLMError as exc:
                reports.append({'case': case['id'], 'passed': False, 'error': str(exc)})
                continue
        pairs = [(k, v) for k, value in values.items() for v in (value if isinstance(value, list) else [value])]
        _, errors, project = read_form(FormData(pairs))
        if set(errors) != set(case.get('expected_errors', [])):
            differences.append({'validation': list(errors), 'expected': case.get('expected_errors', [])})
        if project:
            groups = catalogue.shortlist(project, programmes, date.fromisoformat(data['as_of']))
            for group, expected in case.get('expected', {}).items():
                if group not in groups:
                    continue
                actual = [r['programme'].id for r in groups[group]]
                if (not expected and actual) or not set(expected) <= set(actual):
                    differences.append({'group': group, 'expected': expected, 'actual': actual})
            expected = case.get('expected', {})
            if 'first_candidate' in expected:
                actual = groups['candidates'][0]['programme'].id if groups['candidates'] else None
                if actual != expected['first_candidate']:
                    differences.append({'first_candidate': actual, 'expected': expected['first_candidate']})
            for programme_id in expected.get('amount_unassessed', []):
                rows = [r for r in groups['candidates'] if r['programme'].id == programme_id]
                if not rows or 'not assessed' not in rows[0]['amount_note']:
                    differences.append({'amount_should_be_unassessed': programme_id})
        reports.append({'case': case['id'], 'passed': not differences, 'differences': differences})
    return {'mode': 'live Ollama extraction + matching' if live else 'deterministic matching (no AI)',
            'as_of': data['as_of'], 'passed': sum(r['passed'] for r in reports),
            'total': len(reports), 'cases': reports}


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    report = evaluate(args.live, args.limit)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report['passed'] == report['total'] else 1)
