import logging
import warnings
from typing import Any, Dict
from uuid import uuid4
import base64

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_core._api import LangChainBetaWarning
from langgraph.graph.state import CompiledStateGraph
from fastapi import UploadFile, File
from agents.pitch_deck.agent import pitch_deck_agent
from agents.market_size.agent import market_research_agent
from agents.github_repo.agent import github_repo_agent
from agents.chatbot_qa.agent import qa_agent
from agents.supervisor.agent import supervisor_agent
from agents.video_pitch.agent import video_pitch_agent
from langgraph.pregel import Pregel
from langchain_core.messages import AIMessage
from core.settings import settings
from core.utils import (
    handle_market_size,
    handle_qa_input,
    handle_github_link,
    handle_video_pitch,
)
from core.schema import (
    ChatMessage,
    UserInput,
    VideoPitchInput,
    ExtractClaimsTextInput,
    ScoreStartupInput,
    InvestorSimulationInput,
)
from core.utils import (
    langchain_to_chat_message,
)
from jobs.storage import load_job, create_job
from jobs.tasks import (
    analyze_complete_job,
    analyze_pitch_deck_job,
    analyze_video_pitch_job,
    extract_claims_job,
)
from core.pitch_preprocess import preprocess_pitch_text
from core.pitch_claims import extract_claims_from_text
from core.investor_simulation import (
    compare_claims_to_market,
    compute_investor_simulation,
    build_skepticism_flags,
    build_final_verdict,
    build_top_blockers,
    build_next_actions,
    build_likely_rejection,
)
from core.investor_simulation import ClaimAssumptionOutput
from agents.video_pitch.helpers import analyze_transcript

# Suppress LangChain beta warnings
warnings.filterwarnings("ignore", category=LangChainBetaWarning)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="Pitch Deck Analysis API",
    description="API endpoints for pitch deck analysis, market research, and GitHub repository analysis",
    version="1.0.0"
)

# Configure CORS middleware
default_origins = [
    "*"
]
cors_origins = (
    [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
    if settings.CORS_ORIGINS
    else default_origins
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Retrieve the status of a job.
    """
    job = load_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/analyze-complete")
async def analyze_complete(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Performs a complete analysis using the supervisor agent, including:
    - Pitch deck analysis
    - Market research
    - GitHub repository analysis (if applicable)
    
    Args:
        file (UploadFile): PDF file containing the pitch deck
        
    Returns:
        SupervisorAnalysisResponse containing:
            - pitch_deck_summary: Detailed analysis of the pitch deck
            - pitch_deck_scorecard: Evaluation metrics for the pitch deck
            - market_analysis: Market research data
            - github_details: GitHub repository analysis (if applicable)
            - is_tech_company: Boolean indicating if it's a tech company
            - error: Error message if any step fails
            
    Raises:
        HTTPException: If processing fails or encounters an error
    """

    pdf_bytes = await file.read()
    job = create_job(str(uuid4()))
    analyze_complete_job.apply_async(
        args=[job.id, {"pdf_b64": base64.b64encode(pdf_bytes).decode("utf-8")}],
        task_id=job.id,
    )
    return {"job_id": job.id, "status": job.status}


@router.post("/analyze-pitch-deck")
async def analyze_pitch_deck(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Analyzes a pitch deck PDF and returns a scorecard and summary.
    
    Args:
        file (UploadFile): PDF file containing the pitch deck
        
    Returns:
        Dict containing:
            - scorecard: Evaluation metrics for the pitch deck
            - summary: Detailed analysis of the pitch deck
            
    Raises:
        HTTPException: If API usage limit is reached or processing fails
    """
    pdf_bytes = await file.read()
    job = create_job(str(uuid4()))
    analyze_pitch_deck_job.apply_async(
        args=[job.id, {"pdf_b64": base64.b64encode(pdf_bytes).decode("utf-8")}],
        task_id=job.id,
    )
    return {"job_id": job.id, "status": job.status}

@router.post("/analyze-market-size")
async def analyze_market_size(company_overview: dict) -> Dict[str, Any]:
    """
    Analyzes market size and competitors based on company overview.
    
    Args:
        company_overview (dict): Company information and business details
        
    Returns:
        Dict containing market research data:
            - sector: Industry sector
            - market_size: Total addressable market size
            - competitors: List of main competitors
            
    Raises:
        HTTPException: If API usage limit is reached or processing fails
    """
    try:
        kwargs, run_id = await handle_market_size(company_overview)
        market_analysis = market_research_agent.invoke(**kwargs)
        return {
            'market_research': market_analysis.get('market_research'),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Usage limit reached. Please try again in 30 seconds.",
        )

@router.post("/analyze-github-repository")
async def analyze_github_repository(repository_url: str) -> Dict[str, Any]:
    """
    Analyzes a GitHub repository and returns relevant information.
    
    Args:
        repository_url (str): URL of the GitHub repository
        
    Returns:
        Dict containing repository analysis data
        
    Raises:
        HTTPException: If API usage limit is reached or processing fails
    """
    try:
        kwargs, run_id = await handle_github_link(repository_url)
        repository_analysis = github_repo_agent.invoke(**kwargs)
        return {
            'github_analysis': repository_analysis['repo'],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Usage limit reached. Please try again in 30 seconds.",
        )

@router.post("/chat-assistant")
async def process_chat_query(user_input: UserInput) -> ChatMessage:
    """
    Processes user queries using a conversational AI assistant.
    
    This endpoint handles multi-turn conversations and maintains context using thread_id.
    Each interaction is tracked with a unique run_id for feedback and monitoring.
    
    Args:
        user_input (UserInput): User's message and optional thread/context information
        
    Returns:
        ChatMessage: AI assistant's response
        
    Raises:
        HTTPException: If processing fails or encounters an error
    """
    agent: Pregel = qa_agent
    kwargs, run_id = await handle_qa_input(user_input, agent)
    
    try:
        response_events: list[tuple[str, Any]] = await agent.ainvoke(
            **kwargs, 
            stream_mode=["updates", "values"]
        )
        
        response_type, response = response_events[-1]
        
        if response_type == "values":
            # Normal response - agent completed successfully
            output = langchain_to_chat_message(response["messages"][-1])
        elif response_type == "updates" and "__interrupt__" in response:
            # Interrupt occurred - return first interrupt as AIMessage
            output = langchain_to_chat_message(
                AIMessage(content=response["__interrupt__"][0].value)
            )
        else:
            raise ValueError(f"Unexpected response type: {response_type}")

        output.run_id = str(run_id)
        return output
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while processing your request"
        )


@router.post("/analyze-video-pitch")
async def analyze_video_pitch(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Analyzes a pitch video/audio file and returns an investor-style analysis.

    Args:
        file (UploadFile): Video/audio file containing the pitch

    Returns:
        Dict containing:
            - transcript: Transcribed text from the pitch
            - analysis: Investor analysis with idea filter, hard questions, and scores

    Raises:
        HTTPException: If file type is unsupported or processing fails
    """
    if not file.content_type or not file.content_type.startswith(("video/", "audio/")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a video or audio file.",
        )

    file_bytes = await file.read()
    job = create_job(str(uuid4()))
    analyze_video_pitch_job.apply_async(
        args=[
            job.id,
            {
                "file_b64": base64.b64encode(file_bytes).decode("utf-8"),
                "filename": file.filename or "pitch",
                "content_type": file.content_type,
            },
        ],
        task_id=job.id,
    )
    return {"job_id": job.id, "status": job.status}


@router.post("/analyze-video-pitch-text")
async def analyze_video_pitch_text(video_input: VideoPitchInput) -> Dict[str, Any]:
    """
    Analyzes a pitch video transcript and returns an investor-style analysis.

    Args:
        video_input (VideoPitchInput): Transcript of the pitch video/audio

    Returns:
        Dict containing:
            - transcript: Pitch transcript
            - analysis: Investor analysis with idea filter, hard questions, and scores

    Raises:
        HTTPException: If processing fails
    """
    try:
        kwargs, run_id = await handle_video_pitch(video_input.transcript)
        result = video_pitch_agent.invoke(**kwargs)

        if "analysis" not in result:
            raise HTTPException(
                status_code=500,
                detail="Usage limit reached. Please try again in 30 seconds.",
            )

        return {
            "transcript": video_input.transcript,
            "analysis": result["analysis"],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Usage limit reached. Please try again in 30 seconds.",
        )


@router.post("/extract-claims")
async def extract_claims(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Extracts claims and assumptions from a pitch file (video/audio/pdf).
    """
    if not file.content_type:
        raise HTTPException(status_code=400, detail="Missing content type.")

    file_bytes = await file.read()
    job = create_job(str(uuid4()))
    extract_claims_job.apply_async(
        args=[
            job.id,
            {
                "file_b64": base64.b64encode(file_bytes).decode("utf-8"),
                "filename": file.filename or "pitch",
                "content_type": file.content_type,
            },
        ],
        task_id=job.id,
    )
    return {"job_id": job.id, "status": job.status}


@router.post("/extract-claims-text")
async def extract_claims_text(payload: ExtractClaimsTextInput) -> Dict[str, Any]:
    """
    Extracts claims and assumptions from raw pitch text.
    """
    preprocess = preprocess_pitch_text(payload.text)
    claims = extract_claims_from_text(preprocess.normalized_text)
    return {
        "source_type": payload.source_type or "text",
        "normalized_text": preprocess.normalized_text,
        "sections": preprocess.sections,
        "claim_assumptions": claims.model_dump(),
    }


@router.post("/score-startup")
async def score_startup(payload: ScoreStartupInput) -> Dict[str, Any]:
    """
    Compares claims to market reality and returns scores + verdict.
    """
    if not payload.claim_assumptions:
        raise HTTPException(
            status_code=400,
            detail="claim_assumptions is required. Call /extract-claims first.",
        )
    claims = ClaimAssumptionOutput.model_validate(payload.claim_assumptions)
    comparison = compare_claims_to_market(claims, payload.market_research)
    simulation = compute_investor_simulation(claims, payload.market_research)
    skepticism_flags = build_skepticism_flags(claims)
    final_verdict = build_final_verdict(simulation)

    return {
        "claim_vs_reality": comparison.model_dump(),
        "investor_simulation": simulation.model_dump(),
        "skepticism_flags": skepticism_flags,
        "final_verdict": final_verdict,
        "top_blockers": build_top_blockers(simulation),
        "next_actions": build_next_actions(simulation),
        "likely_rejection": build_likely_rejection(simulation),
    }


@router.post("/investor-simulation")
async def investor_simulation(payload: InvestorSimulationInput) -> Dict[str, Any]:
    """
    Returns rule-based investor simulation output from claims.
    """
    if not payload.claim_assumptions:
        raise HTTPException(
            status_code=400,
            detail="claim_assumptions is required. Call /extract-claims first.",
        )
    claims = ClaimAssumptionOutput.model_validate(payload.claim_assumptions)
    simulation = compute_investor_simulation(claims, payload.market_research)
    return simulation.model_dump()


@router.post("/skepticism-flags")
async def skepticism_flags(payload: InvestorSimulationInput) -> Dict[str, Any]:
    """
    Returns skepticism flags based on unsupported claims.
    """
    if not payload.claim_assumptions:
        raise HTTPException(
            status_code=400,
            detail="claim_assumptions is required. Call /extract-claims first.",
        )
    claims = ClaimAssumptionOutput.model_validate(payload.claim_assumptions)
    flags = build_skepticism_flags(claims)
    return {"skepticism_flags": flags}


@router.post("/final-verdict")
async def final_verdict(payload: InvestorSimulationInput) -> Dict[str, Any]:
    """
    Returns a final verdict, blockers, and actions from claims.
    """
    if not payload.claim_assumptions:
        raise HTTPException(
            status_code=400,
            detail="claim_assumptions is required. Call /extract-claims first.",
        )
    claims = ClaimAssumptionOutput.model_validate(payload.claim_assumptions)
    simulation = compute_investor_simulation(claims, payload.market_research)
    return {
        "final_verdict": build_final_verdict(simulation),
        "top_blockers": build_top_blockers(simulation),
        "next_actions": build_next_actions(simulation),
        "likely_rejection": build_likely_rejection(simulation),
    }


@router.post("/investor-personas")
async def investor_personas(video_input: VideoPitchInput) -> Dict[str, Any]:
    """
    Returns investor personas and hard questions for a pitch transcript.
    """
    try:
        if not video_input.transcript:
            raise HTTPException(
                status_code=400,
                detail="transcript is required.",
            )
        analysis = analyze_transcript(video_input.transcript)
        return {"investor_modes": analysis.investor_modes.model_dump()}
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Investor persona analysis failed. Please try again.",
        )

# Include router in the FastAPI application
app.include_router(router)
