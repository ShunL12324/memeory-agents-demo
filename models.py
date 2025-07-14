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
    origin_user_request: str # 原始用户请求
    plan_list: List[Dict[str, Any]] # 计划列表，包含各个阶段的详细信息，但是没有具体的task信息
    current_plan_index: int # 当前执行的计划索引
    status: MainWorkflowStatus # 状态标记
    messages: Annotated[List[AnyMessage], operator.add]  # 上下文消息，包含planner自己的消息和子图最终返回消息（子图的中间结果不保存在这里）

class SupervisorWorkflowState(TypedDict):
    """State shared between agents - minimal structure"""
    phase_id: str # 当前执行的这个phase的id，用于在memory文件里检查该phase是否完成
    origin_user_request: str # 原始用户请求，目前没用到
    status: SupervisorWorkflowStatus # 状态标记
    messages: Annotated[List[AnyMessage], operator.add] # 上下文消息，第一个是planner下发的phase信息，后续是执行智能体的反馈消息