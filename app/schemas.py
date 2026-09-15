"""Define the data shapes and validation rules passed between matching steps."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


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
    project_budget: float | None = Field(gt=0, allow_inf_nan=False)
    currency: str | None = Field(description="Explicit ISO currency code, e.g. EUR, or null")


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

    @property
    def tone(self) -> str:
        return "strong" if self.score >= 75 else "partial" if self.score >= 50 else "weak"

    @property
    def label(self) -> str:
        """Turn the internal number into a phrase shown to the user."""
        if self.score >= 90:
            return "Exact match"
        if self.score >= 75:
            return "Strong match"
        if self.score >= 50:
            return "Partial match"
        if self.score >= 25:
            return "Weak match"
        return "No clear match"


class RelevanceScore(BaseModel):
    """Three AI-rated factors with an overall score calculated by Python."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    grant_id: int
    industry_match: RelevanceFactor
    project_type_match: RelevanceFactor
    funding_fit: RelevanceFactor
    missing_information: list[str]

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
        return min(rounded, 94) if self.missing_information else rounded

    @property
    def tone(self) -> str:
        return "strong" if self.score >= 75 else "partial" if self.score >= 50 else "weak"

    @property
    def label(self) -> str:
        return {"strong": "Strong overall fit", "partial": "Partial overall fit", "weak": "Weak overall fit"}[self.tone]

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
