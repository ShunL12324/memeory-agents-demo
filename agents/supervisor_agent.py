"""Supervisor agent for coordinating and monitoring other agents."""

import json
from datetime import datetime
import os
from typing import Any, Dict, List

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    SystemMessage,
    ToolMessage,
    HumanMessage,
)
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent

import logger
from models import SupervisorWorkflowState, SupervisorWorkflowStatus
from prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from tools import file_tools

from .base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """Supervisor agent that coordinates workflow execution"""

    def __init__(self):
        super().__init__("supervisor", tools=file_tools)
        self.agents = {}

    def register_agent(self, agent):
        """Register an agent with the supervisor"""
        self.agents[agent.name] = agent

    def _check_if_all_tasks_completed(self, phase_id: str) -> bool:
        """Check if all tasks in the current phase are completed"""
        todo_file_content = ""
        with open("todo.md", "r") as f:
            todo_file_content = f.read()
        system_prompt = SystemMessage(
            content="""
            你需要根据传入的phase_id以及文件内容检查当前阶段的任务是否全部完成。
            如果是，则返回"True"，否则返回"False"。
            你的返回内容只能是"True"或"False"，不要包含其他任何内容。
            """
        )
        human_msg = HumanMessage(content=f"Phase ID: {phase_id}\n\n{todo_file_content}")
        response = self.llm.invoke([system_prompt, human_msg])
        text_content = self._extract_text_content(response)
        if "true" in text_content.strip().lower():
            return True

        return False

    def execute(self, state: SupervisorWorkflowState) -> SupervisorWorkflowState:
        """Execute supervision logic and return updated state"""
        logger.get_logger()._write_log(
            "INFO",
            "supervisor_agent",
            f"开始执行监督者智能体，状态: {state.get('status', 'unknown')}",
        )
        history_messages = state.get("messages", [])
        logger.get_logger()._write_log(
            "INFO",
            "supervisor_agent",
            f"获取到 {len(history_messages)} 条历史消息",
        )

        current_plan = history_messages[0].content

        self.react_agent = create_react_agent(
            model=self.llm,
            prompt=SUPERVISOR_SYSTEM_PROMPT.format(current_plan=current_plan),
            tools=file_tools,
        )

        # list of messages
        response: List[AnyMessage] = self.react_agent.invoke(
            {"messages": history_messages}
        )

        for msg in response["messages"]:
            if msg not in history_messages:
                # Log the message content
                logger.get_logger()._write_log(
                    "INFO", "supervisor_agent", f"收到回复消息\n\n {msg.pretty_repr()}"
                )

        # check if all tasks are completed
        plan_phase_id = state.get("phase_id", "")
        if not plan_phase_id or os.path.exists("todo.md") is False:
            logger.get_logger()._write_log(
                "ERROR",
                "supervisor_agent",
                "状态中缺少阶段ID，无法继续任务处理",
            )
            return SupervisorWorkflowState(
                status=SupervisorWorkflowStatus.ERROR,
                messages=[AIMessage(content="No phase_id found in state.")],
            )

        is_phase_completed = self._check_if_all_tasks_completed(plan_phase_id)
        if is_phase_completed:
            logger.get_logger()._write_log(
                "INFO",
                "supervisor_agent",
                f"阶段 {plan_phase_id} 已完成，更新状态",
            )
            return SupervisorWorkflowState(
                status=SupervisorWorkflowStatus.COMPLETED,
                messages=[
                    AIMessage(content=f"Phase {plan_phase_id} is already completed.")
                ],
            )

        return SupervisorWorkflowState(
            status=SupervisorWorkflowStatus.TASK_PROCESSING,
            messages=[
                msg for msg in response["messages"] if msg not in history_messages
            ],
        )
