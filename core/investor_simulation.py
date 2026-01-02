from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ClaimAssumptionOutput(BaseModel):
    claims: Dict[str, str] = Field(
        description="Key claims extracted from the pitch."
    )
    assumptions: List[str] = Field(
        description="Assumptions implied by the pitch."
    )
    promises: List[str] = Field(
        description="Promises or forward-looking statements."
    )
    missing_evidence: List[str] = Field(
        description="Claims that lack supporting evidence."
    )
    evidence_present: Dict[str, bool] = Field(
        description="Whether evidence is present for each claim area."
    )


class InvestorSimulationOutput(BaseModel):
    scores: Dict[str, int] = Field(
        description="Rule-based scores by category (0-10)."
    )
    overall_score: int = Field(ge=0, le=100)
    verdict: str = Field(description="Investor ready / Not ready")
    hard_questions: List[str] = Field(description="Hard investor questions")
    fix_list: List[str] = Field(description="Actionable fixes to improve readiness")


class ClaimVsRealityOutput(BaseModel):
    problem_real: str
    tam_plausible: str
    differentiation_strong: str
    traction_believable: str
    notes: List[str]


def _score_from_evidence(present: bool, strong: bool = False) -> int:
    if present and strong:
        return 8
    if present:
        return 6
    return 3


def compute_investor_simulation(
    claim_assumptions: ClaimAssumptionOutput,
    market_research: Optional[dict] = None,
) -> InvestorSimulationOutput:
    evidence = claim_assumptions.evidence_present
    claims = claim_assumptions.claims

    has_problem = evidence.get("problem", False)
    has_market = evidence.get("market_size", False)
    has_diff = evidence.get("differentiation", False)
    has_traction = evidence.get("traction", False)
    has_model = evidence.get("business_model", False)

    market_support = bool(market_research and market_research.get("market_size_growth"))
    problem_score = _score_from_evidence(has_problem)
    market_score = _score_from_evidence(has_market, strong=market_support)
    diff_score = _score_from_evidence(has_diff)
    scalability_score = _score_from_evidence(has_model or has_market)

    missing_count = sum(1 for key in ("problem", "market_size", "differentiation", "traction") if not evidence.get(key, False))
    pitch_clarity = max(3, 9 - (missing_count * 2))

    scores = {
        "problem_severity": problem_score,
        "market_size_logic": market_score,
        "differentiation": diff_score,
        "scalability": scalability_score,
        "pitch_clarity": pitch_clarity,
    }

    average = sum(scores.values()) / len(scores)
    overall = int(round(average * 10))
    verdict = "Investor ready" if overall >= 70 else "Not ready"

    hard_questions: List[str] = []
    fix_list: List[str] = []

    if not has_problem:
        hard_questions.append("What specific pain point is most urgent, and for whom?")
        fix_list.append("Clarify the core problem and who feels it most.")
    if not has_market:
        hard_questions.append("What is the clearly defined TAM/SAM/SOM, and how did you calculate it?")
        fix_list.append("Add market sizing with sources and assumptions.")
    if not has_diff:
        hard_questions.append("Why will you win versus incumbents or substitutes?")
        fix_list.append("Provide clear differentiation with proof or defensibility.")
    if not has_traction:
        hard_questions.append("What evidence shows demand or adoption today?")
        fix_list.append("Add traction metrics, pilots, or LOIs.")
    if not has_model:
        hard_questions.append("How do you make money, and what are unit economics?")
        fix_list.append("Explain pricing, GTM, and unit economics.")

    if market_research is None:
        fix_list.append("Run market research to validate size, trends, and competitor pricing.")

    if "problem" in claims and claims.get("problem") == "Not stated":
        hard_questions.append("Can you state the problem in one crisp sentence?")

    return InvestorSimulationOutput(
        scores=scores,
        overall_score=overall,
        verdict=verdict,
        hard_questions=hard_questions[:8],
        fix_list=fix_list[:8],
    )


def compare_claims_to_market(
    claim_assumptions: ClaimAssumptionOutput,
    market_research: Optional[dict] = None,
) -> ClaimVsRealityOutput:
    evidence = claim_assumptions.evidence_present
    claims = claim_assumptions.claims
    notes: List[str] = []

    problem_real = "Yes" if evidence.get("problem") else "Weak"
    if problem_real == "Weak":
        notes.append("Problem statement lacks evidence or specificity.")

    tam_plausible = "Yes" if market_research and claims.get("market_size") not in (None, "", "Not stated") else "Weak"
    if tam_plausible == "Weak":
        notes.append("Market sizing is missing or unsupported by research.")

    differentiation_strong = "Yes" if evidence.get("differentiation") else "Weak"
    if differentiation_strong == "Weak":
        notes.append("Differentiation is not clearly supported.")

    traction_believable = "Yes" if evidence.get("traction") else "Weak"
    if traction_believable == "Weak":
        notes.append("Traction evidence is missing or unverified.")

    return ClaimVsRealityOutput(
        problem_real=problem_real,
        tam_plausible=tam_plausible,
        differentiation_strong=differentiation_strong,
        traction_believable=traction_believable,
        notes=notes,
    )


def build_skepticism_flags(claim_assumptions: ClaimAssumptionOutput) -> List[dict]:
    flags: List[dict] = []
    for key, value in claim_assumptions.claims.items():
        if value and value != "Not stated" and not claim_assumptions.evidence_present.get(key, False):
            flags.append(
                {
                    "statement": value,
                    "why_investors_doubt": "No supporting evidence in the pitch.",
                }
            )
    for promise in claim_assumptions.promises:
        flags.append(
            {
                "statement": promise,
                "why_investors_doubt": "Forward-looking claim without evidence.",
            }
        )
    return flags[:8]


def build_final_verdict(simulation: InvestorSimulationOutput) -> dict:
    if simulation.verdict == "Investor ready":
        summary = "Investors are likely to engage based on clarity and evidence."
        status = "Investor Ready"
    else:
        summary = "Investors may like the idea but will doubt evidence and traction."
        status = "Not Investor Ready"
    return {"status": status, "summary": summary}


def build_top_blockers(simulation: InvestorSimulationOutput) -> List[str]:
    return simulation.fix_list[:3]


def build_next_actions(simulation: InvestorSimulationOutput) -> List[str]:
    return simulation.fix_list[:5]


def build_likely_rejection(simulation: InvestorSimulationOutput) -> str:
    if simulation.verdict == "Investor ready":
        return "This is strong. We would like to learn more and validate traction."
    return "This is interesting, but we need proof that customers actually care."
