"""Supervisor agent for coordinating and monitoring other agents."""

import json
from typing import Dict, Any, List

import logger
from tools import file_tools
from models import SupervisorWorkflowStatus
from .base_agent import BaseAgent
from prompts.supervisor_prompts import SUPERVISOR_SYSTEM_PROMPT
from models import SupervisorWorkflowState
from datetime import datetime
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage, AnyMessage
from langgraph.prebuilt import create_react_agent


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

        return SupervisorWorkflowState(
            status=SupervisorWorkflowStatus.TASK_PROCESSING,
            messages=response["messages"],
        )
