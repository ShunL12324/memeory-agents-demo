import json
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from agents import PlannerAgent, SupervisorAgent, RoleCreatorAgent
import logger
from models import (
    MainWorkflowStatus,
    SubWorkflowStatus,
    AgentState,
    SupervisorSubGraphState,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from datetime import datetime
from tools import all_tools

# Supervisor subgraph
class SupervisorAgentWorkflow:

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()
        self.role_creator = RoleCreatorAgent()

        self.supervisor.register_agent(self.role_creator)

        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""

        def supervisor_node(state: SupervisorSubGraphState) -> SupervisorSubGraphState:
            return self.supervisor.execute(state)

        def supervisor_tool_node(
            state: SupervisorSubGraphState,
        ) -> SupervisorSubGraphState:
            tools_by_name = {tool.name: tool for tool in all_tools}
            messages = state.get("messages", [])
            if len(messages) == 0:
                return state
            else:
                message = messages[-1]
                if not message.tool_calls or len(message.tool_calls) == 0:
                    return state
                else:
                    tool_call = message.tool_calls[0]
                    tool_result = tools_by_name[tool_call.get("name", "")].invoke(tool_call.get("args", {}))
                    tool_msg = ToolMessage(
                        content=json.dumps(tool_result, indent=4),
                        role="supervisor",
                        agent="supervisor",
                        tool_call_id=tool_call.get("id", ""),   
                        tool_name=tool_call.get("name", ""),
                        timestamp=datetime.now().isoformat(),
                    )
                    return SupervisorSubGraphState(
                        status=SubWorkflowStatus.PROCESSING,
                        messages=[tool_msg],
                    )

        def role_creator_node(
            state: SupervisorSubGraphState,
        ) -> SupervisorSubGraphState:
            return self.role_creator.execute(state)

        def routing_logic(state: SupervisorSubGraphState) -> str:
            status = state.get("status", "")

            if status == SubWorkflowStatus.PROCESSING:
                return "supervisor"
            elif status == SubWorkflowStatus.TOOL_CALLING:
                return "supervisor_tool"
            elif status == SubWorkflowStatus.TASK_PROCESSING:
                return "role_creator"
            elif status == SubWorkflowStatus.TASK_COMPLETED:
                return "supervisor"
            elif status == SubWorkflowStatus.ERROR:
                return "supervisor"
            elif status == SubWorkflowStatus.COMPLETED:
                return END

        # Build the workflow graph
        workflow = StateGraph(SupervisorSubGraphState)

        # Add nodes
        workflow.add_node("supervisor", supervisor_node)
        workflow.add_node("supervisor_tool", supervisor_tool_node)  # for ReAct agent
        workflow.add_node("role_creator", role_creator_node)

        # Set entry point
        workflow.set_entry_point("supervisor")

        # Add conditional edges
        workflow.add_conditional_edges(
            "supervisor",
            routing_logic,
            {
                "supervisor": "supervisor",
                "supervisor_tool": "supervisor_tool",
                "role_creator": "role_creator",
                END: END,
            },
        )

        # supervisor_tool always returns to supervisor (ReAct pattern)
        workflow.add_edge("supervisor_tool", "supervisor")

        workflow.add_conditional_edges(
            "role_creator", routing_logic, {"supervisor": "supervisor", END: END}
        )

        return workflow.compile()

    def execute(self, state: AgentState) -> AgentState:
        """Execute the supervisor subgraph"""
        # Convert AgentState to SupervisorSubGraphState
        plan_list = state.get("plan_list", [])
        if not plan_list or len(plan_list) == 0:
            return AgentState(
                origin_user_request=state.get("origin_user_request", ""),
                plan_list=state.get("plan_list", []),
                current_plan_index=state.get("current_plan_index", 0),
                status=MainWorkflowStatus.ERROR,
                messages=[],
            )

        plan = plan_list[state.get("current_plan_index", 0)]
        logger.get_logger()._write_log(
            "INFO", "supervisor_subgraph", f"Start to handle plan: {plan}"
        )
        planner_message = HumanMessage(
            content=f"The current plan is: {plan}",
            role="planner",
            agent="planner",
            timestamp=datetime.now().isoformat(),
        )
        logger.get_logger()._write_log(
            "INFO", "supervisor_subgraph", f"Planner message: {planner_message}"
        )

        supervisor_subgraph_state = SupervisorSubGraphState(
            origin_user_request=state.get("origin_user_request", ""),
            status=SubWorkflowStatus.PROCESSING,
            messages=[planner_message],
        )

        subgraph_state = self.workflow.invoke(supervisor_subgraph_state)

        # update the state depends on the subgrah state
        # if state is error update the main workflow state to error
        # if state is workflow_completed
        # update the main workflow status completed
        subgraph_status = subgraph_state.get("status", "")
        if subgraph_status == SubWorkflowStatus.ERROR:
            logger.get_logger()._write_log(
                "ERROR", "supervisor_agent", f"Error in supervisor subgraph"
            )
            return AgentState(
                origin_user_request=state.get("origin_user_request", ""),
                plan_list=state.get("plan_list", []),
                current_plan_index=state.get("current_plan_index", 0),
                status=MainWorkflowStatus.ERROR,
                messages=[],
            )
        else:
            logger.get_logger()._write_log(
                "INFO",
                "supervisor_agent",
                f"Get the next plan index: {state.get('current_plan_index', 0) + 1}",
            )
            next_plan_index = state.get("current_plan_index", 0) + 1
            if next_plan_index >= len(state.get("plan_list", [])):
                return AgentState(
                    origin_user_request=state.get("origin_user_request", ""),
                    plan_list=state.get("plan_list", []),
                    current_plan_index=state.get(
                        "current_plan_index", len(state.get("plan_list", [])) - 1
                    ),
                    status=MainWorkflowStatus.COMPLETED,
                    messages=[
                        AIMessage(
                            content="The workflow is completed",
                            role="supervisor",
                            agent="supervisor",
                            timestamp=datetime.now().isoformat(),
                        )
                    ],
                )
            else:
                return AgentState(
                    origin_user_request=state.get("origin_user_request", ""),
                    plan_list=state.get("plan_list", []),
                    current_plan_index=next_plan_index,
                    status=MainWorkflowStatus.PHASE_COMPLETED,
                    messages=[
                        AIMessage(
                            content="The phase is completed",
                            role="supervisor",
                            agent="supervisor",
                            timestamp=datetime.now().isoformat(),
                        )
                    ],
                )


class MultiAgentWorkflow:
    """LangGraph workflow orchestrating multiple agents"""

    def __init__(self):
        self.planner = PlannerAgent()
        self.supervisor_subgraph = SupervisorAgentWorkflow()

        # Create the workflow graph
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""

        def planning_node(state: AgentState) -> AgentState:
            """Planning node - creates high-level phases
            we will update the state with the planning results
            and then pass it to the supervisor subgraph"""
            return self.planner.execute(state)

        def supervisor_subgraph_node(state: AgentState) -> AgentState:
            """Supervision node - manages phases and coordinates execution"""
            logger.get_logger()._write_log(
                "INFO", "supervisor_agent", f"Execute the supervisor subgraph"
            )
            return self.supervisor_subgraph.execute(state)

        def routing_logic(state: AgentState) -> str:
            """Determine next node based on current state"""
            status = state.get("status", "")

            if status == MainWorkflowStatus.INITIAL:
                return "planning"
            elif status == MainWorkflowStatus.PLANNING_COMPLETED:
                return "supervisor_subgraph"
            elif status == MainWorkflowStatus.PHASE_COMPLETED:
                return "supervisor_subgraph"
            elif status == MainWorkflowStatus.COMPLETED:
                return END
            else:
                return END

        # Build the workflow graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("planning", planning_node)
        workflow.add_node("supervisor_subgraph", supervisor_subgraph_node)

        # Set entry point
        workflow.set_entry_point("planning")

        # Add conditional edges
        workflow.add_conditional_edges(
            "planning",
            routing_logic,
            {
                "planning": "planning",
                "supervisor_subgraph": "supervisor_subgraph",
                END: END,
            },
        )

        workflow.add_conditional_edges(
            "supervisor_subgraph",
            routing_logic,
            {
                "planning": "planning",
                "supervisor_subgraph": "supervisor_subgraph",
                END: END,
            },
        )

        return workflow.compile()

    def execute(self, state: AgentState) -> AgentState:
        """Execute the multi-agent workflow"""
        return self.workflow.invoke(state)


def run_workflow(user_request: str) -> Dict[str, Any]:
    """Run task using the multi-agent workflow"""
    workflow = MultiAgentWorkflow()

    # Create initial state
    initial_state = AgentState(
        origin_user_request=user_request,
        plan_list=[],
        current_plan_index=0,
        status=MainWorkflowStatus.INITIAL,
        messages=[],
    )

    return workflow.execute(initial_state)
