"""Check the Python rules with fixed inputs and dates, without a database or AI call."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.matching import check_eligibility, rank_scores
from app.schemas import CompanyProfile, RelevanceFactor, RelevanceScore


# A fixed date keeps these checks independent of the day you run the tests.
TODAY = date(2030, 1, 1)


def test_matching_profile_is_eligible(profile, grant):
    """Confirm that a profile meeting every rule is eligible and has no failure reasons."""
    result = check_eligibility(profile, grant, TODAY)
    assert result.eligible
    assert result.reasons == []
    assert [(check.label, check.status) for check in result.checks] == [
        ("Country", "Eligible"),
        ("Company size", "Eligible"),
        ("Funding range", "Eligible"),
        ("Deadline", "Open"),
    ]


# Pytest runs this test once per row, using a fresh profile and grant each time.
@pytest.mark.parametrize("changes, reason", [
    ({"country": "France"}, "Eligible countries"),
    ({"company_size": "large"}, "Supported company sizes"),
    ({"project_budget": 19999}, "Project budget"),
    ({"project_budget": 300001}, "Project budget"),
    ({"country": None}, "include country"),
    ({"company_size": None}, "include company size"),
    ({"project_budget": None}, "include project budget"),
    ({"currency": None}, "include currency"),
    ({"currency": "PLN"}, "budget in EUR"),
])
def test_ineligible_profiles(profile, grant, changes, reason):
    """Try each listed profile change and check that it produces the expected rejection reason."""
    result = check_eligibility(profile.model_copy(update=changes), grant, TODAY)
    assert not result.eligible
    assert any(reason in item for item in result.reasons)


@pytest.mark.parametrize("budget", [20000, 300000])
def test_budget_boundaries_are_inclusive(profile, grant, budget):
    """Confirm that a budget exactly at either funding limit is accepted."""
    assert check_eligibility(profile.model_copy(update={"project_budget": budget}), grant, TODAY).eligible


def test_deadline_today_is_open_but_yesterday_is_closed(profile, grant):
    """Confirm that the closing date is included and the following day is too late."""
    grant.deadline = TODAY
    assert check_eligibility(profile, grant, TODAY).eligible
    grant.deadline = date(2029, 12, 31)
    assert not check_eligibility(profile, grant, TODAY).eligible


def test_industry_and_project_type_do_not_change_eligibility(profile, grant):
    """Show that unrelated topics can pass hard rules; relevance is a separate decision."""
    grant.industries = ["software"]
    grant.project_types = ["research_and_development"]
    assert check_eligibility(profile, grant, TODAY).eligible


def test_all_failed_rules_are_explained(profile, grant):
    """Break four rules at once and confirm the checker reports all four failures."""
    grant.countries = ["Germany"]
    grant.company_sizes = ["large"]
    grant.deadline = date(2029, 1, 1)
    grant.maximum_funding = 100000
    assert len(check_eligibility(profile, grant, TODAY).reasons) == 4


def test_country_and_currency_case(profile, grant):
    """Use lowercase country and currency values and verify that only the bad budget fails."""
    changed = profile.model_copy(update={"country": "poland", "currency": "eur", "project_budget": 1})
    result = check_eligibility(changed, grant, TODAY)
    assert len(result.reasons) == 1
    assert "Project budget" in result.reasons[0]


def test_ranking_highest_first_and_stable_ties(make_relevance_score):
    """Verify descending scores and the smaller grant ID first when scores are equal."""
    scores = [make_relevance_score(i, score) for i, score in [(3, 90), (1, 40), (2, 90)]]
    assert [item.grant_id for item in rank_scores(scores)] == [2, 3, 1]


def test_final_relevance_score_is_weighted():
    """Show that Python, rather than the AI, combines the three relevance factors."""
    factor_scores = [90, 80, 70]
    factors = [RelevanceFactor(score=score, company_need="Company goal", grant_support="Grant scope",
                               explanation="Grounded explanation", improvement=None)
               for score in factor_scores]
    result = RelevanceScore(
        grant_id=1,
        industry_match=factors[0],
        project_type_match=factors[1],
        funding_fit=factors[2],
        missing_information=[],
    )
    assert result.weighted_score == 81
    assert result.score == 81


def test_project_mismatch_dominates_perfect_industry_and_budget(make_relevance_score):
    result = make_relevance_score(1, 100)
    result.project_type_match.score = 0
    assert result.score == 40
    assert result.label == "Weak overall fit"


def test_rounding_cannot_create_perfect_score(make_relevance_score):
    result = make_relevance_score(1, 100)
    result.funding_fit.score = 99
    assert result.weighted_score == 99.85
    assert result.score == 99


def test_perfect_score_requires_no_missing_information(make_relevance_score):
    """Cap an otherwise perfect result when important matching information is missing."""
    assert make_relevance_score(1, 100).score == 100
    assert make_relevance_score(1, 100, ["Expected energy savings"]).score == 94


@pytest.mark.parametrize("score, label", [
    (95, "Exact match"),
    (80, "Strong match"),
    (60, "Partial match"),
    (30, "Weak match"),
    (10, "No clear match"),
])
def test_factor_scores_have_plain_language_labels(score, label):
    factor = RelevanceFactor(score=score, company_need="Company goal", grant_support="Grant scope",
                             explanation="Grounded explanation", improvement=None)
    assert factor.label == label


@pytest.mark.parametrize("budget", [-1, 0, float("inf"), float("nan")])
def test_profile_rejects_invalid_budgets(profile, budget):
    """Confirm that Pydantic rejects negative, zero and non-finite project budgets."""
    with pytest.raises(ValidationError):
        CompanyProfile.model_validate({**profile.model_dump(), "project_budget": budget})


@pytest.mark.parametrize("empty", [None, "", "   ", "Null", "NULL", "none", "N/A"])
def test_optional_explanations_remove_placeholder_values(make_relevance_score, empty):
    data = make_relevance_score(1, 100).model_dump()
    data["project_type_match"]["improvement"] = empty
    data["missing_information"] = [empty, "  Confirm the planned equipment.  "]
    result = RelevanceScore.model_validate(data)
    assert result.project_type_match.improvement is None
    assert result.missing_information == ["Confirm the planned equipment."]


def test_null_missing_information_does_not_cap_score(make_relevance_score):
    data = make_relevance_score(1, 100).model_dump()
    data["missing_information"] = None
    assert RelevanceScore.model_validate(data).score == 100
