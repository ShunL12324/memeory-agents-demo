"""Multi-agent system for processing character creation requests."""

import os
import sys

from workflow import run_workflow


def main():
    """Main entry point - requires command line argument"""
    if len(sys.argv) < 2:
        print('❌ 使用方法: python main.py "角色描述"')
        print('📝 示例: python main.py "创建一个魔法师角色，拥有火焰魔法和红色长袍"')
        sys.exit(1)

    # 获取用户请求
    user_request = " ".join(sys.argv[1:])
    print(f"🚀 处理请求: {user_request}")
    print("=" * 60)

    try:
        # 检查基本配置
        from config import get_bedrock_config

        get_bedrock_config()  # Verify config is loadable

        # 删除旧的todo.md
        todo_json_path = "todo.md"
        if os.path.exists(todo_json_path):
            os.remove(todo_json_path)
            print(f"🗑️ 已删除旧的 {todo_json_path} 文件")

        # 执行workflow
        result = run_workflow(user_request)
        print(f"\n✅ 执行完成，状态: {result.get('status', 'unknown')}")

    except ImportError as e:
        print(f"❌ 配置错误: {str(e)}")
        print("💡 请检查config.py文件")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 执行失败: {str(e)}")
        import traceback

        print("\n🔍 详细错误信息:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
