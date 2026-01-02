from typing import Dict
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from core.prompts import PITCH_PREPROCESS_PROMPT
from core.settings import settings


class PitchPreprocessOutput(BaseModel):
    normalized_text: str = Field(
        description="Normalized pitch text with fluff removed."
    )
    sections: Dict[str, str] = Field(
        description="Detected sections like problem, solution, market, traction, etc."
    )


def preprocess_pitch_text(source_text: str) -> PitchPreprocessOutput:
    model = ChatGoogleGenerativeAI(
        model=settings.TEXT_MODEL,
        temperature=0,
        google_api_key=settings.GOOGLE_API_KEY,
    )
    return model.with_structured_output(PitchPreprocessOutput).invoke(
        PITCH_PREPROCESS_PROMPT.format(source=source_text)
    )
