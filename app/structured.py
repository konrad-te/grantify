"""Explicit form choices and deterministic comparisons with the demo catalogue."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re

COUNTRIES = {name: name for name in (
    "Poland", "Germany", "Czechia", "France", "Spain", "Italy", "Netherlands",
    "Austria", "Belgium", "Denmark", "Finland", "Ireland", "Portugal", "Sweden",
    "Bulgaria", "Croatia", "Cyprus", "Estonia", "Greece", "Hungary", "Latvia",
    "Lithuania", "Luxembourg", "Malta", "Romania", "Slovakia", "Slovenia",
    "Iceland", "Israel", "Norway", "Switzerland", "Türkiye", "Moldova",
    "Montenegro", "North Macedonia", "Ukraine", "Singapore", "South Africa", "South Korea",
    "United Kingdom", "United States", "Canada",
)} | {"other": "Other country"}
SIZES = {"SME": "Micro, small or medium enterprise (SME)", "large": "Large enterprise"}
INDUSTRIES = {"manufacturing": "Manufacturing", "software": "Software",
    "agriculture": "Agriculture", "waste_management": "Waste management and recycling", "other": "Other industry"}
ACTIVITIES = {
    "energy_efficiency": "Energy-saving equipment or building improvements",
    "renewable_energy": "Solar panels, renewable generation or battery storage",
    "digitalization": "Automation, sensors or business software",
    "circular_economy": "Recycling, material reuse or waste reduction",
    "research_and_development": "Research, experiments or prototype development",
    "water_efficiency": "Water-saving equipment or irrigation",
    "machinery_replacement": "Other machinery purchases or replacement",
    "commercialization": "Implement completed R&D results or commercialise innovative technology",
    "startup_development": "Develop an innovative startup through incubation or acceleration",
    "grant_preparation": "Prepare an application to an EU funding programme",
    "export_promotion": "International market feasibility, export promotion or trade fairs",
    "product_design": "Design audit, product design strategy and implementation",
    "critical_biotech": "Develop or manufacture critical biotechnology (STEP)",
    "critical_clean": "Develop or manufacture critical clean technology (STEP)",
    "critical_digital": "Develop or manufacture critical digital technology (STEP)",
    "other": "Other activity"}
OUTCOMES = {"lower_energy": "Lower energy consumption", "lower_emissions": "Lower emissions",
    "less_waste": "Less waste or material use", "less_water": "Lower water consumption",
    "productivity": "Higher productivity or capacity", "new_products": "New products or services", "other": "Other outcome"}
OPTIONS = {"country": COUNTRIES, "company_size": SIZES, "industry": INDUSTRIES,
    "activities": ACTIVITIES, "outcomes": OUTCOMES, "currency": {"EUR": "EUR — Euro", "PLN": "PLN — Polish złoty"}}


@dataclass
class Project:
    country: str
    company_size: str
    industry: str
    activities: list[str]
    requested_funding: Decimal
    project_budget: Decimal
    currency: str


def read_form(form):
    """Validate on the server, preserving input and field errors for correction."""
    keys = ["country", "country_other", "company_size", "industry", "industry_other",
        "requested_funding", "project_budget", "currency", "employees",
        "activities_other", "outcomes_other"]
    values = {key: str(form.get(key, "")).strip() for key in keys}
    values.update({key: list(dict.fromkeys(str(v) for v in form.getlist(key))) for key in ("activities", "outcomes")})
    errors = {}
    for key in keys:
        if len(form.getlist(key)) > 1:
            errors[key] = "Provide one value for this field."
    for key in ("country", "company_size", "industry", "currency"):
        if values[key] not in OPTIONS[key]:
            errors[key] = "Select an option from the list."
    for key in ("activities", "outcomes"):
        if any(value not in OPTIONS[key] for value in values[key]):
            errors[key] = "Select only the listed options."
    if not values["activities"]:
        errors["activities"] = "Select at least one planned activity."
    for key in ("country", "industry", "activities", "outcomes"):
        selected = values[key]
        is_other = "other" in selected if isinstance(selected, list) else selected == "other"
        if is_other and not values[key + "_other"]:
            errors[key + "_other"] = "Describe your Other selection."
        if len(values[key + "_other"]) > 200:
            errors[key + "_other"] = "Use 200 characters or fewer."
    amounts = {}
    for key in ("requested_funding", "project_budget"):
        if not re.fullmatch(r"[0-9]{1,13}(?:\.[0-9]{1,2})?", values[key]):
            errors[key] = "Enter a positive amount using digits and an optional decimal point (e.g. 120000 or 120000.50)."
        else:
            amounts[key] = Decimal(values[key])
            if amounts[key] <= 0:
                errors[key] = "Enter an amount greater than zero."
    if len(amounts) == 2 and amounts["requested_funding"] > amounts["project_budget"]:
        errors["requested_funding"] = "Requested funding cannot exceed total project cost. Check both amounts."
    if values["employees"] and not re.fullmatch(r"[0-9]{1,9}", values["employees"]):
        errors["employees"] = "Enter a whole number of employees, including 0, or leave blank."
    if errors:
        return values, errors, None
    return values, errors, Project(
        country=values["country_other"] if values["country"] == "other" else values["country"],
        company_size=values["company_size"], industry=values["industry"], activities=values["activities"],
        requested_funding=amounts["requested_funding"], project_budget=amounts["project_budget"], currency=values["currency"])


def explain_no_results(project, grants, today=None):
    """Explain the first blocking step across the catalogue in plain language."""
    today = today or date.today()
    if not grants:
        return "The demo catalogue is empty. There are no programmes to search yet."
    candidates = [g for g in grants if project.country.casefold() in {c.casefold() for c in g.countries}]
    if not candidates:
        countries = ", ".join(sorted({c for g in grants for c in g.countries}))
        return (f"You selected {project.country}. None of the demo programmes supports companies registered there. "
                f"This catalogue only covers: {countries}. Your entry is valid; this is a limitation of the demo data.")
    candidates = [g for g in candidates if project.company_size in g.company_sizes]
    if not candidates:
        return (f"The demo programmes covering {project.country} do not support your selected company size "
                f"({SIZES[project.company_size]}). Your entry is valid; this catalogue has no suitable programme for that combination.")
    open_programmes = [g for g in candidates if g.deadline >= today]
    if not open_programmes:
        return f"All demo programmes covering {project.country} and your company size have passed their deadlines."
    if not any(g.minimum_funding <= project.requested_funding <= g.maximum_funding for g in open_programmes):
        return (f"You requested EUR {project.requested_funding:,.2f}. That amount is outside the award range of every open "
                f"demo programme covering {project.country} and your company size. The detailed reasons below show each programme’s limits.")
    return "No sample programmes pass all the basic checks. The detailed reasons below explain which requirements were not met."


def compare(project, grant, today=None):
    """Report known checks and category overlap without claiming full eligibility."""
    today = today or date.today()
    failures = []
    if project.country.casefold() not in {country.casefold() for country in grant.countries}:
        failures.append(f"Company country must be one of: {', '.join(grant.countries)}.")
    if project.company_size not in grant.company_sizes:
        failures.append(f"Company size must be one of: {', '.join(grant.company_sizes)}.")
    if not grant.minimum_funding <= project.requested_funding <= grant.maximum_funding:
        failures.append(f"Requested funding must be EUR {grant.minimum_funding:,.0f}–{grant.maximum_funding:,.0f}.")
    if grant.deadline < today:
        failures.append(f"The deadline passed on {grant.deadline.isoformat()}.")
    matched = [ACTIVITIES[key] for key in project.activities if key in grant.project_types]
    unconfirmed = [ACTIVITIES[key] for key in project.activities if key not in grant.project_types]
    industry_match = project.industry in grant.industries or "all" in grant.industries
    questions = []
    if project.industry == "other":
        questions.append("Your Other industry needs assessment; the entered text has not been classified.")
    elif not industry_match:
        questions.append("Your industry is not listed in this programme's focus. Confirm whether it is supported.")
    if unconfirmed:
        questions.append("Activities not confirmed by the listed categories: " + "; ".join(unconfirmed) + ".")
    return {"grant": grant, "failures": failures, "matched": matched, "questions": questions,
        "category_matches": len(matched) + int(industry_match and project.industry != "other"),
        "category_total": len(project.activities) + 1,
        "activity_total": len(project.activities),
        "industry_confirmed": industry_match and project.industry != "other",
        "industry_label": INDUSTRIES[project.industry],
        "country_label": project.country,
        "size_label": SIZES[project.company_size],
        "requested_funding": project.requested_funding,
        "industry_match": industry_match, "status": "Needs assessment" if questions else "Listed categories match",
        "tone": "partial" if questions else "strong"}
