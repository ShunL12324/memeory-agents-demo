import json  # pylint: disable=missing-module-docstring

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from typing_extensions import Any, Literal

from src import logger
from src.models import MainGraphState, SupervisorSubGraphState

from .react_agents import PlannerAgent, RoleCreatorAgent, SupervisorAgent


# Supervisor subgraph
class SupervisorSubGraph:
    """Supervisor agent workflow that coordinates the supervisor subgraph."""

    def __init__(self) -> None:
        """初始化"""
        self.supervisor = SupervisorAgent()
        self.role_creator = RoleCreatorAgent()
        self.workflow = self._create_workflow()

    def _create_workflow(self) -> Any:
        """创建工作流"""
        workflow = StateGraph(SupervisorSubGraphState)

        # Add nodes
        workflow.add_node(
            "supervisor",
            self.supervisor.react_agent,
            destinations=(
                "role_creator",
                "__end__",
            ),
        )
        workflow.add_node("role_creator", self.role_creator.react_agent)
        workflow.add_edge(START, "supervisor")
        workflow.add_edge("role_creator", "supervisor")

        return workflow.compile()


class MainGraph:
    """主图工作流，包含Planner和Supervisor子图"""

    def __init__(self):
        self.planner = PlannerAgent()
        self.supervisor_subgraph = SupervisorSubGraph()
        self.workflow = self._create_workflow()

    def _supervisor_subgraph_node(
        self, state: MainGraphState
    ) -> Command[Literal["planner"]]:
        origin_user_request = state.get("origin_user_request", "")
        current_phase_info = state.get("current_phase_info", "")

        logger.get_logger()._write_log(  # pylint: disable=protected-access
            "INFO",
            "supervisor_subgraph_node",
            "Processing phase in supervisor subgraph",
            {
                "origin_user_request": origin_user_request,
                "current_phase_info": current_phase_info,
            },
        )

        supervisor_workflow_state = {
            "messages": [
                HumanMessage(
                    content="The original user request: "
                    + origin_user_request
                    + "\n\n"
                    + "This is info of current phase you are going to process:"
                    + current_phase_info,
                )
            ],
            "origin_user_request": origin_user_request,
        }

        self.supervisor_subgraph.workflow.invoke(supervisor_workflow_state)

        message = AIMessage(
            role="supervisor_subgraph",
            content="Successfully finished the phase, now you can continue to the next phase.",
        )

        # Update the state with the tool message and set the next graph to "planner"
        return Command(
            update={
                **state,
                "messages": [message],
            },
            goto="planner",
        )

    def _create_workflow(self) -> CompiledStateGraph[MainGraphState]:
        # Build the workflow graph
        workflow = StateGraph(MainGraphState)

        # Add nodes
        workflow.add_node(
            "planner",
            self.planner.react_agent,
            destinations=("supervisor_subgraph", END),
        )
        workflow.add_node(
            "supervisor_subgraph",
            self._supervisor_subgraph_node,
        )

        workflow.add_edge(START, "planner")
        workflow.add_edge("planner", "supervisor_subgraph")

        return workflow.compile()


def run_workflow(user_request: str) -> Any:
    """Run task using the multi-agent workflow"""
    workflow = MainGraph()

    # Create initial state
    initial_state = {
        "origin_user_request": user_request,
        "current_phase_info": "",
        "messages": [HumanMessage(content=user_request)],
    }

    logger.get_logger()._write_log(  # pylint: disable=protected-access
        "INFO",
        "run_workflow",
        "Starting multi-agent workflow",
        {"initial_state_keys": list(initial_state.keys())},
    )

    for agent, mode, chunk in workflow.workflow.stream(  # pylint: disable=unused-variable
        initial_state,  # type: ignore
        config={"configurable": {"thread_id": "test_main_thread"}},
        stream_mode=["messages"],
        # stream_mode=["debug"],
        subgraphs=True,
    ):
        # print(f"Agent: {agent}, Mode: {mode}")
        # print(f"Chunk: {chunk}")
        try:
            if isinstance(chunk, tuple) and len(chunk) == 2:
                message_chunk = chunk[0]
                # metadata = chunk[1]
                if isinstance(message_chunk, AIMessageChunk):
                    if hasattr(message_chunk, "content"):
                        if isinstance(message_chunk.content, str):
                            print(message_chunk.content, end="", flush=True)
                        elif isinstance(message_chunk.content, list):
                            for item in message_chunk.content:
                                if "type" in item:
                                    if "text" in item:
                                        print(item["text"], end="", flush=True)  # type: ignore
                                    if "input" in item:
                                        print(
                                            json.dumps(
                                                item["input"],  # type: ignore
                                                indent=2,
                                                ensure_ascii=False,
                                            ),
                                            end="",
                                            flush=True,
                                        )  # type: ignore
        except Exception as e:  # pylint: disable=broad-except
            logger.get_logger()._write_log(  # pylint: disable=protected-access
                "ERROR",
                "run_workflow",
                "Error processing chunk",
                {"error": str(e)},
            )
            print(f"Error processing chunk: {e}")
            continue
    return ""
