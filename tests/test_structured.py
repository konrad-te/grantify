"""Boundary checks for the active rule-based comparison, independent of AI."""
from datetime import date, timedelta
from decimal import Decimal

import pytest
from starlette.datastructures import FormData

from app.structured import Project, compare, read_form


@pytest.mark.parametrize("amount,passes", [(19999, False), (20000, True), (300000, True), (300001, False)])
def test_award_boundaries(grant, amount, passes):
    project = Project("Poland", "SME", "manufacturing", ["energy_efficiency"],
                      Decimal(amount), Decimal(900000), "EUR")
    result = compare(project, grant, date(2030, 1, 1))
    assert (not result["failures"]) is passes


def test_deadline_is_inclusive_and_all_failures_are_reported(grant):
    project = Project("Poland", "SME", "manufacturing", ["energy_efficiency"],
                      Decimal(120000), Decimal(150000), "EUR")
    assert not compare(project, grant, grant.deadline)["failures"]
    assert len(compare(project, grant, grant.deadline + timedelta(days=1))["failures"]) == 1
    project.country, project.company_size, project.requested_funding = "Canada", "large", Decimal(1)
    assert len(compare(project, grant, grant.deadline + timedelta(days=1))["failures"]) == 4


def test_duplicate_scalar_values_are_not_silently_resolved():
    values, errors, project = read_form(FormData([
        ("country", "Poland"), ("company_size", "SME"), ("industry", "manufacturing"),
        ("activities", "energy_efficiency"), ("currency", "EUR"),
        ("requested_funding", "120000"), ("requested_funding", "100000"), ("project_budget", "150000"),
    ]))
    assert project is None
    assert errors["requested_funding"] == "Provide one value for this field."


def test_all_industries_is_broad_support_not_an_invented_sector_match(grant):
    grant.industries = ["all"]
    project = Project("Poland", "SME", "agriculture", ["energy_efficiency"],
                      Decimal(120000), Decimal(150000), "EUR")
    assert compare(project, grant, date(2030, 1, 1))["status"] == "Listed categories match"
    project.industry = "other"
    assert compare(project, grant, date(2030, 1, 1))["status"] == "Needs assessment"


@pytest.mark.parametrize("industry,activities,expected,total", [
    ("manufacturing", ["energy_efficiency"], 2, 2),
    ("manufacturing", ["energy_efficiency", "circular_economy"], 2, 3),
    ("software", ["circular_economy"], 0, 2),
    ("other", ["energy_efficiency", "other"], 1, 3),
])
def test_category_coverage_counts_only_confirmed_categories(grant, industry, activities, expected, total):
    if industry == "other":
        grant.industries = ["all"]
    project = Project("Poland", "SME", industry, activities, Decimal(120000), Decimal(150000), "EUR")
    result = compare(project, grant, date(2030, 1, 1))
    assert result["category_matches"] == expected
    assert result["category_total"] == total
    assert bool(result["questions"]) == (expected < total)
