from typing import List, Optional, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from core.investor_simulation import ClaimAssumptionOutput, InvestorSimulationOutput

class IdeaFilter(BaseModel):
    problem: str = Field(
        description="The stated problem the startup is solving, or 'Not stated'."
    )
    for_who: str = Field(
        description="Who the product is for, or 'Not stated'."
    )
    why_now: str = Field(
        description="Why now is the right time, or 'Not stated'."
    )
    why_you: str = Field(
        description="Why this team/company is suited, or 'Not stated'."
    )
    differentiation: str = Field(
        description="What is different from others, or 'Not stated'."
    )
    weak_points: List[str] = Field(
        description="List of missing or weak areas based on the idea filter."
    )

class InvestorModeFeedback(BaseModel):
    hard_questions: List[str] = Field(
        description="Hard questions from this investor persona."
    )

class InvestorModes(BaseModel):
    seed_investor: InvestorModeFeedback
    vc_investor: InvestorModeFeedback
    angel_investor: InvestorModeFeedback
    demo_day: InvestorModeFeedback

class SkepticismFlag(BaseModel):
    sentence: str = Field(
        description="Exact or near-exact sentence/claim from the pitch transcript."
    )
    reason: str = Field(
        description="Why investors may not believe this point."
    )

class RatingBreakdown(BaseModel):
    problem_severity: int = Field(ge=0, le=10)
    market_size_logic: int = Field(ge=0, le=10)
    differentiation: int = Field(ge=0, le=10)
    scalability: int = Field(ge=0, le=10)
    pitch_clarity: int = Field(ge=0, le=10)

class VideoPitchAnalysis(BaseModel):
    summary: str = Field(
        description="Short 2-4 sentence summary of the pitch."
    )
    strengths: List[str] = Field(
        description="Top strengths based on the pitch content."
    )
    weaknesses: List[str] = Field(
        description="Top weaknesses based on the pitch content."
    )
    overall_score: int = Field(
        ge=0,
        le=100,
        description="Overall investor score (0-100).",
    )
    claim_assumptions: Optional[ClaimAssumptionOutput] = Field(
        default=None,
        description="Extracted claims and assumptions from the transcript.",
    )
    investor_simulation: Optional[InvestorSimulationOutput] = Field(
        default=None,
        description="Rule-based investor simulation output.",
    )
    idea_filter: IdeaFilter
    investor_modes: InvestorModes
    skepticism_flags: List[SkepticismFlag]
    ratings: RatingBreakdown
    filter_ai_score: int = Field(ge=0, le=100)
    investor_ready_status: Literal["Investor ready", "Not ready"]

class GraphState(TypedDict):
    transcript: str
    analysis: Optional[VideoPitchAnalysis]
    error: Optional[str]
