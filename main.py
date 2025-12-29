import logging
import warnings
from typing import Any, Dict

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
from core.utils import (
    handle_input_slides, 
    handle_market_size,
    handle_complete,
    getbase64, 
    convert_pdf_to_images, 
    handle_qa_input, 
    handle_github_link,
    handle_video_pitch,
    transcribe_audio_bytes
)
from core.schema import (
    ChatMessage,
    UserInput,
    VideoPitchInput,
)
from core.utils import (
    langchain_to_chat_message,
)

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
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

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

    try:
        agent: CompiledStateGraph = supervisor_agent
        encoded_images = []
        pdf_bytes = await file.read()
        images = convert_pdf_to_images(pdf_bytes)

        for idx, image in enumerate(images):
            encoded_images.append({'imageByte': getbase64(image)})

        kwargs, run_id = await handle_complete(encoded_images)
        result = supervisor_agent.invoke(**kwargs)
        
        out = {
            'summary': result['summary'],
            'scorecard': result['scorecard'],
            'overall_score': result.get('overall_score', 0),
            'market_research': result.get('market_research')
        }
        if result['github_url']:
            out['github_details'] = result['github_details']
        return out
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Usage limit reached. Please try again in 30 seconds.",
        )


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
    agent: CompiledStateGraph = pitch_deck_agent
    encoded_images = []
    pdf_bytes = await file.read()
    images = convert_pdf_to_images(pdf_bytes)

    for idx, image in enumerate(images):
        encoded_images.append({'imageByte': getbase64(image)})

    kwargs, run_id = await handle_input_slides(encoded_images)
    response_events = await agent.ainvoke(**kwargs, stream_mode=["updates", "values"])
    response_type, response = response_events[-1]
    
    if (response_type == "values") and ('scorecard' in response) and ('summary' in response):
        return {
            'scorecard': response['scorecard'],
            'summary': response['summary'],
            'overall_score': response.get('overall_score', 0),
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Usage limit reached. Please try again in 30 seconds.",
        )

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
    try:
        if not file.content_type or not file.content_type.startswith(("video/", "audio/")):
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Please upload a video or audio file.",
            )

        file_bytes = await file.read()
        transcript = transcribe_audio_bytes(
            file_bytes,
            file.filename or "pitch",
            file.content_type,
        )
        if not transcript:
            raise HTTPException(
                status_code=422,
                detail="Transcription failed to extract text.",
            )

        kwargs, run_id = await handle_video_pitch(transcript)
        result = video_pitch_agent.invoke(**kwargs)

        if "analysis" not in result:
            raise HTTPException(
                status_code=500,
                detail="Usage limit reached. Please try again in 30 seconds.",
            )

        return {
            "transcript": transcript,
            "analysis": result["analysis"],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Usage limit reached. Please try again in 30 seconds.",
        )


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

# Include router in the FastAPI application
app.include_router(router)
