from typing import Dict, Any, List, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from agents import PlannerAgent, SupervisorAgent, RoleCreatorAgent
import json
import operator
from datetime import datetime
from simple_file_tools import format_ai_history_context_from_messages


class AgentState(TypedDict):
    """State shared between agents - minimal structure"""
    origin_user_request: str
    planning_results: str
    status: str
    messages: Annotated[List[AnyMessage], operator.add]  # Unified message storage with reducer

class SupervisorSubGraphState(TypedDict):
    """State shared between agents - minimal structure"""
    origin_user_request: str
    planning_results: str
    status: str
    phases: List[Dict[str, Any]]
    current_phase_index: int
    messages: Annotated[List[AnyMessage], operator.add]

# Supervisor subgraph
class SupervisorAgentWorkflow:

    def __init__(self) -> None:
        self.supervisor = SupervisorAgent()
        self.role_creator = RoleCreatorAgent()

        self.supervisor.register_agent(self.role_creator)

        self.workflow = self._create_workflow()

    def _create_workflow(self) -> StateGraph:

        """Create the LangGraph workflow"""
        def supervision_node(state: SupervisorSubGraphState) -> SupervisorSubGraphState:
            status = state.get("status", "")

            if status == "initial":
                return self.supervisor.execute(state)
            elif status == "ready_for_phase_processing":
                return self.role_creator.execute(state)
            elif status == "phase_completed":
                return self.supervisor.execute(state)
            elif status == "workflow_completed":
                return self.supervisor.execute(state)

            return state
        
        def role_creator_node(state: SupervisorSubGraphState) -> SupervisorSubGraphState:
            return self.role_creator.execute(state)
        
        def routing_logic(state: SupervisorSubGraphState) -> str:
            status = state.get("status", "")
            
            if status == "initial":
                return "supervision"
            elif status == "ready_for_phase_processing":
                return "role_creator"
            elif status == "phase_completed":
                return "supervision"
            elif status == "workflow_completed":
                return END
        
        # Build the workflow graph
        workflow = StateGraph(SupervisorSubGraphState)
        
        # Add nodes
        workflow.add_node("supervision", supervision_node)
        workflow.add_node("role_creator", role_creator_node)
        
        # Set entry point
        workflow.set_entry_point("supervision")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "supervision",
            routing_logic,
            {
                "supervision": "supervision",
                "role_creator": "role_creator",
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "role_creator",
            routing_logic,
            {
                "supervision": "supervision",
                END: END
            }
        )

        return workflow.compile()

    def execute(self, state: AgentState) -> AgentState:
        """Execute the supervisor subgraph"""
        subgraph_state = self.workflow.invoke(state)
        
        # update the state depends on the subgrah state
        # if state is error update the main workflow state to error
        # if state is workflow_completed
        # update the main workflow status completed
        subgraph_status = subgraph_state.get("status", "")
        if subgraph_status == "error":
            return AgentState(
                origin_user_request=state.get("origin_user_request", ""),
                planning_results=state.get("planning_results", ""),
                status="error",
                messages=[]
            )
        elif subgraph_status == "workflow_completed":
            return AgentState(
                origin_user_request=state.get("origin_user_request", ""),
                planning_results=state.get("planning_results", ""),
                status="workflow_completed",
                messages=[]
            )
        else:
            return state


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
                
            # construct an empty state for the supervisor subgraph
            supervisor_subgraph_state = SupervisorSubGraphState(
                origin_user_request=state.get("origin_user_request", ""),
                planning_results=state.get("planning_results", ""),
                status="initial",
                phases=[],
                current_phase_index=0,
                messages=[] # this should separete with the messages from the planning node
            )

            subgraph_result = self.supervisor_subgraph.execute(supervisor_subgraph_state)
            
            # Map subgraph result back to AgentState
            return AgentState(
                origin_user_request=subgraph_result.get("origin_user_request", ""),
                planning_results=subgraph_result.get("planning_results", ""),
                status=subgraph_result.get("status", ""),
                messages=state.get("messages", [])  # Preserve main workflow messages
            )
            
        def routing_logic(state: AgentState) -> str:
            """Determine next node based on current state"""
            status = state.get("status", "")
            
            if status == "initial":
                return "planning"
            elif status == "planning_completed":
                return "supervisor_subgraph"
            elif status == "workflow_completed":
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
                END: END
            }
        )
        
        workflow.add_conditional_edges(
            "supervisor_subgraph", 
            routing_logic,
            {
                "planning": "planning",
                "supervisor_subgraph": "supervisor_subgraph",
                END: END
            }
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
        planning_results="",
        status="initial",
        messages=[]
    )
    
    return workflow.execute(initial_state)