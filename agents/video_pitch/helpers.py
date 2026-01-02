from langchain_google_genai import ChatGoogleGenerativeAI
from core.settings import settings
from core.prompts import VIDEO_PITCH_ANALYSIS_PROMPT, CLAIM_ASSUMPTION_PROMPT
from agents.video_pitch.models import VideoPitchAnalysis
from core.investor_simulation import ClaimAssumptionOutput

language_model = ChatGoogleGenerativeAI(
    model=settings.TEXT_MODEL,
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY,
)


def analyze_transcript(transcript: str) -> VideoPitchAnalysis:
    return language_model.with_structured_output(VideoPitchAnalysis).invoke(
        VIDEO_PITCH_ANALYSIS_PROMPT.format(transcript=transcript)
    )


def extract_claims_from_text(source_text: str) -> ClaimAssumptionOutput:
    return language_model.with_structured_output(ClaimAssumptionOutput).invoke(
        CLAIM_ASSUMPTION_PROMPT.format(source=source_text)
    )
