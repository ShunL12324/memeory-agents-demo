"""工具函数和辅助方法.AI写的，用来处理流式消息和格式化输出."""

from typing import Any, Dict, Optional, Tuple

from langchain_core.messages import AIMessageChunk


def process_stream_chunk(
    message_chunk: AIMessageChunk, json_buffer: str, in_json_mode: bool
) -> Tuple[str, bool]:
    """
    处理流式消息块，简单处理转义字符.

    Args:
        message_chunk: AI消息块
        json_buffer: JSON缓存 (用于检测工具调用开始)
        in_json_mode: 是否在工具调用模式

    Returns:
        (json_buffer, in_json_mode)
    """
    if not hasattr(message_chunk, "content"):
        return json_buffer, in_json_mode

    if isinstance(message_chunk.content, str):
        # 直接输出字符串内容，处理转义字符
        content = _unescape_string(message_chunk.content)
        print(content, end="", flush=True)

    elif isinstance(message_chunk.content, list):
        for item in message_chunk.content:
            if isinstance(item, dict) and "type" in item:
                if "text" in item:
                    # 如果之前在工具调用模式，现在遇到文本，说明工具调用结束
                    if in_json_mode:
                        print("\n\n", flush=True)
                        in_json_mode = False

                    # 处理文本内容的转义字符
                    text_content = _unescape_string(item["text"])
                    print(text_content, end="", flush=True)
                elif "input" in item:
                    # 检测工具调用开始
                    if not in_json_mode:
                        print("\n[TOOL] ", end="", flush=True)
                        in_json_mode = True

                    # 将工具调用输入作为普通文本流式输出，处理转义字符
                    input_content = item["input"]
                    if isinstance(input_content, dict):
                        for k, v in input_content.items():  # pylint: disable=unused-variable
                            if isinstance(v, str):
                                # 处理转义字符后输出
                                unescaped_content = _unescape_string(v)
                                print(unescaped_content, end="", flush=True)
                            else:
                                print(str(v), end="", flush=True)
                    else:
                        # 如果不是字典，直接输出
                        content = _unescape_string(str(input_content))
                        print(content, end="", flush=True)

    return json_buffer, in_json_mode


def _unescape_string(text: str) -> str:
    """处理字符串中的转义字符."""
    if not isinstance(text, str):
        return text

    # 处理常见的转义字符
    try:
        # 使用更完整的转义字符处理
        unescaped = text

        # 处理各种转义序列，顺序很重要
        replacements = [
            ("\\\\", "\x00"),  # 临时替换双反斜杠，避免干扰
            ('\\"', '"'),  # 转义引号
            ("\\n", "\n"),  # 换行符
            ("\\t", "\t"),  # 制表符
            ("\\r", "\r"),  # 回车符
            ("\\/", "/"),  # 转义斜杠
            ("\\b", "\b"),  # 退格符
            ("\\f", "\f"),  # 换页符
            ("\x00", "\\"),  # 恢复单反斜杠
        ]

        for old, new in replacements:
            unescaped = unescaped.replace(old, new)

        return unescaped
    except Exception:
        # 如果处理失败，返回原始字符串
        return text


def format_user_request_display(request: str) -> str:
    """格式化用户请求的显示."""
    return f"[REQUEST] {request}"


def format_workflow_status(
    status: str, details: Optional[Dict[str, Any]] = None
) -> str:
    """格式化工作流状态显示."""
    status_prefixes = {
        "starting": "[START]",
        "processing": "[PROC]",
        "completed": "[DONE]",
        "error": "[ERROR]",
    }
    prefix = status_prefixes.get(status, "[INFO]")

    if details:
        detail_str = " | ".join([f"{k}: {v}" for k, v in details.items()])
        return f"{prefix} {status} | {detail_str}"

    return f"{prefix} {status}"
