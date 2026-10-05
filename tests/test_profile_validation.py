"""Adversarial and ordinary descriptions exercise extraction evidence checks."""
import pytest

from app.matching import profile_problems
from app.profile_validation import validate_profile
from app.schemas import CompanyProfile, ProfileEvidence


@pytest.fixture
def extracted():
    return CompanyProfile(
        country="Poland", company_size="SME", industry="manufacturing", employees=30,
        project_type="machinery_replacement", project_goal="reduce electricity use",
        project_budget=30000, currency="EUR", source_phrases=["untrusted highlight"],
        evidence=ProfileEvidence(industry="manufacturing", project_type="replace machinery",
                                 project_goal=["reduce electricity use"]),
    )


def test_gibberish_cannot_become_a_complete_company_profile(extracted):
    text = "bdfbdzbdfbd rgr <grae polish dmiamdjqaw energy 30000"
    extracted.employees = 30000
    extracted.currency = "PLN"
    extracted.industry = "energy"
    extracted.evidence = ProfileEvidence(**{key: [text] if key == "project_goal" else text for key in ProfileEvidence.model_fields})
    extracted.source_phrases = text.split()
    result = validate_profile(text, extracted)
    assert result.country == "Poland"
    assert all(getattr(result, field) is None for field in ProfileEvidence.model_fields if field != "country")
    assert result.source_phrases == ["polish"]
    questions = profile_problems(result, text)
    assert "What does 30000 refer to" in questions[0]
    assert any("Which currency" in question for question in questions)
    assert not any("You stated PLN" in question for question in questions)


def test_explicit_facts_survive_and_highlights_are_supported(extracted):
    text = "Polish manufacturing SME with 30 employees. We will replace machinery to reduce electricity use. Project budget: EUR 30,000."
    result = validate_profile(text, extracted)
    assert result.model_dump(exclude={"evidence", "source_phrases"}) == extracted.model_dump(exclude={"evidence", "source_phrases"})
    assert len(profile_problems(result, text)) == 1
    assert "How much funding" in profile_problems(result, text)[0]
    assert all(phrase in text for phrase in result.source_phrases)
    assert "untrusted highlight" not in result.source_phrases


@pytest.mark.parametrize("text, employees, budget", [
    ("30000", None, None),
    ("30000 employees", 30000, None),
    ("Total project budget: 30000", None, 30000),
    ("Project cost is EUR 30,000", None, 30000),
    ("Project budget: 30 000 euros", None, 30000),
    ("Project budget: EUR 30k", None, 30000),
    ("Project budget: EUR 30 thousand", None, 30000),
    ("Headcount: 30000", 30000, None),
    ("budget: 30000 employees", None, None),
    ("30000 employees. Project budget: EUR 30000", 30000, 30000),
    ("Budget EUR 30000, later budget EUR 40000", None, None),
    ("-30000 employees", None, None),
])
def test_numbers_require_distinct_labelled_roles(extracted, text, employees, budget):
    extracted.employees = 30000
    result = validate_profile(text, extracted)
    assert result.employees == employees
    assert result.project_budget == budget


@pytest.mark.parametrize("text, claimed, expected", [
    ("Polish company with budget 30000", "PLN", None),
    ("Polish company with budget 30000", "EUR", None),
    ("Budget: 30000 PLN", "PLN", "PLN"),
    ("Budget: €30000", "EUR", "EUR"),
    ("Budget: 30000 euros", "EUR", "EUR"),
    ("Budget: $30000", "USD", None),
    ("Budget EUR 30000 or PLN 30000", "EUR", None),
])
def test_currency_is_explicit_and_unambiguous(extracted, text, claimed, expected):
    extracted.currency = claimed
    result = validate_profile(text, extracted)
    assert result.currency == expected


def test_employee_count_zero_is_preserved_without_inferring_size(extracted):
    extracted.employees = 0
    result = validate_profile("Polish manufacturing business with 0 employees", extracted)
    assert result.employees == 0
    assert result.company_size is None


def test_missing_or_broad_semantic_evidence_is_rejected(extracted):
    extracted.evidence.industry = "a phrase not in the input"
    extracted.evidence.project_type = "energy"
    extracted.evidence.project_goal = ["energy"]
    result = validate_profile("Polish manufacturing SME energy 30000", extracted)
    assert result.industry is result.project_type is result.project_goal is None
    assert result.source_phrases == ["Polish", "SME"]


def test_adding_labelled_answers_resolves_the_bare_number(extracted):
    text = "Polish manufacturing SME energy 30000. We plan to replace machinery. Project budget: EUR 30000."
    result = validate_profile(text, extracted)
    assert result.employees is None
    assert result.project_goal is None
    assert len(profile_problems(result, text)) == 1
    assert "How much funding" in profile_problems(result, text)[0]


def test_follow_up_names_unlabelled_number_even_at_end_of_sentence(extracted):
    text = "Polish energy 30000."
    result = validate_profile(text, extracted)
    assert "What does 30000 refer to" in profile_problems(result, text)[0]


def test_screenshot_description_preserves_facts_and_asks_only_for_total_cost(extracted):
    text = (
        "Polish manufacturing SME with 30 employees. "
        "We want €120,000 funding to improve energy efficiency in our factory "
        "by replacing old machinery and reducing electricity consumption."
    )
    extracted.project_budget = 120000
    extracted.requested_funding = 120000
    extracted.evidence.project_type = "replacing old machinery"
    extracted.evidence.project_goal = ["improve energy efficiency", "reducing electricity consumption"]
    result = validate_profile(text, extracted)
    assert all(getattr(result, field) is not None for field in ProfileEvidence.model_fields
               if field != "project_budget")
    assert result.project_budget is None
    questions = profile_problems(result, text)
    assert len(questions) == 1
    assert "You stated a funding amount" in questions[0]
    assert "total cost" in questions[0]
    assert "replacing old machinery" in result.source_phrases
    assert "reducing electricity consumption" in result.source_phrases
    assert "improve energy efficiency" in result.source_phrases
    assert "€120,000 funding" in result.source_phrases
    assert "€" in result.source_phrases
    assert result.requested_funding == 120000


def test_distinct_award_and_total_are_preserved(extracted):
    extracted.requested_funding = 120000
    extracted.project_budget = 200000
    text = "We request EUR 120,000 funding. Total project budget: EUR 200,000."
    result = validate_profile(text, extracted)
    assert result.requested_funding == 120000
    assert result.project_budget == 200000


def test_unquoted_goal_is_never_highlighted(extracted):
    extracted.evidence.project_goal = ["reduce electricity use", "increase production"]
    result = validate_profile("We will replace machinery to reduce electricity use.", extracted)
    assert result.project_goal == "reduce electricity use"
    assert "increase production" not in result.source_phrases


@pytest.mark.parametrize("funding_text", ["€120,000 funding", "funding of EUR 120,000", "grant amount: 120000 EUR"])
def test_funding_request_does_not_hide_other_unlabelled_numbers(extracted, funding_text):
    text = f"Polish manufacturing SME with 30 employees. We want {funding_text}. 50000."
    result = validate_profile(text, extracted)
    questions = profile_problems(result, text)
    assert "What does 50000 refer to" in questions[0]
    assert "120,000" not in questions[0]
    assert "120000" not in questions[0]
