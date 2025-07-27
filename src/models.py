"""State definitions for the multi-agent workflow system."""

from langgraph.prebuilt.chat_agent_executor import AgentState
from typing_extensions import NotRequired


class MainGraphState(AgentState):
    """主图状态"""

    origin_user_request: str  # 原始用户请求
    current_phase_info: NotRequired[str]


class SupervisorSubGraphState(AgentState):
    """Supervisor 子图状态"""

    origin_user_request: str  # 原始用户请求
