"""Real-catalogue integration and authored acceptance examples; no AI required."""
import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.datastructures import FormData

from app import ai_form, catalogue, main
from app.structured import read_form

DATA = json.loads((Path(__file__).parent.parent / 'app/static/test-projects.json').read_text(encoding='utf-8'))
AS_OF = date.fromisoformat(DATA['as_of'])


def form_data(values):
    return FormData([(k, item) for k, value in values.items()
                     for item in (value if isinstance(value, list) else [value])])


@pytest.mark.parametrize('case', DATA['cases'], ids=lambda c: c['id'])
def test_authored_scenarios(case):
    _, errors, project = read_form(form_data(case.get('manual_form', case['expected_form'])))
    if 'expected_errors' in case:
        assert set(errors) == set(case['expected_errors'])
        return
    assert not errors
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    expected = case['expected']
    for key in ('candidates', 'upcoming', 'archive', 'excluded'):
        if key not in expected:
            continue
        actual = {r['programme'].id for r in groups[key]}
        if expected[key]:
            assert set(expected[key]) <= actual
        else:
            assert not actual
    if 'first_candidate' in expected:
        assert groups['candidates'][0]['programme'].id == expected['first_candidate']
    for programme_id in expected.get('amount_unassessed', []):
        row = next(r for r in groups['candidates'] if r['programme'].id == programme_id)
        assert 'not assessed' in row['amount_note']
    assert sum(map(len, groups.values())) == 10


def test_dates_and_stale_snapshot():
    p = next(p for p in catalogue.load_catalogue() if p.id == 'innowwide')
    assert catalogue.availability(p, AS_OF)[0] == 'window'
    upcoming = p.model_copy(update={'opens_on': AS_OF + timedelta(days=1)})
    assert catalogue.availability(upcoming, AS_OF)[0] == 'upcoming'
    assert catalogue.availability(p, p.opens_on)[0] == 'unknown'
    at_open = p.model_copy(update={'reviewed_on': p.opens_on})
    assert catalogue.availability(at_open, p.opens_on)[0] == 'window'
    assert catalogue.availability(p, AS_OF + timedelta(days=31))[0] == 'unknown'
    refreshed = p.model_copy(update={'reviewed_on': p.closes_on})
    assert catalogue.availability(refreshed, p.closes_on)[0] == 'window'
    assert catalogue.availability(refreshed, p.closes_on + timedelta(days=1))[0] == 'closed'
    cancelled = p.model_copy(update={'cancelled': True})
    assert catalogue.availability(cancelled, AS_OF)[0] == 'cancelled'


def test_no_fictional_catalogue_or_brand_on_public_pages():
    with TestClient(main.app) as client:
        home = client.get('/')
        page = client.get('/catalogue')
        assert page.status_code == home.status_code == 200
        assert 'class="brand"' not in home.text
        assert 'Learning MVP' not in home.text
        assert 'European innovation' in home.text
        assert '10 real' in page.text
        assert 'example.com' not in page.text
        for p in catalogue.load_catalogue():
            assert p.source_url in page.text
            assert p.title in page.text
        assert len(client.get('/static/test-projects.json').json()['cases']) == 20


def test_pln_and_new_activity_evidence():
    text = 'We plan to prepare an application to Horizon Europe. We request PLN 30000 funding.'
    draft = ai_form.FormDraft(
        currency=ai_form.Suggestion(value='PLN', evidence='PLN'),
        activities=[ai_form.ActivitySuggestion(value='grant_preparation',
            evidence='prepare an application to Horizon Europe')])
    values, _, _, _ = ai_form.prepare_form(text, draft)
    assert values['currency'] == 'PLN'
    assert values['activities'] == ['grant_preparation']


def test_no_conversion_or_project_budget_substitution():
    values = DATA['cases'][0]['expected_form'] | {
        'activities': ['export_promotion'], 'currency': 'EUR',
        'requested_funding': '60000', 'project_budget': '9999999'}
    _, errors, project = read_form(form_data(values))
    assert not errors
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    assert any(r['programme'].id == 'innowwide' for r in groups['candidates'])
    project.requested_funding = Decimal('60000.01')
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    assert any(r['programme'].id == 'innowwide' for r in groups['excluded'])
    project.currency = 'PLN'
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    row = next(r for r in groups['candidates'] if r['programme'].id == 'innowwide')
    assert 'not assessed' in row['amount_note']


def test_bad_catalogue_fails_explicitly(tmp_path, monkeypatch):
    path = tmp_path / 'invalid.json'
    path.write_text('{"programmes": []}', encoding='utf-8')
    monkeypatch.setattr(catalogue, 'CATALOGUE_PATH', path)
    assert catalogue.load_catalogue() == []
    path.write_text('{broken', encoding='utf-8')
    with pytest.raises(ValueError):
        catalogue.load_catalogue()

def test_country_lists_are_programme_specific():
    entries = {p.id: p for p in catalogue.load_demo_catalogue()}
    assert 'Canada' in entries['eurostars'].countries
    assert 'Canada' not in entries['innowwide'].countries
    assert 'United Kingdom' in entries['eic-accelerator'].countries
    assert 'United Kingdom' not in entries['life-circular'].countries
    assert 'Norway' not in entries['life-circular'].countries
    assert 'Iceland' in entries['life-circular'].countries


def test_demo_date_and_catalogue_do_not_follow_live_updates(monkeypatch):
    monkeypatch.setattr(catalogue, 'current_date', lambda: date(2030, 1, 1))
    with TestClient(main.app) as client:
        monkeypatch.setattr(main, 'load_catalogue', lambda: [])
        normal = client.get('/catalogue').text
        demo = client.get('/catalogue?mode=demo').text
        assert '0 real funding' in normal
        assert '2030-01-01' in normal
        assert '10 real funding' in demo
        assert 'fixed date 2026-10-04' in demo
        assert '2030-01-01' not in demo
        case = DATA['cases'][3]
        page = client.post('/match?mode=demo', data=case['expected_form'])
        assert 'data-programme-id="innowwide"' in page.text
        assert 'Within published window' in page.text
        assert 'fixed demo snapshot' in page.text
        assert 'data-programme-id=' not in client.post('/match', data=case['expected_form']).text


@pytest.mark.parametrize('case', [c for c in DATA['cases'] if c.get('demo')], ids=lambda c: c['id'])
def test_demo_examples_are_editable_and_explicitly_not_ai(case, monkeypatch):
    def no_ai(*args):
        raise AssertionError('Sample forms must not call AI')
    monkeypatch.setattr(ai_form, 'extract_form', no_ai)
    with TestClient(main.app) as client:
        description = client.get('/?mode=demo&example=' + case['id'])
        assert case['description'] in description.text
        assert 'Review the sample form' not in description.text
        page = client.get('/?mode=demo&prefill=yes&example=' + case['id'])
        assert 'not AI-generated suggestions' in page.text
        assert 'name="review_required" value="yes"' in page.text
        assert 'action="/match?mode=demo#matching-output"' in page.text
        assert 'value="' + case['expected_form']['requested_funding'] + '"' in page.text
        payload = case['expected_form'] | {'review_required': 'yes'}
        assert client.post('/match?mode=demo', data=payload).status_code == 422
        payload['review_confirmed'] = 'yes'
        result = client.post('/match?mode=demo', data=payload)
        assert result.status_code == 200
        assert 'fixed date 2026-10-04' in result.text
        assert client.get('/?mode=demo&example=unknown').status_code == 404


def test_demo_mode_survives_preparation_errors_and_success(monkeypatch):
    monkeypatch.setattr(ai_form, 'extract_form', lambda text: ai_form.FormDraft())
    with TestClient(main.app) as client:
        for response in [
            client.post('/prepare-profile?mode=demo', data={'description': 'short'}),
            client.post('/prepare-profile?mode=demo', data={'description': 'Project details without enough facts.'}),
            client.post('/prepare-document?mode=demo'),
            client.post('/prepare-document?mode=demo', files={'project_document': ('demo.txt', b'Project details without enough facts.')}),
        ]:
            assert 'fixed date 2026-10-04' in response.text
            assert 'action="/match?mode=demo#matching-output"' in response.text
        assert 'fixed date' not in client.get('/?mode=unknown').text
