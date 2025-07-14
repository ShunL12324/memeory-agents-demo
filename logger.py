"""Logging system for multi-agent workflow."""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class WorkflowLogger:
    """Logger for multi-agent workflow execution"""

    def __init__(self, session_id: str = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)

        # Create log files with timestamp
        self.log_file = self.logs_dir / f"workflow_{self.session_id}.log"
        
        # Clean up old log files, keep only 3 most recent
        self._cleanup_old_logs()

        # Initialize log data
        self.log_data = {
            "session_id": self.session_id,
            "start_time": datetime.now().isoformat(),
            "workflow_steps": [],
            "agent_interactions": [],
            "tool_calls": [],
            "errors": [],
            "final_status": None,
        }

        # Write initial log entry
        self._write_log(
            "INFO",
            "workflow",
            "Workflow logging started",
            {
                "session_id": self.session_id,
                "log_file": str(self.log_file),
            },
        )

    def _write_log(
        self, level: str, component: str, message: str, data: Dict[str, Any] = None
    ):
        """Write a log entry to text, JSON, and markdown logs"""
        timestamp = datetime.now().isoformat()

        # Text log entry
        log_entry = f"[{timestamp}] [{level}] [{component}] {message}"
        if data:
            log_entry += f" | Data: {json.dumps(data, ensure_ascii=False)}"

        # Write to text log
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

        # Add to JSON log data
        json_entry = {
            "timestamp": timestamp,
            "level": level,
            "component": component,
            "message": message,
            "data": data or {},
        }

        # Categorize the entry
        if component.endswith("_agent"):
            self.log_data["agent_interactions"].append(json_entry)
        elif "tool" in component.lower():
            self.log_data["tool_calls"].append(json_entry)
        elif level == "ERROR":
            self.log_data["errors"].append(json_entry)
        else:
            self.log_data["workflow_steps"].append(json_entry)

    def _cleanup_old_logs(self):
        """Keep only the 3 most recent log files"""
        log_files = list(self.logs_dir.glob("workflow_*.log"))
        if len(log_files) > 3:
            # Sort by modification time, newest first
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            # Remove old files beyond the 3 most recent
            for old_file in log_files[3:]:
                try:
                    old_file.unlink()
                except OSError:
                    pass  # Ignore errors if file can't be deleted

    def _init_markdown_log(self):
        """Initialize the readable log file"""
        with open(self.md_log_file, "w", encoding="utf-8") as f:
            f.write(f"Multi-Agent Workflow Log\n")
            f.write(f"{'='*50}\n")
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*50}\n\n")

    def _write_markdown_entry(
        self,
        timestamp: str,
        level: str,
        component: str,
        message: str,
        data: Dict[str, Any] = None,
    ):
        """Write an entry to the markdown log"""
        time_str = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")

        with open(self.md_log_file, "a", encoding="utf-8") as f:
            # Different formatting based on component type
            if component.endswith("_agent"):
                self._write_agent_markdown(f, time_str, level, component, message, data)
            elif "tool" in component.lower():
                self._write_tool_markdown(f, time_str, level, component, message, data)
            elif level == "ERROR":
                self._write_error_markdown(f, time_str, component, message, data)
            else:
                self._write_workflow_markdown(
                    f, time_str, level, component, message, data
                )

    def _write_agent_markdown(
        self,
        f,
        time_str: str,
        level: str,
        component: str,
        message: str,
        data: Dict[str, Any],
    ):
        """Write agent interaction in readable format"""
        # Extract agent name and index
        agent_name = component.replace("_agent", "")

        # Get current interaction index for this agent
        if not hasattr(self, "_agent_counters"):
            self._agent_counters = {}
        if agent_name not in self._agent_counters:
            self._agent_counters[agent_name] = 0
        self._agent_counters[agent_name] += 1

        index = self._agent_counters[agent_name]

        f.write(f"[{index:02d}] {agent_name.upper()} @ {time_str}\n")
        f.write(f"{'-'*40}\n")

        # Input section - show the messages sent to LLM
        if data and "input" in data:
            input_data = data["input"]

            # Show system message if available
            if "system_message" in input_data and input_data["system_message"]:
                f.write(
                    f"SYSTEM> {input_data['system_message'][:150]}{'...' if len(input_data['system_message']) > 150 else ''}\n\n"
                )

            # Show user message if available
            if "user_message" in input_data and input_data["user_message"]:
                f.write(f"USER> {input_data['user_message']}\n\n")

        # Response section with thinking support
        if data and "response" in data:
            response = data["response"]
            f.write(f"RESPONSE>\n")
            f.write(f"{response}\n\n")

        # Processing time
        if data and "processing_time_seconds" in data:
            f.write(f"Time: {data['processing_time_seconds']:.2f}s\n")

        f.write(f"{'-'*40}\n\n")

    def _write_tool_markdown(
        self,
        f,
        time_str: str,
        level: str,
        component: str,
        message: str,
        data: Dict[str, Any],
    ):
        """Write tool call in readable format"""
        tool_name = component.replace("tool_", "")
        status_icon = "✓" if level == "INFO" else "✗"

        f.write(f"TOOL {status_icon} {tool_name} @ {time_str}\n")
        f.write(f"Agent: {data.get('agent', 'unknown')}\n")

        if data and "tool_input" in data:
            f.write(f"Input: ")
            input_data = data["tool_input"]
            # Show input as key=value pairs on single line
            input_items = []
            for key, value in input_data.items():
                if len(str(value)) > 50:
                    input_items.append(f"{key}=<{len(str(value))} chars>")
                else:
                    input_items.append(f"{key}={value}")
            f.write(", ".join(input_items))
            f.write("\n")

        if data and "tool_output" in data:
            output = data["tool_output"]
            f.write(f"Output: ")
            if len(output) > 100:
                f.write(f"{output[:100]}... ({len(output)} chars total)\n")
            else:
                f.write(f"{output}\n")

        f.write(f"{'-'*30}\n\n")

    def _write_error_markdown(
        self, f, time_str: str, component: str, message: str, data: Dict[str, Any]
    ):
        """Write error in readable format"""
        f.write(f"ERROR ✗ {component} @ {time_str}\n")
        f.write(f"Message: {message}\n")

        if data:
            f.write(f"Details: {json.dumps(data, ensure_ascii=False)}\n")

        f.write(f"{'-'*30}\n\n")

    def _write_workflow_markdown(
        self,
        f,
        time_str: str,
        level: str,
        component: str,
        message: str,
        data: Dict[str, Any],
    ):
        """Write workflow step in readable format"""
        # Only log important workflow events
        if "workflow" in component and level == "INFO":
            if "started" in message.lower():
                f.write(f"WORKFLOW STARTED @ {time_str}\n")
                if data and "character_request" in data:
                    f.write(f"Request: {data['character_request']}\n")
                f.write(f"{'-'*40}\n\n")
            elif "completed" in message.lower():
                f.write(f"WORKFLOW COMPLETED @ {time_str}\n")
                if data and "final_state" in data:
                    final_state = data["final_state"]
                    if "status" in final_state:
                        f.write(f"Status: {final_state['status']}\n")
                    if "task_results" in final_state:
                        f.write(f"Tasks: {len(final_state['task_results'])}\n")
                f.write(f"{'-'*40}\n\n")

    def log_workflow_start(
        self, character_request: str, context: Dict[str, Any] = None
    ):
        """Log workflow start"""
        self._write_log(
            "INFO",
            "workflow",
            "Character creation workflow started",
            {"character_request": character_request, "context": context or {}},
        )

    def log_workflow_end(self, status: str, final_state: Dict[str, Any] = None):
        """Log workflow completion"""
        self.log_data["final_status"] = status
        self.log_data["end_time"] = datetime.now().isoformat()

        self._write_log(
            "INFO",
            "workflow",
            f"Workflow completed with status: {status}",
            {"final_state": final_state or {}},
        )

    def log_agent_response(
        self,
        agent_name: str,
        action: str,
        input_data: Dict[str, Any],
        response: str,
        processing_time: float = None,
    ):
        """Log agent response"""
        self._write_log(
            "INFO",
            f"{agent_name}_agent",
            f"Agent action: {action}",
            {
                "input": input_data,
                "response": response,  # Keep full response for thinking content
                "response_length": len(response),
                "processing_time_seconds": processing_time,
            },
        )

    def log_tool_call(
        self,
        agent_name: str,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_output: str,
        success: bool = True,
    ):
        """Log tool call"""
        level = "INFO" if success else "ERROR"
        self._write_log(
            level,
            f"tool_{tool_name}",
            f"Tool called by {agent_name}",
            {
                "tool_input": tool_input,
                "tool_output": (
                    tool_output[:300] + "..." if len(tool_output) > 300 else tool_output
                ),
                "success": success,
                "agent": agent_name,
            },
        )

    def log_state_transition(
        self, from_node: str, to_node: str, state_data: Dict[str, Any]
    ):
        """Log state transition between nodes"""
        self._write_log(
            "INFO",
            "workflow",
            f"State transition: {from_node} -> {to_node}",
            {
                "from_node": from_node,
                "to_node": to_node,
                "current_task_index": state_data.get("current_task_index"),
                "status": state_data.get("status"),
                "task_count": len(state_data.get("task_results", [])),
            },
        )

    def log_task_completion(
        self, task_id: str, task_name: str, asset_info: Dict[str, Any]
    ):
        """Log task completion"""
        self._write_log(
            "INFO",
            "task",
            f"Task completed: {task_id}",
            {"task_id": task_id, "task_name": task_name, "asset_info": asset_info},
        )

        # Write simple task completion entry
        with open(self.md_log_file, "a", encoding="utf-8") as f:
            f.write(f"TASK COMPLETED: {task_id}\n")
            f.write(f"Task: {task_name[:80]}{'...' if len(task_name) > 80 else ''}\n")
            if asset_info.get("assets_url"):
                f.write(f"Asset: {asset_info['assets_url']}\n")
            f.write(f"{'-'*20}\n\n")

    def log_error(
        self, component: str, error_message: str, error_data: Dict[str, Any] = None
    ):
        """Log error"""
        self._write_log("ERROR", component, error_message, error_data or {})

    def error(self, error_message: str, error_data: Dict[str, Any] = None):
        """Alias for log_error with default component"""
        self.log_error("system", error_message, error_data)

    def log_plan_creation(self, plan: Dict[str, Any]):
        """Log plan creation"""
        tasks = plan.get("tasks", [])
        self._write_log(
            "INFO",
            "planner_agent",
            f"Plan created with {len(tasks)} tasks",
            {
                "task_count": len(tasks),
                "task_list": [
                    {"task_id": t.get("task_id"), "task_name": t.get("task_name")}
                    for t in tasks
                ],
            },
        )

    def log_todo_file_operation(self, operation: str, file_path: str, result: str):
        """Log todo file operations"""
        self._write_log(
            "INFO",
            "supervisor_agent",
            f"Todo file {operation}",
            {"operation": operation, "file_path": file_path, "result": result},
        )

    def get_log_summary(self) -> Dict[str, Any]:
        """Get a summary of the current log"""
        return {
            "session_id": self.session_id,
            "workflow_steps_count": len(self.log_data["workflow_steps"]),
            "agent_interactions_count": len(self.log_data["agent_interactions"]),
            "tool_calls_count": len(self.log_data["tool_calls"]),
            "errors_count": len(self.log_data["errors"]),
            "final_status": self.log_data["final_status"],
            "log_files": {
                "text_log": str(self.log_file),
                "markdown_log": str(self.md_log_file),
            },
        }


# Global logger instance
_current_logger: Optional[WorkflowLogger] = None


def get_logger(session_id: str = None) -> WorkflowLogger:
    """Get or create workflow logger"""
    global _current_logger
    if _current_logger is None or (
        session_id and _current_logger.session_id != session_id
    ):
        _current_logger = WorkflowLogger(session_id)
    return _current_logger


def log_agent_response(
    agent_name: str,
    action: str,
    input_data: Dict[str, Any],
    response: str,
    processing_time: float = None,
):
    """Convenience function to log agent response"""
    get_logger().log_agent_response(
        agent_name, action, input_data, response, processing_time
    )


def log_tool_call(
    agent_name: str,
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: str,
    success: bool = True,
):
    """Convenience function to log tool call"""
    get_logger().log_tool_call(agent_name, tool_name, tool_input, tool_output, success)


def log_error(component: str, error_message: str, error_data: Dict[str, Any] = None):
    """Convenience function to log error"""
    get_logger().log_error(component, error_message, error_data)
