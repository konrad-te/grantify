"""Real-catalogue integration and authored acceptance examples; no AI required."""
import json
from html import unescape
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
        assert 'European funding for startups and SMEs' not in home.text
        assert 'Describe your project' in home.text
        assert '10 programmes and call tracks' in page.text
        for html in (home.text, page.text):
            assert 'href="/static/test-projects.json"' not in html
            assert 'Sources reviewed on 4 October' not in html
        assert 'Current-date mode' not in home.text
        assert 'Pilot catalogue:' not in home.text
        assert '<details class="card-details"><summary>Eligibility' in page.text
        assert 'example.com' not in page.text
        for p in catalogue.load_catalogue():
            assert p.source_url in page.text
            assert p.title in page.text
        assert len(client.get('/static/test-projects.json').json()['cases']) == 21


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
        assert '0 programmes and call tracks' in normal
        assert '2030-01-01' in normal
        assert '10 programmes and call tracks' in demo
        assert 'fixed date 2026-10-04' in demo
        assert '2030-01-01' not in demo
        case = next(c for c in DATA['cases'] if c['id'] == 'market-study')
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
        assert case['description'] in unescape(description.text)
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


@pytest.mark.parametrize('demo', [False, True])
@pytest.mark.parametrize('case', [c for c in DATA['cases'] if c.get('demo')], ids=lambda c: c['id'])
def test_visible_examples_load_text_and_expected_result_only(case, demo, monkeypatch):
    def no_ai(*args):
        raise AssertionError('Choosing an example must not invoke AI')
    monkeypatch.setattr(ai_form, 'extract_form', no_ai)
    prefix = '/?mode=demo&' if demo else '/?'
    with TestClient(main.app) as client:
        home = client.get(prefix).text
        assert 'Try a fictional example' in home
        assert home.count('class="example-option"') == 5
        assert 'id="example-expectation"' not in home
        page = client.get(prefix + 'example=' + case['id']).text
        assert case['description'] in unescape(page)
        assert case['explanation'] in unescape(page)
        assert 'Expected result' in page
        assert 'Reference: 2026-10-04 demo snapshot' in page
        assert 'aria-current="true"' in page
        assert 'value="' + case['expected_form']['requested_funding'] + '"' not in page
        assert 'Your funding shortlist' not in page
        assert 'Prepare my form' in page
        assert ('Demo · fixed date' in page) == demo


def test_expected_outcome_is_retained_only_for_unchanged_example(monkeypatch):
    monkeypatch.setattr(ai_form, 'extract_form', lambda text: ai_form.FormDraft())
    with TestClient(main.app) as client:
        description = DATA['cases'][0]['description']
        response = client.post('/prepare-profile', data={'description': description})
        assert 'id="example-expectation"' in response.text
        edited = client.post('/prepare-profile', data={'description': description + ' Changed project.'})
        assert 'id="example-expectation"' not in edited.text
        assert client.get('/?example=unknown').status_code == 404
        assert 'Review the sample form' not in client.get('/?example=software&prefill=yes').text


def test_recycling_explains_closed_matches_and_expands_them():
    case = next(c for c in DATA['cases'] if c['id'] == 'recycling')
    with TestClient(main.app) as client:
        page = client.post('/match?mode=demo', data=case['expected_form']).text
        assert 'We found 2 relevant programmes' in page
        assert 'their recorded application rounds are closed.' in page
        assert 'Applications closed 22 September 2026.' in page
        assert 'id="archived-matches" open' in page
        assert 'does not mean your project cannot get funding' in page
        assert 'mode=demo&amp;example=market-study' in page
        assert 'id="no-match-message"' not in page


def test_open_demo_example_has_a_published_window():
    case = next(c for c in DATA['cases'] if c['id'] == 'market-study')
    with TestClient(main.app) as client:
        page = client.post('/match?mode=demo', data=case['expected_form']).text
        assert 'data-programme-id="innowwide"' in page
        assert 'Within published window' in page
        assert 'id="archived-match-message"' not in page
        assert 'id="no-match-message"' not in page


def test_shortlist_explains_known_overlap_without_showing_a_false_eligibility_score():
    case = next(c for c in DATA['cases'] if c['id'] == 'market-study')
    _, errors, project = read_form(form_data(case['expected_form']))
    assert not errors
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    row = next(r for r in groups['candidates'] if r['programme'].id == 'innowwide')
    assert row['score'] == 100
    assert row['score_label'] == 'Strong known fit'
    assert [(check['points'], check['maximum']) for check in row['score_breakdown']] == [
        (20, 20), (15, 15), (35, 35), (15, 15), (15, 15)]
    assert row['unconfirmed_count'] == len(row['questions']) == 5
    with TestClient(main.app) as client:
        page = client.post('/match?mode=demo', data=case['expected_form']).text
        assert 'Why it appeared' in page
        assert 'What still needs checking' in page
        assert 'Check the evidence' in page
        assert 'When was the company legally established?' in page
        assert 'I don’t have this evidence yet' in page
        assert '100<span>/100</span>' not in page


def test_followups_turn_evidence_and_unknowns_into_specific_next_steps(monkeypatch):
    case = next(c for c in DATA['cases'] if c['id'] == 'software')
    form = {
        **case['expected_form'],
        'programme_id': 'eic-accelerator',
        'evidence_tested': 'Tested for six months at one wind farm and identified eight known faults.',
        'evidence_advantage': 'Detected faults two weeks earlier than the monitoring system used by the farm.',
        'evidence_market': '',
        'unknown_market': 'yes',
        'evidence_delivery': '',
        'evidence_budget': '',
        'review_method': 'ai',
    }
    from app.llm import LLMError
    monkeypatch.setattr(main, 'review_project_ai', lambda *args: (_ for _ in ()).throw(
        LLMError('The AI review is unavailable.')))
    with TestClient(main.app) as client:
        response = client.post('/check-programme?mode=demo', data=form)
    assert response.status_code == 503
    assert 'The AI review is unavailable.' in response.text
    assert 'Tested for six months at one wind farm' in response.text
    assert 'Promising lead' not in response.text
    assert 'eligible for EIC Accelerator' not in response.text


def test_complete_evidence_produces_a_concrete_but_cautious_assessment(monkeypatch):
    case = next(c for c in DATA['cases'] if c['id'] == 'software')
    form = {
        **case['expected_form'],
        'programme_id': 'eic-accelerator',
        'evidence_tested': 'Tested for six months at one wind farm and identified eight known faults.',
        'evidence_advantage': 'Detected faults two weeks earlier than the monitoring system used by the farm.',
        'evidence_market': 'Two wind-farm operators signed pilot letters and one agreed to a paid trial.',
        'evidence_delivery': '', 'evidence_budget': '',
    }
    monkeypatch.setattr(main, 'review_project', lambda *args: {
        'heading': 'Build the evidence before preparing an application',
        'summary': 'A useful project can still be a poor fit for this programme.',
        'next_action': 'Collect independent field-test results.',
        'findings': [], 'tasks': ['Collect field-test results.'], 'remaining': [],
        'finance': 'Total cost: EUR 180000.', 'source': 'https://eic.ec.europa.eu/',
        'reviewed': '2026-10-08',
    })
    with TestClient(main.app) as client:
        response = client.post('/check-programme?mode=demo', data=form)
    assert response.status_code == 200
    assert 'Build the evidence before preparing an application' in response.text
    assert 'Collect independent field-test results.' in response.text
    assert 'Answer the next questions or update my details' in response.text
    assert 'eligible for EIC Accelerator' not in response.text


def test_followups_require_all_answers_and_only_a_shortlisted_programme():
    case = next(c for c in DATA['cases'] if c['id'] == 'software')
    form = {
        **case['expected_form'],
        'programme_id': 'eic-accelerator',
        'evidence_tested': 'Tested at one wind farm for six months.',
        'evidence_advantage': 'too short',
        'evidence_market': '',
    }
    with TestClient(main.app) as client:
        incomplete = client.post('/check-programme?mode=demo', data=form)
        invalid = client.post('/check-programme?mode=demo', data={
            **case['expected_form'], 'programme_id': 'innowwide'})
    assert incomplete.status_code == 422
    assert 'Use one answer per question' in incomplete.text
    assert invalid.status_code == 400


def test_unknown_amount_and_availability_do_not_receive_full_points():
    case = next(c for c in DATA['cases'] if c['id'] == 'software')
    _, errors, project = read_form(form_data(case['expected_form']))
    assert not errors
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    row = next(r for r in groups['candidates'] if r['programme'].id == 'eic-accelerator')
    assert row['score'] == 80
    checks = {check['label']: check for check in row['score_breakdown']}
    assert checks['Funding request']['points'] == 5
    assert checks['Call availability']['points'] == 5
    assert 'No comparable verified cap' in checks['Funding request']['detail']
    assert 'not verified' in checks['Call availability']['detail']


def test_partial_activity_coverage_reduces_score():
    values = next(c for c in DATA['cases'] if c['id'] == 'manufacturing')['expected_form']
    _, errors, project = read_form(form_data(values))
    assert not errors
    groups = catalogue.shortlist(project, catalogue.load_demo_catalogue(), AS_OF)
    challenge = next(r for r in groups['candidates'] if r['programme'].id == 'eic-pathfinder-challenges')
    network = next(r for r in groups['candidates'] if r['programme'].id == 'eureka-network')
    assert challenge['score'] == 63
    assert network['score'] == 63
    activity = next(check for check in challenge['score_breakdown'] if check['label'] == 'Selected activities')
    assert activity['points'] == 18
    assert activity['detail'].startswith('1 of 2')


def test_candidates_are_ranked_by_known_fit_score_before_title():
    case = next(c for c in DATA['cases'] if c['id'] == 'software')
    _, errors, project = read_form(form_data(case['expected_form']))
    assert not errors
    base = next(p for p in catalogue.load_demo_catalogue() if p.id == 'eic-accelerator')
    alphabetical_first = base.model_copy(update={'id': 'unknown', 'title': 'A programme'})
    higher_score = base.model_copy(update={
        'id': 'window', 'title': 'Z programme', 'opens_on': AS_OF,
        'closes_on': AS_OF + timedelta(days=10), 'reviewed_on': AS_OF})
    groups = catalogue.shortlist(project, [alphabetical_first, higher_score], AS_OF)
    assert [row['programme'].id for row in groups['candidates']] == ['window', 'unknown']
    assert [row['score'] for row in groups['candidates']] == [90, 80]
