from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.graph import END
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing_extensions import Annotated, Literal

from src import logger
from src.models import MainGraphState


@tool(
    "hand_off_to_supervisor_graph",
    description="Hand off workflow to supervisor subgraph",
)
def hand_off_to_supervisor_graph(
    state: Annotated[MainGraphState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
    assigned_phase_info: str,
) -> Command[Literal["supervisor_subgraph", "planner"]]:
    """Handoff to the supervisor agent."""
    history = state.get("messages", [])
    logger.get_logger().tool_call(
        "planner",
        "hand_off_to_supervisor_graph",
        {"state_keys": str(state.keys())},
        "Successfully handed off to supervisor subgraph",
        print_to_console=False,  # 避免干扰流式输出
    )
    tool_message = ToolMessage(
        content="Successfully handed off to supervisor subgraph.",
        tool_call_id=tool_call_id,
        tool_name="hand_off_to_supervisor_graph",
    )
    return Command(
        goto="supervisor_subgraph",
        update={
            **state,
            "messages": list(history) + [tool_message],
            "current_phase_info": assigned_phase_info,
        },
        graph=Command.PARENT,
    )


@tool(
    "end_workflow",
    description="Navigate to end of workflow",
)
def end_workflow(
    state: Annotated[MainGraphState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Navigate to end of workflow."""
    history = state.get("messages", [])
    logger.get_logger().tool_call(
        "planner",
        "end_workflow",
        {"state_keys": list(state.keys())},
        "Workflow ended successfully",
        True,
        print_to_console=False,  # Avoid interfering with streaming output
    )
    tool_message = ToolMessage(
        content="Workflow ended successfully",
        tool_call_id=tool_call_id,
        tool_name="end_workflow",
    )
    return Command(
        goto=END,
        update={
            **state,
            "messages": list(history) + [tool_message],
        },
        graph=Command.PARENT,
    )


PLANNER_TOOLS = [hand_off_to_supervisor_graph, end_workflow]
