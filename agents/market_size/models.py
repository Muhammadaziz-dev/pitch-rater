from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from typing_extensions import TypedDict

class CompanyOverview(BaseModel):
    """Response model for company overview details"""
    company_name: Optional[str] = Field(default=None, alias="Company Name", description="Name of the company")
    what_company_does: Optional[str] = Field(default=None, alias="What the Company Does", description="Company description")
    team_size: Optional[str] = Field(default=None, alias="Team Size", description="Size of the team")
    industry: Optional[str] = Field(default=None, alias="Industry", description="Industry category")
    region: Optional[str] = Field(default=None, alias="Region", description="Geographic region")
    funding_stage: Optional[str] = Field(default=None, alias="Funding Stage", description="Current funding stage")
    ask: Optional[str] = Field(default=None, alias="Ask", description="Funding ask amount")
    valuation: Optional[str] = Field(default=None, alias="Valuation", description="Company valuation")
    previous_rounds: Optional[List[Dict[str, str]]] = Field(default=None, alias="Previous Rounds", description="Previous funding rounds")

class TargetMarketData(TypedDict):
    primary_users: str
    geography: str
    secondary_users: str
    citations: List[str]

class MainProblemData(TypedDict):
    pain_points: List[str]
    citations: List[str]

class CompetitorInfo(TypedDict):
    name: str
    description: str
    citations: List[str]

class UserSentimentData(TypedDict):
    positive: List[str]
    negative: List[str]
    citations: List[str]

class MarketSizeGrowthData(TypedDict):
    market_size: str
    growth_rate: str
    growth_notes: str
    citations: List[str]

class PricingStrategyData(TypedDict):
    competitor: str
    pricing: str
    notes: str
    citations: List[str]

class UniqueValueGapData(TypedDict):
    gaps: List[str]
    citations: List[str]

class RisksChallengesData(TypedDict):
    risks: List[str]
    citations: List[str]

class TrendsData(TypedDict):
    trends: List[str]
    citations: List[str]

class MarketResearchData(TypedDict):
    clarification_questions: List[str]
    target_market: TargetMarketData
    main_problem: MainProblemData
    competitors: List[CompetitorInfo]
    user_sentiment: UserSentimentData
    market_size_growth: MarketSizeGrowthData
    pricing_strategies: List[PricingStrategyData]
    unique_value_gap: UniqueValueGapData
    risks_challenges: RisksChallengesData
    trends: TrendsData

class GraphState(TypedDict):
    input_overview: CompanyOverview
    market_research: Optional[MarketResearchData]
    error: Optional[str]

class TargetMarketModel(BaseModel):
    primary_users: str
    geography: str
    secondary_users: str
    citations: List[str]

class MainProblemModel(BaseModel):
    pain_points: List[str]
    citations: List[str]

class CompetitorModel(BaseModel):
    name: str
    description: str
    citations: List[str]

class UserSentimentModel(BaseModel):
    positive: List[str]
    negative: List[str]
    citations: List[str]

class MarketSizeGrowthModel(BaseModel):
    market_size: str
    growth_rate: str
    growth_notes: str
    citations: List[str]

class PricingStrategyModel(BaseModel):
    competitor: str
    pricing: str
    notes: str
    citations: List[str]

class UniqueValueGapModel(BaseModel):
    gaps: List[str]
    citations: List[str]

class RisksChallengesModel(BaseModel):
    risks: List[str]
    citations: List[str]

class TrendsModel(BaseModel):
    trends: List[str]
    citations: List[str]

class MarketResearchResponse(BaseModel):
    clarification_questions: List[str]
    target_market: TargetMarketModel
    main_problem: MainProblemModel
    competitors: List[CompetitorModel]
    user_sentiment: UserSentimentModel
    market_size_growth: MarketSizeGrowthModel
    pricing_strategies: List[PricingStrategyModel]
    unique_value_gap: UniqueValueGapModel
    risks_challenges: RisksChallengesModel
    trends: TrendsModel
