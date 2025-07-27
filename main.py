"""Multi-agent system for processing character creation requests."""

import sys

from src.workflow import run_workflow


def main():
    user_request = " ".join(sys.argv[1:])
    print(f"处理请求: {user_request}")
    print("=" * 60)

    result = run_workflow(user_request)
    print(f"处理结果: {result}")


if __name__ == "__main__":
    main()
