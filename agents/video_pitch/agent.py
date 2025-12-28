from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph

from agents.video_pitch.models import GraphState
from agents.video_pitch.nodes import analyze_video_pitch, end_state, should_continue

graph = StateGraph(GraphState)

graph.add_node("analyze_video_pitch", RunnableLambda(analyze_video_pitch))
graph.add_node("end", RunnableLambda(end_state))

graph.set_entry_point("analyze_video_pitch")

graph.add_conditional_edges(
    "analyze_video_pitch",
    should_continue,
    {
        "continue": "end",
        "end": "end",
    },
)

graph.set_finish_point("end")

video_pitch_agent = graph.compile(checkpointer=MemorySaver())
