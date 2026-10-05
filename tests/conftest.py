"""Shared test examples. Pytest supplies a fresh fixture to each test that names it."""

from datetime import date

import pytest

from app.models import Grant
from app.schemas import CompanyProfile, RelevanceFactor, RelevanceScore


@pytest.fixture
def profile():
    """Provide a fresh Polish SME profile whose EUR 150,000 project fits the sample grant."""
    return CompanyProfile(
        country="Poland", company_size="SME", industry="manufacturing", employees=35,
        project_type="energy_efficiency", project_budget=150000, requested_funding=150000, currency="EUR",
    )


@pytest.fixture
def grant():
    """Provide a fresh sample grant object without saving it to a database."""
    return Grant(
        id=1, title="Factory Energy Upgrade", description="Efficient factory motors.",
        countries=["Poland"], company_sizes=["SME"], industries=["manufacturing"],
        project_types=["energy_efficiency"], minimum_funding=20000, maximum_funding=300000,
        deadline=date(2030, 6, 1), source_url="https://example.com/mock-grants/1",
    )


@pytest.fixture
def make_relevance_score():
    """Build a three-factor result with predictable scores and evidence."""
    def make(grant_id: int, score: int, missing_information: list[str] | None = None):
        def factor(name: str) -> RelevanceFactor:
            return RelevanceFactor(
                score=score, company_need=f"Company {name} need", grant_support=f"Grant {name} scope",
                explanation=f"{name} explanation based on the inputs.", improvement=None,
                confidence="High", clarification=None,
            )

        return RelevanceScore(
            grant_id=grant_id,
            industry_match=factor("Industry"),
            project_type_match=factor("Project"),
            funding_fit=factor("Funding"),
            missing_information=missing_information or [],
        )

    return make
