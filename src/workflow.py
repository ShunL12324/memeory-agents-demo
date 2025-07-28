# pylint: disable=missing-module-docstring

from pathlib import Path

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from typing_extensions import Any, Literal

from src import logger
from src.models import MainGraphState, SupervisorSubGraphState
from src.utils import process_stream_chunk

from .react_agents import PlannerAgent, RoleCreatorAgent, SupervisorAgent


def _save_graph_png(graph: CompiledStateGraph, filename: str) -> None:
    """保存workflow图表为PNG文件"""
    try:
        # 确保图片目录存在
        Path("graphs").mkdir(exist_ok=True)

        # 生成PNG数据
        png_data = graph.get_graph().draw_mermaid_png()

        # 保存到文件
        graph_path = Path("graphs") / filename
        with open(graph_path, "wb") as f:
            f.write(png_data)

        logger.get_logger().workflow_step(
            "graph_generation",
            f"Workflow graph saved to {graph_path}",
            {"filename": filename, "path": str(graph_path)},
        )

    except Exception as e:  # pylint: disable=broad-except
        logger.get_logger().error(
            "graph_generation",
            f"Failed to save workflow graph: {e}",
            {"filename": filename, "error": str(e)},
        )


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
        )
        workflow.add_node("role_creator", self.role_creator.react_agent)

        workflow.add_edge(START, "supervisor")
        # workflow.add_edge("supervisor", "role_creator")
        workflow.add_edge("role_creator", "supervisor")
        # workflow.add_edge("supervisor", END)

        compiled_workflow = workflow.compile()

        # 保存子图的图片
        _save_graph_png(compiled_workflow, "supervisor_subgraph.png")

        return compiled_workflow


class MainGraph:
    """主图工作流，包含Planner和Supervisor子图"""

    def __init__(self):
        self.planner = PlannerAgent()
        self.supervisor_subgraph = SupervisorSubGraph()
        self.workflow = self._create_workflow()
        logger.get_logger().workflow_step("workflow_init", "MainGraph initialized")

    def _supervisor_subgraph_node(
        self, state: MainGraphState
    ) -> Command[Literal["planner"]]:
        origin_user_request = state.get("origin_user_request", "")
        current_phase_info = state.get("current_phase_info", "")

        logger.get_logger().workflow_step(
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

        logger.get_logger().workflow_step(
            "supervisor_subgraph_invoke",
            "Invoking supervisor subgraph workflow",
            {
                "phase_info": current_phase_info[:100] + "..."
                if len(current_phase_info) > 100
                else current_phase_info
            },
        )

        result = self.supervisor_subgraph.workflow.invoke(supervisor_workflow_state)

        logger.get_logger().workflow_step(
            "supervisor_subgraph_complete",
            "Supervisor subgraph completed, returning to planner",
        )

        # Summaries the messages within the supervisor subgraph
        llm_summary = self.supervisor_subgraph.supervisor.llm
        history_info = ""
        for msg in result.get("messages", []):
            if isinstance(msg, AIMessage):
                content = msg.content
                if isinstance(content, list):
                    content = "\n".join(
                        [
                            item["text"]
                            if isinstance(item, dict) and "text" in item
                            else str(item)
                            for item in content
                        ]
                    )
                history_info += f"[AI]: {content}\n"
            elif isinstance(msg, HumanMessage):
                content = msg.content
                if isinstance(content, list):
                    content = "\n".join(
                        [
                            item["text"]
                            if isinstance(item, dict) and "text" in item
                            else str(item)
                            for item in content
                        ]
                    )
                history_info += f"[User]: {content}\n"

        # Summarize the conversation
        summary_message = llm_summary.invoke(
            [
                {
                    "role": "system",
                    "content": "You are a expert summarizer. You can precisely summarize the conversation, keep all the key information, conclusions and decisions. But make content conscise.",
                },
                {
                    "role": "user",
                    "content": f"Summarize the following conversation:\n{history_info}",
                },
            ]
        )

        report_message = AIMessage(
            role="supervisor_subgraph", content=summary_message.content
        )

        # Update the state with the tool message and set the next graph to "planner"
        return Command(
            update={
                **state,
                "messages": [report_message],
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
        )
        workflow.add_node(
            "supervisor_subgraph",
            self._supervisor_subgraph_node,
        )

        workflow.add_edge(START, "planner")
        # workflow.add_edge("planner", "supervisor_subgraph")
        # workflow.add_edge("supervisor_subgraph", "planner")
        # workflow.add_edge("planner", END)

        compiled_workflow = workflow.compile()

        # 保存主图的图片
        _save_graph_png(compiled_workflow, "main_workflow.png")

        return compiled_workflow


def run_workflow(user_request: str) -> Any:
    """Run task using the multi-agent workflow"""
    workflow = MainGraph()

    # Create initial state
    initial_state = {
        "origin_user_request": user_request,
        "current_phase_info": "",
        "messages": [HumanMessage(content=user_request)],
    }

    print("[WORKFLOW] Starting multi-agent workflow...")
    logger.get_logger().workflow_step(
        "run_workflow",
        "Starting multi-agent workflow",
        {
            "user_request": user_request,
            "initial_state_keys": list(initial_state.keys()),
        },
    )

    # 用于缓存JSON内容的变量
    json_buffer = ""
    in_json_mode = False

    stored_agent = ""

    for agent, mode, chunk in workflow.workflow.stream(  # pylint: disable=unused-variable
        initial_state,  # type: ignore
        config={"configurable": {"thread_id": "test_main_thread"}},
        stream_mode=["messages"],
        # stream_mode=["debug"],
        subgraphs=True,
    ):
        try:
            if isinstance(chunk, tuple) and len(chunk) == 2:
                message_chunk = chunk[0]
                # metadata = chunk[1]
                if isinstance(message_chunk, AIMessageChunk):
                    if agent != stored_agent:
                        stored_agent = agent
                        print(f"AGENT: {agent}")
                    json_buffer, in_json_mode = process_stream_chunk(
                        message_chunk, json_buffer, in_json_mode
                    )
        except Exception as e:  # pylint: disable=broad-except
            logger.get_logger().error(
                "run_workflow",
                "Error processing chunk",
                {"error": str(e)},
                print_to_console=False,  # 避免干扰流式输出
            )
            print(f"\n[ERROR] Error processing chunk: {e}\n")
            continue

    print("\n[WORKFLOW] Completed successfully!")
    logger.get_logger().workflow_step("run_workflow", "Workflow execution completed")
    return ""
