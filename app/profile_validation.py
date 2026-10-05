"""Check extraction against the user's words before using or highlighting it.

Numbers need explicit roles, currencies need explicit markers, and semantic
fields need short supporting excerpts. Unclear values stay unknown.
"""

import re

from app.schemas import CompanyProfile, ProfileEvidence


NUMBER = r"(?:\d{1,3}(?:[, \u00a0]\d{3})+|\d+)(?:\.\d+)?(?:\s*(?:thousand|million|k)\b)?"
NUMBERS = re.compile(rf"(?<![\w.])[-+]?{NUMBER}(?!\w|\.\d)", re.I)
CURRENCIES = {
    "EUR": r"\b(?:EUR|euros?)\b|€",
    "PLN": r"\b(?:PLN|zloty|złoty|zł)\b",
    "GBP": r"\bGBP\b|£",
    "USD": r"\bUSD\b|US\$",
    **{code: rf"\b{code}\b" for code in ("CAD", "AUD", "CHF", "CZK", "SEK", "NOK", "DKK", "JPY")},
}
MONEY = r"(?:EUR|PLN|GBP|USD|euros?|zloty|złoty|zł|€|£|US\$|\$)"
REQUESTED_FUNDING = re.compile(
    rf"(?<!\w)(?:{MONEY}\s*)?{NUMBER}(?:\s*{MONEY})?\s+(?:in\s+)?(?:funding|grant|financial support)\b"
    rf"|\b(?:funding|grant)(?:\s+(?:request|requested|amount))?\s*(?:of|:|=)?\s*(?:{MONEY}\s*)?{NUMBER}",
    re.I,
)
NUMBER_PATTERNS = {
    "requested_funding": [
        rf"(?<![\w.\-])(?:{MONEY}\s*)?(?P<number>{NUMBER})(?:\s*{MONEY})?\s+(?:in\s+)?(?:funding|grant|financial support)\b",
        rf"\b(?:funding|grant)(?:\s+(?:request|requested|amount))?\s*(?:of|:|=)?\s*(?:{MONEY}\s*)?(?P<number>{NUMBER})",
    ],
    "employees": [
        rf"(?<![\w.\-])(?P<number>{NUMBER})\s+(?:full[- ]time\s+)?(?:employees|workers|staff|people)\b",
        rf"\b(?:employees|headcount|staff|team of|employs?|employing)\s*(?:is|of|:|=)?\s*(?P<number>{NUMBER})\b",
    ],
    "project_budget": [
        rf"\b(?:budget|costs?|investment|project worth)\s*(?:(?:is|of|at|around|approximately|estimated at)\s*)?[:=]?\s*(?:{MONEY}\s*)?(?P<number>{NUMBER})(?:\s*{MONEY})?",
        rf"(?<!\w)(?:{MONEY}\s*)?(?P<number>{NUMBER})(?:\s*{MONEY})?\s+(?:(?:total|project)\s+)*(?:budget|cost|investment)\b",
    ],
}
COUNTRY_ALIASES = {
    "poland": "Poland|Polish", "germany": "Germany|German", "czechia": "Czechia|Czech Republic|Czech",
    "france": "France|French", "spain": "Spain|Spanish", "italy": "Italy|Italian",
    "netherlands": "Netherlands|Dutch", "canada": "Canada|Canadian",
    "united kingdom": "United Kingdom|UK|British", "united states": "United States|USA|American",
}
ACTION = r"\b(?:replac\w*|install\w*|buy\w*|purchas\w*|upgrad\w*|improv\w*|reduc\w*|develop\w*|build\w*|expand\w*|automat\w*|moderniz\w*|modernis\w*|increas\w*|lower\w*|sav\w*|cut\w*|launch\w*|research\w*)\b"


def number_value(text: str) -> float:
    text = re.sub(r"[,\s]", "", text.lower())
    multiplier = 1
    for suffix, scale in (("thousand", 1000), ("million", 1000000), ("k", 1000)):
        if text.endswith(suffix):
            text, multiplier = text[:-len(suffix)], scale
            break
    return float(text) * multiplier


def _labelled_number(description: str, field: str, value: int | float | None) -> re.Match[str] | None:
    matches = [match for pattern in NUMBER_PATTERNS[field]
               for match in re.finditer(pattern, description, re.I)]
    if value is None or {number_value(m.group("number")) for m in matches} != {value}:
        return None
    return matches[0]


def _excerpt(description: str, evidence: str | None) -> str | None:
    if not evidence or len(evidence) > 120 or len(evidence.split()) > 14:
        return None
    match = re.search(r"(?<!\w)" + re.escape(evidence) + r"(?!\w)", description, re.I)
    return match.group() if match else None


def validate_profile(description: str, profile: CompanyProfile) -> CompanyProfile:
    """Discard unsupported guesses and rebuild highlights from accepted evidence only."""
    values = profile.model_dump()
    accepted = {}
    for field in ProfileEvidence.model_fields:
        value = getattr(profile, field)
        evidence = getattr(profile.evidence, field)
        excerpts = evidence if isinstance(evidence, list) else [evidence]
        proofs = [proof for excerpt in excerpts if (proof := _excerpt(description, excerpt))]
        proof = proofs[0] if proofs else None
        if value is None:
            continue
        if field == "country":
            aliases = COUNTRY_ALIASES.get(value.casefold(), re.escape(value))
            match = re.search(rf"\b(?:{aliases})\b", description, re.I)
            proof = match.group() if match else None
        elif field == "company_size":
            patterns = {
                "SME": r"\bSMEs?\b|\b(?:micro|small|medium)(?:[- ]sized)?\s+(?:business|company|enterprise)\b",
                "large": r"\blarge\s+(?:business|company|enterprise)\b",
            }
            found = {size: re.search(pattern, description, re.I) for size, pattern in patterns.items()}
            proof = found[value].group() if found[value] and not found['large' if value == 'SME' else 'SME'] else None
        elif field in NUMBER_PATTERNS:
            match = _labelled_number(description, field, value)
            proof = match.group() if match else None
        elif field == "currency":
            found = {code: re.search(pattern, description, re.I) for code, pattern in CURRENCIES.items()}
            codes = [code for code, match in found.items() if match]
            code = value.upper()
            proof = found[code].group() if codes == [code] else None
            values[field] = code
        elif field in {"project_type", "project_goal"}:
            # An isolated topic such as 'energy' is not a stated activity or outcome.
            proofs = [item for item in proofs if len(item.split()) >= 2 and re.search(ACTION, item, re.I)]
            proof = (proofs if isinstance(evidence, list) else proofs[0]) if proofs else None
        elif field == "industry" and proof:
            words = re.findall(r"[a-z]{3,}", value.casefold())
            related = next((match for word in words if (match := re.search(rf"\b{re.escape(word[:5])}\w*", proof, re.I))), None)
            business_context = re.search(r"\b(?:industry|sector|business|company|manufactur\w*|we (?:make|sell|produce))\b", proof, re.I)
            if not related or (value.casefold() in {"energy", "technology", "innovation", "green"} and not business_context):
                proof = None
            elif related:
                proof = _excerpt(proof, value.replace("_", " ")) or related.group()
        if proof:
            accepted[field] = proof
            if field == "project_goal":
                # Keep the displayed/scored goal grounded in the accepted outcomes.
                values[field] = "; ".join(proof) if isinstance(proof, list) else proof
        else:
            values[field] = None

    # One occurrence cannot simultaneously be an employee count and a budget.
    employee = _labelled_number(description, "employees", values["employees"])
    budget = _labelled_number(description, "project_budget", values["project_budget"])
    if employee and budget and employee.span("number") == budget.span("number"):
        for field in ("employees", "project_budget"):
            values[field] = None
            accepted.pop(field, None)
    values["evidence"] = accepted
    values["source_phrases"] = list(dict.fromkeys(
        phrase for proof in accepted.values() for phrase in (proof if isinstance(proof, list) else [proof])
    ))
    return CompanyProfile.model_validate(values)


def unassigned_numbers(description: str, profile: CompanyProfile) -> list[str]:
    """Find numbers still needing a role; do not re-ask about a confirmed amount."""
    covered = [match.span() for phrase in profile.source_phrases
               for match in re.finditer(re.escape(phrase), description, re.I)]
    covered.extend(match.span() for match in REQUESTED_FUNDING.finditer(description))
    return list(dict.fromkeys(match.group() for match in NUMBERS.finditer(description)
        if number_value(match.group()) not in {profile.employees, profile.project_budget}
        and not any(start <= match.start() and match.end() <= end for start, end in covered)))[:3]
