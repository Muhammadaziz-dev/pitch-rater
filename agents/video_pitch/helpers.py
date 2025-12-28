from langchain_openai import ChatOpenAI
from core.settings import settings
from core.prompts import VIDEO_PITCH_ANALYSIS_PROMPT
from agents.video_pitch.models import VideoPitchAnalysis

language_model = ChatOpenAI(model=settings.TEXT_MODEL, temperature=0)


def analyze_transcript(transcript: str) -> VideoPitchAnalysis:
    return language_model.with_structured_output(VideoPitchAnalysis).invoke(
        VIDEO_PITCH_ANALYSIS_PROMPT.format(transcript=transcript)
    )
