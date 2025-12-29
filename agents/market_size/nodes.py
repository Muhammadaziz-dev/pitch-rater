from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_google_genai import ChatGoogleGenerativeAI
from core.prompts import MARKET_RESEARCH_PROMPT
from core.settings import settings
from agents.market_size.models import (
    GraphState,
    MarketResearchResponse    
)

language_model = ChatGoogleGenerativeAI(
    model=settings.MARKET_MODEL or settings.TEXT_MODEL,
    temperature=0,
    google_api_key=settings.GOOGLE_API_KEY,
)
search_tool = TavilySearchResults(k=3)
tools = [search_tool]
language_model = language_model.bind_tools(tools).with_structured_output(MarketResearchResponse)  

def market_research(state: GraphState) -> GraphState:
    try:
        print("--- Step 1: Market Research ---")
        response = language_model.invoke(
            MARKET_RESEARCH_PROMPT + str(state["input_overview"])
        )
        
        state["market_research"] = response.model_dump()
        return state
    except Exception as e:
        print(f"Error in market research: {str(e)}")
        state["error"] = f"Market Research failed: {str(e)}"
        return state

def end_state(state: GraphState) -> GraphState:
    """Final node that returns the state as is"""
    return state
