"""Supervisor agent for coordinating and monitoring other agents."""

import json
from datetime import datetime
import os
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, AnyMessage, SystemMessage, ToolMessage
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

    def execute(self, state: SupervisorWorkflowState) -> SupervisorWorkflowState:
        """Execute supervision logic and return updated state"""
        logger.get_logger()._write_log(
            "INFO", "supervisor_agent", f"Execute the supervisor agent"
        )
        history_messages = state.get("messages", [])
        logger.get_logger()._write_log(
            "INFO",
            "supervisor_agent",
            f"History messages length: {len(history_messages)}",
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
            logger.get_logger()._write_log(
                "INFO", "supervisor_agent", "\n" + msg.pretty_repr()
            )

        # check if all tasks are completed
        plan_phase_id = state.get("phase_id", "")
        if not plan_phase_id or os.path.exists("todo.json") is False:
            logger.get_logger()._write_log(
                "ERROR",
                "supervisor_agent",
                "No phase_id found in state, cannot proceed with task processing.",
            )
            return SupervisorWorkflowState(
                status=SupervisorWorkflowStatus.ERROR,
                messages=[AIMessage(content="No phase_id found in state.")],
            )

        todo_file_content = ""
        with open("todo.json", "r") as f:
            todo_file_content = f.read()
        todo_data = json.loads(todo_file_content)
        current_phase = next(
            (phase for phase in todo_data if phase["phase_id"] == plan_phase_id), None
        )
        if not current_phase:
            logger.get_logger()._write_log(
                "ERROR",
                "supervisor_agent",
                f"Phase {plan_phase_id} not found in todo.json",
            )
            return SupervisorWorkflowState(
                status=SupervisorWorkflowStatus.ERROR,
                messages=[
                    AIMessage(content=f"Phase {plan_phase_id} not found in todo.json")
                ],
            )
        if current_phase["status"] == "completed":
            logger.get_logger()._write_log(
                "INFO",
                "supervisor_agent",
                f"Phase {plan_phase_id} already completed, updating status",
            )
            return SupervisorWorkflowState(
                status=SupervisorWorkflowStatus.COMPLETED,
                messages=[
                    AIMessage(content=f"Phase {plan_phase_id} is already completed.")
                ],
            )

        return SupervisorWorkflowState(
            status=SupervisorWorkflowStatus.TASK_PROCESSING,
            messages=response["messages"],
        )
