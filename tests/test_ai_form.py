"""Grounding and ambiguity checks for suggestions before human confirmation."""
from unittest.mock import Mock

import pytest

from app import ai_form


def suggestion(value, evidence):
    return {'value': value, 'evidence': evidence}


def prepare(text, **fields):
    return ai_form.prepare_form(text, ai_form.FormDraft.model_validate(fields))


def test_multiple_activities_and_unknown_activity_preserve_evidence():
    text = 'We will install energy-saving equipment, reuse waste, and install a shop sign.'
    values, evidence, missing, _ = prepare(text, activities=[
        suggestion('energy_efficiency', 'install energy-saving equipment'),
        suggestion('circular_economy', 'reuse waste'),
        suggestion('other', 'install a shop sign'),
    ])
    assert values['activities'] == ['energy_efficiency', 'circular_economy', 'other']
    assert values['activities_other'] == 'install a shop sign'
    assert len(evidence['activities']) == 3
    assert 'activities' not in missing


def test_unknown_industry_is_other_not_inferred_category():
    values, _, _, _ = prepare('We run a bakery.', industry=suggestion('other', 'bakery'))
    assert values['industry'] == 'other'
    assert values['industry_other'] == 'bakery'


@pytest.mark.parametrize('phrase', ['registered in', 'based in', 'headquartered in', 'incorporated in'])
def test_explicit_company_country_takes_priority_over_project_country(phrase):
    text = (f'We are a software SME {phrase} Ireland. We will conduct a market feasibility '
            'study in Canada. We request EUR 60,000 funding; total project cost is EUR 86,000.')
    values, evidence, missing, warnings = prepare(text,
        country=suggestion('Canada', 'Canada'))
    assert values['country'] == 'Ireland'
    assert evidence['country'] == [f'{phrase} Ireland']
    assert 'country' not in missing
    assert not warnings


def test_conflicting_company_countries_remain_unresolved():
    text = 'Our company is registered in Ireland and incorporated in Canada.'
    values, evidence, missing, _ = prepare(text, country=suggestion('Ireland', 'Ireland'))
    assert 'country' not in values
    assert 'country' not in evidence
    assert 'country' in missing


def test_project_based_elsewhere_does_not_conflict_with_company_registration():
    text = 'Our company is registered in ireland. The feasibility study is based in Canada.'
    values, evidence, missing, _ = prepare(text, country=suggestion('Canada', 'Canada'))
    assert values['country'] == 'Ireland'
    assert evidence['country'] == ['registered in ireland']
    assert 'country' not in missing


def test_negated_registration_does_not_resolve_ambiguous_countries():
    text = 'We are not registered in Ireland. Our study will be in Canada.'
    values, _, missing, _ = prepare(text, country=suggestion('Canada', 'Canada'))
    assert 'country' not in values
    assert 'country' in missing


@pytest.mark.parametrize('text,fields', [
    ('Thirty mysterious purple clouds.', {'country': suggestion('Poland', 'Polish')}),
    ('We have 35 employees.', {'company_size': suggestion('SME', '35 employees')}),
    ('We are not a Polish company.', {'country': suggestion('Poland', 'Polish')}),
    ('We install solar panels.', {'activities': [suggestion('circular_economy', 'install solar panels')]}),
    ('We run a software company.', {'industry': suggestion('manufacturing', 'software company')}),
    ('We request 120000 funding.', {'currency': suggestion('EUR', '120000 funding')}),
    ('We have 35 employees and a budget of EUR 120000.', {'project_budget': suggestion('35', '35 employees')}),
    ('We request EUR 120000 funding.', {'project_budget': suggestion('120000', 'EUR 120000 funding')}),
    ('We have 120000.', {'requested_funding': suggestion('120000', '120000')}),
    ('Polish company with a German office.', {'country': suggestion('Poland', 'Polish')}),
    ('Our budget is EUR 120000 or budget EUR 150000.', {'project_budget': suggestion('120000', 'budget is EUR 120000')}),
    ('Budget EUR 120000.', {'project_budget': suggestion('1e9999999', 'Budget EUR 120000')}),
])
def test_unsupported_or_ambiguous_suggestions_are_not_prefilled(text, fields):
    values, evidence, _, _ = prepare(text, **fields)
    assert not values
    assert not evidence


def test_currency_is_not_converted_and_zero_employees_is_preserved():
    values, _, missing, warnings = prepare('We have 0 employees. We request USD 100 funding.',
        employees=suggestion('0', '0 employees'), currency=suggestion('USD', 'USD'),
        requested_funding=suggestion('100', 'USD 100 funding'))
    assert values['employees'] == '0'
    assert 'currency' in missing
    assert any('Do not relabel' in warning for warning in warnings)


def test_distinct_money_roles_and_exact_cents():
    values, _, _, _ = prepare('We request EUR 120000.51 funding. Total cost EUR 180000.79.',
        requested_funding=suggestion('120000.51', 'EUR 120000.51 funding'),
        project_budget=suggestion('180000.79', 'Total cost EUR 180000.79'))
    assert values['requested_funding'] == '120000.51'
    assert values['project_budget'] == '180000.79'


def test_extraction_makes_one_structured_call_with_no_grants(monkeypatch):
    request = Mock(return_value=ai_form.FormDraft())
    monkeypatch.setattr(ai_form.llm, '_structured_request', request)
    assert ai_form.extract_form('A project description.') == ai_form.FormDraft()
    request.assert_called_once()
    assert request.call_args.args[1:] == ('A project description.', ai_form.FormDraft)


def test_full_verbatim_money_sentence_is_accepted_but_paraphrase_is_rejected():
    text = 'We request EUR 120,000 funding for a project with a total cost of EUR 180,000.'
    values, _, _, _ = prepare(text,
        requested_funding=suggestion('120000', text),
        project_budget=suggestion('180000', text), currency=suggestion('EUR', text))
    assert values == {'requested_funding': '120000', 'project_budget': '180000', 'currency': 'EUR'}
    values, _, _, warnings = prepare(text,
        project_budget=suggestion('180000', 'a project costing EUR 180,000'))
    assert not values
    assert warnings


def test_plain_equipment_purchase_is_not_proof_of_energy_savings():
    values, _, _, _ = prepare('We plan to replace inefficient equipment.',
        activities=[suggestion('energy_efficiency', 'replace inefficient equipment')])
    assert not values
