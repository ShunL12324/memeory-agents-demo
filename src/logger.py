"""简化的多智能体工作流日志系统."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


class WorkflowLogger:
    """简化的工作流日志记录器"""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        self.log_file = self.logs_dir / f"workflow_{self.session_id}.log"
        
        # 清理旧日志文件，只保留最近3个
        self._cleanup_old_logs()
        
        # 记录初始日志
        self.info("workflow", "Workflow logging started", {"session_id": self.session_id})

    def _cleanup_old_logs(self):
        """保留最近3个日志文件"""
        log_files = list(self.logs_dir.glob("workflow_*.log"))
        if len(log_files) > 3:
            log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            for old_file in log_files[3:]:
                try:
                    old_file.unlink()
                except OSError:
                    pass

    def _write_log(self, level: str, component: str, message: str, data: Optional[Dict[str, Any]] = None, print_to_console: bool = True):
        """写入日志条目"""
        timestamp = datetime.now().isoformat()
        
        # 构建日志条目
        log_entry = f"[{timestamp}] [{level}] [{component}] {message}"
        if data:
            log_entry += f" | {json.dumps(data, ensure_ascii=False)}"
        
        # 写入文件
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
        except (OSError, IOError) as e:
            if print_to_console:
                print(f"Warning: Failed to write to log file: {e}")
        
        # 可选打印到控制台
        if print_to_console:
            print(log_entry)

    def info(self, component: str, message: str, data: Optional[Dict[str, Any]] = None, print_to_console: bool = True):
        """记录信息日志"""
        self._write_log("INFO", component, message, data, print_to_console)

    def error(self, component: str, message: str, data: Optional[Dict[str, Any]] = None, print_to_console: bool = True):
        """记录错误日志"""
        self._write_log("ERROR", component, message, data, print_to_console)

    def tool_call(self, agent: str, tool: str, input_data: Dict[str, Any], output: Any, success: bool = True, print_to_console: bool = True):
        """记录工具调用"""
        level = "INFO" if success else "ERROR"
        output_str = str(output)
        if len(output_str) > 300:
            output_str = output_str[:300] + "..."
        
        self._write_log(
            level, 
            f"tool_{tool}", 
            f"Tool called by {agent}",
            {"input": input_data, "output": output_str, "success": success},
            print_to_console
        )

    def workflow_step(self, step: str, message: str, data: Optional[Dict[str, Any]] = None):
        """记录工作流步骤 - 仅记录到文件，不打印到控制台"""
        self._write_log("WORKFLOW", step, message, data, print_to_console=False)


# 全局logger实例
_current_logger: Optional[WorkflowLogger] = None


def get_logger(session_id: Optional[str] = None) -> WorkflowLogger:
    """获取或创建工作流日志记录器"""
    global _current_logger
    if _current_logger is None or (session_id and _current_logger.session_id != session_id):
        _current_logger = WorkflowLogger(session_id)
    return _current_logger