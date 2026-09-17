"""Define the data shapes and validation rules passed between matching steps."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def optional_text(value: str | None) -> str | None:
    """Local models sometimes send the word 'null' instead of JSON null."""
    if value is None or value == [] or value == {}:
        return None
    if value is not None and not isinstance(value, str):
        raise ValueError("Expected text or null")
    placeholder = value.strip().casefold().strip("\"'.! ")
    if placeholder in {
        "", "null", "none", "nil", "n/a", "na", "not applicable", "[]", "{}",
        "[ ]", "{ }", "-", "—", "no clarification needed", "no clarification required",
        "no clarifications needed", "no missing information", "nothing to clarify",
        "none required", "none needed", "no critical information appears to be missing",
        "no additional information suggested by the ai",
    }:
        return None
    return value.strip()


def specific_clarification(value: str | None) -> str | None:
    value = optional_text(value)
    if value and value.casefold().rstrip(".! ") in {
        "important information is missing", "information is missing",
        "missing information", "more information is needed", "needs clarification",
    }:
        raise ValueError("Name the uncertain fact and explain why it matters")
    return value


class CompanyProfile(BaseModel):
    """Validated company and project details extracted from the description.

    Every field must be included, but unknown values may be None. Pydantic
    rejects invalid values; matching.py separately checks required details."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    country: str | None = Field(min_length=1, description="English country name or null")
    company_size: Literal["SME", "large"] | None
    industry: str | None = Field(min_length=1)
    employees: int | None = Field(ge=0)
    project_type: str | None = Field(min_length=1)
    project_goal: str | None = Field(default=None, min_length=1, description="Explicit intended outcome of the project, or null")
    project_budget: float | None = Field(gt=0, allow_inf_nan=False)
    currency: str | None = Field(description="Explicit ISO currency code, e.g. EUR, or null")
    source_phrases: list[str] = Field(default_factory=list, description="Exact short excerpts from the original description for the extracted attributes")


class EligibilityCheck(BaseModel):
    """One hard requirement evaluated by deterministic Python logic."""
    label: str
    status: str
    passed: bool


class EligibilityResult(BaseModel):
    """A Python eligibility decision, its checks and all failure reasons."""
    eligible: bool
    checks: list[EligibilityCheck]
    reasons: list[str]


class RelevanceFactor(BaseModel):
    """One explained part of a grant's relevance score."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    score: int = Field(ge=0, le=100)
    company_need: str = Field(min_length=1, description="Actual company goal or relevant profile value")
    grant_support: str = Field(min_length=1, description="What this grant explicitly supports")
    explanation: str = Field(min_length=1)
    improvement: str | None = Field(description="Conditional, realistic way to improve fit, or null")
    confidence: Literal["High", "Medium", "Low"] = Field(
        description="Evidence certainty, separate from fit: High is explicit, Medium has a specific uncertainty, Low has little evidence"
    )
    clarification: str | None = Field(
        description="Name the uncertain fact and explain how it could change the assessment; null when no clarification is needed"
    )

    @field_validator("improvement", mode="before")
    @classmethod
    def clean_improvement(cls, value: str | None) -> str | None:
        return optional_text(value)

    @field_validator("clarification", mode="before")
    @classmethod
    def clean_clarification(cls, value: str | None) -> str | None:
        return specific_clarification(value)

    @model_validator(mode="after")
    def explain_uncertainty(self):
        if self.confidence != "High" and not self.clarification:
            raise ValueError("Medium or Low confidence requires a specific clarification")
        return self

    @property
    def tone(self) -> str:
        return "strong" if self.score >= 75 else "partial" if self.score >= 50 else "weak"

    @property
    def label(self) -> str:
        """Turn the internal number into a phrase shown to the user."""
        if self.score == 100 and self.confidence == "High" and not self.clarification:
            return "Exact match"
        if self.score >= 75:
            return "Strong match"
        if self.score >= 50:
            return "Partial match"
        if self.score >= 25:
            return "Weak match"
        return "No match"


class RelevanceScore(BaseModel):
    """Three AI-rated factors with an overall score calculated by Python."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    grant_id: int
    industry_match: RelevanceFactor
    project_type_match: RelevanceFactor
    funding_fit: RelevanceFactor
    missing_information: list[str]

    @field_validator("missing_information", mode="before")
    @classmethod
    def clean_missing_information(cls, value):
        if value is None or value == {} or isinstance(value, str) and optional_text(value) is None:
            return []
        if isinstance(value, list):
            return [cleaned for item in value if (cleaned := specific_clarification(item))]
        return value

    @property
    def match_reasons(self) -> list[str]:
        """Reuse the strongest supported factor explanations without inventing positives."""
        ranked = sorted(self.breakdown, key=lambda item: (-item[1].score, -item[2]))
        reasons = {}
        for _, factor, _ in ranked:
            if factor.score >= 75 and factor.confidence != "Low":
                explanation = optional_text(factor.explanation)
                if explanation:
                    reasons.setdefault(explanation.casefold().rstrip("."), explanation)
        return list(reasons.values())[:3]

    @property
    def main_reason(self) -> str:
        if self.match_reasons:
            return " ".join(self.match_reasons)
        # With no strong factors, show the closest alignment without claiming a strong match.
        if self.project_type_match.score >= 50:
            return self.project_type_match.explanation
        strongest = max((factor for _, factor, _ in self.breakdown), key=lambda factor: factor.score)
        return strongest.explanation

    @property
    def main_concern(self) -> str | None:
        # Surface mismatches here; unresolved questions have their own clarification section.
        for _, factor, _ in self.breakdown:
            if factor.score < 75 and factor.explanation != self.main_reason:
                return factor.explanation
        return None

    @property
    def clarifications(self) -> list[str]:
        """Collect uncertainties once, preserving their order and removing duplicates."""
        items = [factor.clarification for _, factor, _ in self.breakdown]
        items.extend(self.missing_information)
        unique = {}
        for item in items:
            if cleaned := optional_text(item):
                unique.setdefault(cleaned.casefold().rstrip("."), cleaned)
        return list(unique.values())

    @property
    def assessment_confidence(self) -> str:
        """Use the least certain factor; unresolved questions prevent High confidence."""
        levels = [factor.confidence for _, factor, _ in self.breakdown]
        if "Low" in levels:
            return "Low"
        return "Medium" if "Medium" in levels or self.clarifications else "High"

    def factor_label(self, name: str, factor: RelevanceFactor) -> str:
        if name == "Funding fit" and factor.score >= 75:
            return "Within range"
        if factor.label == "Exact match" and self.missing_information:
            return "Strong match"
        return factor.label

    @property
    def weighted_score(self) -> float:
        """Project fit matters most; an affordable unrelated grant should rank poorly."""
        return sum(factor.score * weight for _, factor, weight in self.breakdown) / 100

    @property
    def score(self) -> int:
        rounded = round(self.weighted_score)
        # Rounding alone must never create a perfect match.
        if self.weighted_score < 100:
            rounded = min(rounded, 99)
        return rounded

    @property
    def tone(self) -> str:
        return "strong" if self.score >= 75 else "partial" if self.score >= 50 else "weak"

    @property
    def label(self) -> str:
        if self.score >= 90:
            return "Very strong match"
        if self.score < 25:
            return "No match"
        return {"strong": "Strong match", "partial": "Partial match", "weak": "Weak match"}[self.tone]

    @property
    def breakdown(self) -> list[tuple[str, RelevanceFactor, int]]:
        """Single source for display order, names and percentage weights."""
        return [
            ("Project fit", self.project_type_match, 60),
            ("Industry match", self.industry_match, 25),
            ("Funding fit", self.funding_fit, 15),
        ]


class RelevanceBatch(BaseModel):
    """The wrapper containing all factor breakdowns from one Ollama request."""
    model_config = ConfigDict(extra="forbid")

    results: list[RelevanceScore]
