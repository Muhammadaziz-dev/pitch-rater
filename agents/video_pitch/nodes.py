from typing import Union, Literal

from agents.video_pitch.helpers import analyze_transcript, extract_claims_from_text
from agents.video_pitch.models import GraphState, VideoPitchAnalysis
from core.investor_simulation import compute_investor_simulation


def analyze_video_pitch(state: GraphState) -> Union[GraphState, dict]:
    try:
        analysis = analyze_transcript(state["transcript"])
        claims = extract_claims_from_text(state["transcript"])
        analysis.claim_assumptions = claims
        analysis.investor_simulation = compute_investor_simulation(claims)
        score = _calculate_filter_score(analysis)
        analysis.filter_ai_score = score
        analysis.overall_score = score
        analysis.investor_ready_status = "Investor ready" if score >= 70 else "Not ready"
        state["analysis"] = analysis.model_dump()
        return state
    except Exception as exc:
        return {"error": f"Video pitch analysis failed: {exc}"}


def _calculate_filter_score(analysis: VideoPitchAnalysis) -> int:
    ratings = analysis.ratings
    scores = [
        ratings.problem_severity,
        ratings.market_size_logic,
        ratings.differentiation,
        ratings.scalability,
        ratings.pitch_clarity,
    ]
    average = sum(scores) / len(scores)
    return int(round(average * 10))


def should_continue(state: Union[GraphState, dict]) -> Union[Literal["continue"], Literal["end"]]:
    if isinstance(state, dict) and "error" in state:
        return "end"
    return "continue"


def end_state(state: Union[GraphState, dict]) -> Union[GraphState, dict]:
    return state
