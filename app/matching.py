"""Apply the demo eligibility rules and sort relevance scores without calling AI."""

from datetime import date

from app.models import Grant
from app.schemas import CompanyProfile, EligibilityCheck, EligibilityResult, RelevanceScore


def profile_problems(profile: CompanyProfile) -> list[str]:
    """Return messages for missing required details or a non-EUR budget.

    An empty list means the profile is ready for matching. Employee count
    is optional. Industry and project type are required for relevance
    scoring even though they do not exclude a grant by themselves."""
    problems = []
    for field in ("country", "company_size", "industry", "project_type", "project_budget", "currency"):
        if getattr(profile, field) is None:
            problems.append(f"Please include {field.replace('_', ' ')} in your description.")
    if profile.currency is not None and profile.currency.upper() != "EUR":
        problems.append("Please provide your project budget in EUR; currency conversion is not supported.")
    return problems


def check_eligibility(
    company_profile: CompanyProfile, grant: Grant, today: date | None = None
) -> EligibilityResult:
    """Decide whether one grant passes every demo rule, recording all failures.

    Check profile completeness, country, company size, deadline and budget.
    The deadline day and both budget limits are included. Compare total
    project budget directly with the funding range; do not convert currency.
    Industry and project type affect later AI relevance, not eligibility.
    Tests can supply today; normal requests use the server's current date.
    Return eligible=True only when there are no failure reasons."""
    reasons = profile_problems(company_profile)
    country = company_profile.country
    country_passed = bool(country) and country.casefold() in {
        item.casefold() for item in grant.countries
    }
    if country and not country_passed:
        reasons.append(f"Eligible countries: {', '.join(grant.countries)}.")
    size = company_profile.company_size
    size_passed = bool(size) and size in grant.company_sizes
    if size and not size_passed:
        reasons.append(f"Supported company sizes: {', '.join(grant.company_sizes)}.")
    deadline_passed = grant.deadline >= (today or date.today())
    if not deadline_passed:
        reasons.append(f"The deadline passed on {grant.deadline.isoformat()}.")
    budget = company_profile.project_budget
    budget_passed = (
        budget is not None
        and (company_profile.currency or "").upper() == "EUR"
        and grant.minimum_funding <= budget <= grant.maximum_funding
    )
    if budget is not None and (company_profile.currency or "").upper() == "EUR" and not budget_passed:
        reasons.append(
            f"Project budget must be between EUR {grant.minimum_funding:,.0f} "
            f"and EUR {grant.maximum_funding:,.0f} under these demo rules."
        )
    checks = [
        EligibilityCheck(
            label="Country", status="Eligible" if country_passed else "Not eligible",
            passed=country_passed,
        ),
        EligibilityCheck(
            label="Company size", status="Eligible" if size_passed else "Not eligible",
            passed=size_passed,
        ),
        EligibilityCheck(
            label="Funding range", status="Within range" if budget_passed else "Outside range",
            passed=budget_passed,
        ),
        EligibilityCheck(
            label="Deadline", status="Open" if deadline_passed else "Closed",
            passed=deadline_passed,
        ),
    ]
    return EligibilityResult(eligible=not reasons, checks=checks, reasons=reasons)


def rank_scores(scores: list[RelevanceScore]) -> list[RelevanceScore]:
    """Return a new list with the highest relevance score first.

    For equal scores, use the smaller grant ID first so ties have a
    predictable order. The original list is left unchanged."""
    return sorted(scores, key=lambda result: (-result.score, result.grant_id))
