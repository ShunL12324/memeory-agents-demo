from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.tools import tool


class ReadFileInput(BaseModel):
    """Input schema for reading a file."""
    file_path: str = Field(description="Path to the file to read")


class WriteFileInput(BaseModel):
    """Input schema for writing content to a file."""
    file_path: str = Field(description="Path to the file to write to")
    content: str = Field(description="Content to write to the file")


class EditFileInput(BaseModel):
    """Input schema for editing a file."""
    file_path: str = Field(description="Path to the file to edit")
    old_text: str = Field(description="Text to be replaced in the file")
    new_text: str = Field(description="New text to replace the old text with")


class ListFilesInput(BaseModel):
    """Input schema for listing files in a directory."""
    path: str = Field(description="Path to the directory to list files from")
    depth: int = Field(default=1, description="Maximum depth to traverse (1 = current directory only, 2 = include subdirectories, etc.)")
    

@tool(
    "read_file",
    description="Read the contents of a file and return them as a string. Returns error message if file not found.",
    args_schema=ReadFileInput
)
def read_file(file_path: str) -> str:
    """Read the contents of a file and return them as a string."""
    try:
        path = Path(file_path)
        if not path.exists():
            return "Error: File not found"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"Content:\n{content}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(
    "write_file",
    description="Write content to a file, creating parent directories if they don't exist. Overwrites existing files.",
    args_schema=WriteFileInput
)
def write_file(file_path: str, content: str) -> str:
    """Write content to a file, creating parent directories if needed."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote {len(content)} characters to {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(
    "edit_file",
    description="Edit a file by replacing all occurrences of old_text with new_text. Returns error if file not found or text not found.",
    args_schema=EditFileInput
)
def edit_file(file_path: str, old_text: str, new_text: str) -> str:
    """Edit a file by replacing all occurrences of old_text with new_text."""
    try:
        path = Path(file_path)
        if not path.exists():
            return "Error: File not found"
        
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if old_text not in content:
            return "Error: Text to replace not found"
        
        new_content = content.replace(old_text, new_text)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        count = content.count(old_text)
        return f"Successfully replaced {count} occurrence(s)"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(
    "list_files",
    description="List files and directories in a given path with specified depth. Returns file paths and basic information.",
    args_schema=ListFilesInput
)
def list_files(path: str, depth: int = 1) -> str:
    """List files and directories in a given path with specified depth."""
    try:
        base_path = Path(path)
        if not base_path.exists():
            return "Error: Directory not found"
        
        if not base_path.is_dir():
            return "Error: Path is not a directory"
        
        files_info = []
        
        def collect_files(current_path: Path, current_depth: int, max_depth: int):
            if current_depth > max_depth:
                return
            
            try:
                for item in sorted(current_path.iterdir()):
                    relative_path = item.relative_to(base_path)
                    indent = "  " * (current_depth - 1)
                    
                    if item.is_dir():
                        files_info.append(f"{indent}{relative_path}/ (directory)")
                        if current_depth < max_depth:
                            collect_files(item, current_depth + 1, max_depth)
                    else:
                        size = item.stat().st_size
                        files_info.append(f"{indent}{relative_path} ({size} bytes)")
            except PermissionError:
                files_info.append(f"{indent}[Permission denied]")
        
        collect_files(base_path, 1, depth)
        
        if not files_info:
            return f"Directory {path} is empty"
        
        return f"Files in {path} (depth={depth}):\n" + "\n".join(files_info)
        
    except Exception as e:
        return f"Error: {str(e)}"   


# Export tools for easy import
file_tools = [read_file, write_file, edit_file, list_files]
all_tools = [] + file_tools