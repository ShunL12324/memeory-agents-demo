"""Interactive multi-agent system for processing user requests."""

import sys
from workflow import run_workflow


class InteractiveAgent:
    """Interactive multi-agent system interface"""
    
    def __init__(self):
        pass
        
    def display_header(self):
        """Display system header"""
        print("🎮 Game Character Creation - Multi-Agent System")
        print("=" * 60)
        print("🎯 描述你想要的游戏角色，AI团队将协作创建")
        print("📝 输入 'help' 查看帮助，'quit' 退出系统")
        print("=" * 60)
        
    def display_help(self):
        """Display help information"""
        print("\n📚 游戏角色创建指南:")
        print("• 创建一个魔法师角色，拥有火焰魔法和长袍")
        print("• 设计一个赛博朋克战士，机械臂和激光武器")
        print("• 制作一个可爱的精灵弓箭手，绿色主题")
        print("• 创建一个暗黑风格的死灵法师")
        print("• 设计一个未来科幻的机器人角色")
        print("\n💡 提示: 描述角色外观、技能、风格等细节")
        
    def process_request(self, user_request: str):
        """Process user request through multi-agent workflow"""
        print(f"\n🚀 开始创建角色: {user_request}")
        print("─" * 50)
        
        try:
            # 执行workflow
            result = run_workflow(user_request)
            
            # 显示结果
            print("\n📊 执行完成!")
            print("─" * 30)
            print(f"✅ 状态: {result.get('status', 'unknown')}")
            
            if result.get('messages'):
                print(f"💬 系统消息: {len(result['messages'])}条")
                    
        except KeyboardInterrupt:
            print("\n⏹️ 用户中断执行")
        except Exception as e:
            print(f"\n❌ 执行失败: {str(e)}")
            
    def run_interactive_mode(self):
        """Run interactive mode"""
        self.display_header()
        
        while True:
            try:
                # 获取用户输入
                print("\n🎯 请描述你想要的游戏角色:")
                user_input = input(">>> ").strip()
                
                # 处理特殊命令
                if not user_input:
                    continue
                elif user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 再见! 感谢使用游戏角色创建系统")
                    break
                elif user_input.lower() in ['help', 'h']:
                    self.display_help()
                    continue
                elif user_input.lower() == 'clear':
                    # 清屏
                    print("\033[2J\033[H", end="")
                    self.display_header()
                    continue
                    
                # 处理用户请求
                self.process_request(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，系统退出")
                break
            except EOFError:
                print("\n\n👋 输入结束，系统退出")
                break


def main():
    """Main entry point"""
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 简单模式：python main.py "用户输入"
        user_request = " ".join(sys.argv[1:])
        print(f"🚀 处理请求: {user_request}")
        print("=" * 60)
        
        try:
            # 直接执行workflow
            result = run_workflow(user_request)
            print(f"\n✅ 执行完成，状态: {result.get('status', 'unknown')}")
            
        except Exception as e:
            print(f"\n❌ 执行失败: {str(e)}")
            import traceback
            print("\n🔍 详细错误信息:")
            traceback.print_exc()
            sys.exit(1)
    else:
        # 交互模式
        try:
            # 检查基本配置
            from config import get_bedrock_config
            get_bedrock_config()  # Verify config is loadable
            
            # 创建交互式系统
            interactive_agent = InteractiveAgent()
            
            # 运行交互模式
            interactive_agent.run_interactive_mode()
            
        except ImportError as e:
            print(f"❌ 配置错误: {str(e)}")
            print("💡 请检查config.py文件")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 系统启动失败: {str(e)}")
            print("💡 请检查依赖安装和AWS配置")
            sys.exit(1)


if __name__ == "__main__":
    main()