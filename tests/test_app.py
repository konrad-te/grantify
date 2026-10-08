"""Exercise structured submissions and deterministic results without an AI service."""
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from datetime import date
from app import main, llm, ai_form
from app import catalogue


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(catalogue, 'current_date', lambda: date(2026, 10, 4))
    # Every request must work with both former AI operations unavailable.
    monkeypatch.setattr(llm, 'extract_profile', Mock(side_effect=AssertionError('AI extraction called')))
    monkeypatch.setattr(llm, 'score_grants', Mock(side_effect=AssertionError('AI scoring called')))
    monkeypatch.setattr(ai_form, 'extract_form', Mock(side_effect=AssertionError('Unexpected AI preparation')))
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def submission():
    return dict(country='Poland', company_size='SME', industry='manufacturing',
        activities=['energy_efficiency'], requested_funding='120000', project_budget='150000', currency='EUR')


def test_home_and_static_assets(client):
    page = client.get('/')
    assert page.status_code == 200
    assert 'Describe your project' in page.text
    assert 'Skip this and fill in the form myself' in page.text
    assert page.text.index('id="description-entry"') < page.text.index('id="funding-form"')
    for name in ['country', 'company_size', 'industry', 'activities', 'requested_funding',
                 'project_budget', 'currency', 'employees', 'outcomes']:
        assert f'name="{name}"' in page.text
    assert 'name="additional_details"' not in page.text
    assert 'highlighted-description' not in page.text
    assert client.get('/static/style.css').status_code == 200
    assert client.get('/static/app.js').status_code == 200


def test_catalogue_loading_is_repeatable(client):
    first = catalogue.load_catalogue()
    second = catalogue.load_catalogue()
    assert first == second
    assert len(first) == 10
    assert len({p.id for p in first}) == 10


def test_structured_search_preserves_input_and_explains_results(client, submission):
    page = client.post('/match', data=submission)
    assert page.status_code == 200
    assert 'Your funding shortlist' in page.text
    assert 'data-programme-id="life-climate"' in page.text
    assert 'data-programme-id="life-clean-energy"' in page.text
    assert 'Published call closed' in page.text
    assert 'Why it appeared' in page.text
    assert 'within the award range' not in page.text
    assert 'Mock source' not in page.text
    assert 'value="120000"' in page.text
    assert 'name="activities" value="energy_efficiency" checked' in page.text


@pytest.mark.parametrize('field', ['country', 'company_size', 'industry', 'activities', 'requested_funding', 'project_budget', 'currency'])
def test_required_fields_checked_on_server(client, submission, field):
    submission.pop(field)
    page = client.post('/match', data=submission)
    assert page.status_code == 422
    assert f'id="error-{field}"' in page.text
    assert 'opportunities pass the basic checks' not in page.text


@pytest.mark.parametrize('key,value', [
    ('requested_funding', '0'), ('requested_funding', '-1'), ('requested_funding', 'NaN'),
    ('requested_funding', 'Infinity'), ('requested_funding', '1e5'), ('requested_funding', '120,000'),
    ('requested_funding', '10.001'), ('requested_funding', '160000'), ('project_budget', 'nan'),
    ('employees', '-1'), ('employees', '3.5'), ('activities', ['invented']),
    ('outcomes', ['invented']), ('country', 'invented'), ('company_size', 'tiny'), ('currency', 'GBP'),
    ('industry', 'other'), ('activities', ['other']), ('country', 'other'),
])
def test_invalid_inputs_get_field_errors(client, submission, key, value):
    submission[key] = value
    page = client.post('/match', data=submission)
    assert page.status_code == 422
    assert 'Check these fields' in page.text
    assert 'opportunities pass the basic checks' not in page.text


def test_legacy_free_text_does_not_trigger_extraction(client):
    page = client.post('/match', data={'description': 'Polish manufacturing SME with EUR 120000 funding.'})
    assert page.status_code == 422
    assert 'error-country' in page.text


def test_outcomes_employees_cannot_change_matches(client, submission):
    original = client.post('/match', data=submission).text.split('id="matching-output"')[1]
    submission.update(employees='0', outcomes=['new_products'])
    modified = client.post('/match', data=submission).text.split('id="matching-output"')[1]
    assert original == modified


def test_other_and_multiple_activities_need_assessment(client, submission):
    submission.update(industry='other', industry_other='Bakery',
                      activities=['energy_efficiency', 'other'], activities_other='New shop interior')
    page = client.post('/match', data=submission)
    assert page.status_code == 200
    assert 'Other selected activities are not covered' in page.text
    assert 'Sector exclusions' in page.text
    assert 'value="Bakery"' in page.text


def test_two_supported_activities_rank_a_programme_covering_both_first(client, submission):
    submission['activities'] = ['water_efficiency', 'circular_economy']
    output = client.post('/match', data=submission).text.split('id="matching-output"')[1]
    assert output.index('data-programme-id="life-circular"') < output.index('data-programme-id="life-climate"')
    assert 'What still needs checking' in output
    assert 'Funding amount not assessed' in output


def test_other_text_is_escaped(client, submission):
    submission.update(industry='other', industry_other='<script>alert(1)</script>')
    page = client.post('/match', data=submission)
    assert '<script>alert(1)</script>' not in page.text
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page.text


def test_large_total_cost_does_not_exclude_smaller_funding_request(client, submission):
    submission['project_budget'] = '900000'
    assert 'data-programme-id="life-climate"' in client.post('/match', data=submission).text


def test_catalogue_failure_keeps_answers(client, submission, monkeypatch):
    monkeypatch.setattr(main, 'load_catalogue', Mock(side_effect=OSError('private detail')))
    page = client.post('/match', data=submission)
    assert page.status_code == 503
    assert 'value="120000"' in page.text
    assert 'Could not read the programme catalogue' in page.text
    assert 'private detail' not in page.text


def test_unsupported_country_has_explicit_reasons(client, submission):
    submission['country'] = 'Canada'
    page = client.post('/match', data=submission)
    assert page.status_code == 200
    assert 'Country not covered' in page.text
    assert 'catalogue coverage limit' in page.text
    assert 'data-programme-id=' not in page.text


def test_request_above_verified_cap_is_excluded(client, submission):
    submission.update(currency='EUR', requested_funding='60001', project_budget='100000',
                      activities=['export_promotion'])
    page = client.post('/match', data=submission)
    assert 'data-excluded-id="innowwide"' in page.text
    assert 'Request exceeds the published maximum of EUR 60,000' in page.text


def test_large_company_is_outside_pilot_not_globally_ineligible(client, submission):
    submission['company_size'] = 'large'
    page = client.post('/match', data=submission)
    assert 'Outside this pilot' in page.text
    assert 'data-programme-id=' not in page.text


def test_closed_call_is_shown_only_as_archive(client, submission, monkeypatch):
    programme = next(p for p in catalogue.load_catalogue() if p.id == 'life-clean-energy')
    monkeypatch.setattr(main, 'load_catalogue', lambda: [programme])
    page = client.post('/match', data=submission)
    assert 'Closed or cancelled calls with matching topics (1)' in page.text
    assert 'We found 1 relevant programme' in page.text
    assert 'id="archived-matches" open' in page.text


def test_empty_catalogue_has_no_candidates(client, submission, monkeypatch):
    monkeypatch.setattr(main, 'load_catalogue', lambda: [])
    page = client.post('/match', data=submission)
    assert page.status_code == 200
    assert 'No matching programmes in this catalogue' in page.text


def test_preparation_requires_review_and_matches_like_manual(client, submission, monkeypatch):
    draft = ai_form.FormDraft.model_validate({
        'country': {'value': 'Poland', 'evidence': 'Polish'},
        'company_size': {'value': 'SME', 'evidence': 'SME'},
        'industry': {'value': 'manufacturing', 'evidence': 'manufacturing'},
        'activities': [{'value': 'energy_efficiency', 'evidence': 'install energy-saving equipment'}],
        'requested_funding': {'value': '120000', 'evidence': 'EUR 120,000 funding'},
        'project_budget': {'value': '150000', 'evidence': 'total cost EUR 150,000'},
        'currency': {'value': 'EUR', 'evidence': 'EUR'},
    })
    description = 'Polish manufacturing SME. We will install energy-saving equipment. We request EUR 120,000 funding; total cost EUR 150,000.'
    extract = Mock(return_value=draft)
    monkeypatch.setattr(ai_form, 'extract_form', extract)
    prepared = client.post('/prepare-profile', data={'description': description})
    assert prepared.status_code == 200
    assert 'Review your prepared form' in prepared.text
    assert 'All required fields have suggestions' in prepared.text
    assert '<q>Polish</q>' in prepared.text
    assert 'value="120000"' in prepared.text
    assert 'Your funding shortlist' not in prepared.text
    extract.assert_called_once_with(description)
    manual = client.post('/match', data=submission).text.split('id="matching-output"')[1]
    submission.update(review_required='yes', draft_description=description)
    assert client.post('/match', data=submission).status_code == 422
    submission['review_confirmed'] = 'yes'
    confirmed = client.post('/match', data=submission)
    assert confirmed.status_code == 200
    assert confirmed.text.split('id="matching-output"')[1] == manual
    extract.assert_called_once()
    submission['country'] = 'Canada'
    edited = client.post('/match', data=submission)
    assert 'Country not covered' in edited.text
    assert 'data-programme-id=' not in edited.text


def test_preparation_failure_preserves_escaped_description(client, monkeypatch):
    monkeypatch.setattr(ai_form, 'extract_form', Mock(side_effect=llm.LLMError('Model unavailable.')))
    response = client.post('/prepare-profile', data={'description': '<script>alert(1)</script> My project'})
    assert response.status_code == 503
    assert 'Model unavailable.' in response.text
    assert 'Unable to fill up the form because:<br>Model unavailable.' in response.text
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in response.text
    assert '<script>alert(1)</script>' not in response.text
    assert 'Your description is still here' not in response.text


@pytest.mark.parametrize('description', ['', 'short', 'x' * 5001])
def test_invalid_description_never_calls_ai(client, description):
    response = client.post('/prepare-profile', data={'description': description})
    assert response.status_code == 422


def test_empty_ai_draft_offers_manual_completion(client, monkeypatch):
    monkeypatch.setattr(ai_form, 'extract_form', Mock(return_value=ai_form.FormDraft()))
    response = client.post('/prepare-profile', data={'description': 'I have an idea but no company details yet.'})
    assert 'Still needed:' in response.text
    assert 'Not confidently extracted' in response.text
    assert 'Your funding shortlist' not in response.text


def test_document_upload_uses_review_flow(client, monkeypatch):
    description = 'We are a Polish manufacturing SME.'
    extract = Mock(return_value=ai_form.FormDraft(country=ai_form.Suggestion(value='Poland', evidence='Polish')))
    monkeypatch.setattr(ai_form, 'extract_form', extract)
    response = client.post('/prepare-document', files={'project_document': ('project.txt', description.encode(), 'text/plain')})
    assert response.status_code == 200
    extract.assert_called_once_with(description)
    assert 'Review your prepared form' in response.text
    assert 'name="review_required" value="yes"' in response.text
    assert description in response.text
    assert 'Your funding shortlist' not in response.text


def test_bad_upload_never_calls_ai(client):
    response = client.post('/prepare-document', files={'project_document': ('bad.pdf', b'invalid pdf', 'application/pdf')})
    assert response.status_code == 422
    assert 'does not contain a valid PDF' in response.text


def test_upload_missing_or_multiple_files(client):
    assert client.post('/prepare-document').status_code == 422
    response = client.post('/prepare-document', files=[('project_document', ('a.txt', b'project details')), ('project_document', ('b.txt', b'more details'))])
    assert response.status_code == 422
    assert 'one project document at a time' in response.text


def test_upload_model_failure_preserves_extracted_text(client, monkeypatch):
    monkeypatch.setattr(ai_form, 'extract_form', Mock(side_effect=llm.LLMError('Model unavailable.')))
    response = client.post('/prepare-document', files={'project_document': ('brief.txt', b'Polish manufacturing SME details')})
    assert response.status_code == 503
    assert 'Polish manufacturing SME details' in response.text
    assert 'Model unavailable.' in response.text


def test_downloadable_example_document(client):
    response = client.get('/static/example-project.txt')
    assert response.status_code == 200
    assert 'fictional project' in response.text
    assert 'EUR 120,000 funding' in response.text
