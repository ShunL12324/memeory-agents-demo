"""State definitions for the multi-agent workflow system."""

from enum import Enum
from typing import Annotated, TypedDict, List, Dict, Any
from langchain_core.messages import AnyMessage
import operator


class MainWorkflowStatus(Enum):
    """Status values for the main workflow (AgentState)"""
    INITIAL = "initial"
    PLANNING_COMPLETED = "planning_completed",
    PHASE_COMPLETED = "phase_completed",
    COMPLETED = "completed",
    ERROR = "error"


class SupervisorWorkflowStatus(Enum):
    """Status values for the supervisor subgraph (SupervisorSubGraphState)"""
    PROCESSING = "processing"
    TASK_PROCESSING = "task_processing"
    TASK_COMPLETED = "task_completed"
    COMPLETED = "completed"
    ERROR = "error"

class MainWorkflowState(TypedDict):
    """State shared between agents - minimal structure"""
    origin_user_request: str
    plan_list: List[Dict[str, Any]]
    current_plan_index: int
    status: MainWorkflowStatus
    messages: Annotated[List[AnyMessage], operator.add]  # Unified message storage with reducer

class SupervisorWorkflowState(TypedDict):
    """State shared between agents - minimal structure"""
    phase_id: str
    origin_user_request: str
    status: SupervisorWorkflowStatus
    messages: Annotated[List[AnyMessage], operator.add]