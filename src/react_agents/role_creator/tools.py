from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command
from typing_extensions import Annotated, Literal

from src import logger
from src.models import SupervisorSubGraphState


@tool("hand_off_to_supervisor", description="Hand off workflow to supervisor agent")
def hand_off_to_supervisor(
    state: Annotated[SupervisorSubGraphState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command[Literal["supervisor", "planner"]]:
    """Hand off workflow to the supervisor agent."""
    history = state.get("messages", [])
    logger.get_logger().tool_call(
        "role_creator",
        "hand_off_to_supervisor",
        {"state_keys": list(state.keys())},
        "Successfully handed off to supervisor agent",
        True,
        print_to_console=False  # 避免干扰流式输出
    )
    tool_message = ToolMessage(
        content="Successfully handed off to supervisor agent.",
        tool_call_id=tool_call_id,
        tool_name="hand_off_to_supervisor",
    )

    return Command(
        goto="supervisor",
        update={**state, "messages": list(history) + [tool_message]},
        graph=Command.PARENT,
    )


ROLE_CREATOR_TOOLS = [hand_off_to_supervisor]
