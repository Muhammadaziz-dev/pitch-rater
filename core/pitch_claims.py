from langchain_google_genai import ChatGoogleGenerativeAI
from core.prompts import CLAIM_ASSUMPTION_PROMPT
from core.settings import settings
from core.investor_simulation import ClaimAssumptionOutput


def extract_claims_from_text(source_text: str) -> ClaimAssumptionOutput:
    model = ChatGoogleGenerativeAI(
        model=settings.TEXT_MODEL,
        temperature=0,
        google_api_key=settings.GOOGLE_API_KEY,
    )
    return model.with_structured_output(ClaimAssumptionOutput).invoke(
        CLAIM_ASSUMPTION_PROMPT.format(source=source_text)
    )
