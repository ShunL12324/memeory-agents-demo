# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a memory agents demo project built with Python 3.10+. The project uses:
- **boto3** for AWS integrations
- **langchain-aws** for AWS-based language model operations
- **langgraph** for graph-based agent workflows

The project uses `uv` as the Python package manager instead of pip.

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Set AWS credentials (or use config.py defaults)
export AWS_ACCESS_KEY_ID="your-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-key"

# Quick test (不需要AWS配置) - 演示模式
uv run python start_demo.py

# Full demo (需要AWS Bedrock配置)
uv run python main.py
```

### Troubleshooting AWS Bedrock Issues

Common issues and solutions:

#### 1. Throttling/Quota Limits
```
Error: Too many tokens per day / ThrottlingException
```
**Solutions:**
- Wait a few hours for quota reset (daily limits)
- Check AWS Bedrock console for quota settings
- Try different AWS region
- Reduce token usage in config.py
- Use demo mode: `python start_demo.py`

#### 2. Configuration Issues
```
Error: ValidationException / thinking.enabled.budget_tokens
```
**Solutions:**
- Ensure thinking budget_tokens ≥ 1024
- Check model_id format matches Bedrock
- Verify region supports Claude 4 Sonnet

#### 3. Authentication Issues
```
Error: AWS credentials / UnauthorizedOperation
```
**Solutions:**
- Update AWS credentials in config.py
- Ensure IAM permissions for Bedrock
- Verify region setting (us-east-1)

### Python Environment
- Python version: 3.10 (specified in .python-version)
- Package manager: uv (evident from uv.lock file)
- Virtual environment managed by uv

### Bedrock Configuration
- Model: `us.anthropic.claude-sonnet-4-20250514-v1:0` (Claude 4 Sonnet with thinking)
- Region: `us-east-1`
- Timeout: 3600 seconds (required for Claude models)
- Agent-specific temperature settings:
  - Planner: 0.7 (creative planning)
  - Supervisor: 0.3 (deterministic coordination)  
  - Executor: 0.1 (precise execution)

## Architecture Notes

This is a multi-agent system for game character creation using LangGraph with planner + supervisor architecture:

### Agent Structure
- **PlannerAgent**: Creates structured task plans for character creation (concept art, 3D modeling, textures, etc.)
- **SupervisorAgent**: Manages todo.md file, coordinates tasks, and tracks asset creation progress
- **RoleCreatorAgent**: Generates character assets and uploads to S3 (simulated)

### Key Features
- **Structured Task Management**: JSON-formatted tasks with dependencies and asset tracking
- **todo.md Integration**: Automatic creation and updating of task status in markdown format
- **Asset Tracking**: Each task generates specific game assets with S3 URLs
- **Character Creation Pipeline**: 
  - Concept art and design
  - 3D modeling and textures
  - Rigging and animation
  - Backstory and lore
  - Integration testing

### File Structure
```
src/                          # Main source code directory
├── agents/                   # 智能体模块目录
│   ├── __init__.py
│   ├── base_agent.py        # Base agent class with AWS Bedrock integration
│   ├── planner_agent.py     # Task planning agent implementation
│   ├── supervisor_agent.py  # Coordination and monitoring agent
│   └── role_creator_agent.py # Character asset creation agent
├── prompts/                 # Agent-specific prompts separated by role
│   ├── planner_prompts.py
│   ├── supervisor_prompts.py
│   └── role_creator_prompts.py
├── workflow.py              # LangGraph workflow orchestration
├── tools.py                 # Tool definitions and integrations
├── utils.py                 # Utility functions
├── models.py               # Data models and state definitions
└── logger.py               # Comprehensive logging system (text, JSON, markdown)

# Root level files
├── main.py                  # Application entry point
├── config.py               # Configuration settings
├── config.example.py       # Configuration template
└── pyproject.toml          # Project configuration
```

### Tool System
File operations use simple Python functions to avoid LangChain complexity:
```python
# Simple file operations in src/tools.py
def simple_read_file(file_path: str) -> str:
    # Direct file operations without LangChain dependencies

# Used by SupervisorAgent for todo.md management
supervisor.manage_todo_file(tasks)  # Creates/updates todo.md
```

## Quick Start

### 运行系统
```bash
uv run python main.py
```
功能特点:
- 🎯 **交互式任务处理**: 输入任务描述，智能体团队协作完成
- 📋 **实时执行反馈**: 显示Planning → Supervision → Execution过程
- 💬 **会话管理**: 每次启动创建新的会话ID
- 🔧 **完整工作流**: Planner + Supervisor + Executor协作

### 支持的命令:
- `help` - 显示使用指南和任务示例
- `clear` - 清屏并重新显示标题
- `quit/exit/q` - 退出系统

### 3. 配置AWS凭据
如果使用自己的AWS账号:
1. 复制 `config.example.py` 到 `config_local.py`
2. 更新AWS凭据
3. 运行完整演示

### 使用示例:
```
🎯 请描述你想要的游戏角色 (会话: 20250628_010815):
>>> 创建一个魔法师角色，拥有火焰魔法和红色长袍

🚀 开始创建角色: 创建一个魔法师角色，拥有火焰魔法和红色长袍
──────────────────────────────────────────────────────

🎯 Planning character creation: 创建一个魔法师角色，拥有火焰魔法和红色长袍
📋 Plan created: 5 tasks
👔 Supervisor evaluating plan...
📄 Created todo.md with 5 tasks
📝 Tasks recorded in todo.md
🎨 Creating asset 1: Create concept art for fire mage character
✨ Asset created: s3://game-assets/characters/task_001_concept_art.png
📄 Updated task 001 in todo.md
...
✅ All tasks completed!

📊 执行完成!
──────────────
✅ 状态: completed
🎨 完成任务: 5
📦 创建的资产:
  1. s3://game-assets/characters/task_001_concept_art.png
  2. s3://game-assets/characters/task_002_3d_model.fbx
💬 系统消息: 15条
```