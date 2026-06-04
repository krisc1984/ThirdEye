#!/usr/bin/env python3
"""
test_skill_agent_multi_turn.py - 多轮对话测试脚本

用于测试 skill_agent 的多轮对话能力，支持：
1. 交互式多轮对话
2. 预设对话场景测试
3. 对话历史管理
4. 测试结果评估
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from skill_agent import (
    SkillLoader,
    create_openai_agent_with_skills,
    run_skill_agent,
    run_skill_agent_sync,
    load_model_config,
)


# =============================================================================
# 多轮对话测试器
# =============================================================================
class MultiTurnTester:
    """多轮对话测试器"""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        model: Optional[str] = None,
    ):
        self.config_path = config_path
        self.skills_dir = skills_dir
        self.model = model

        # 加载配置
        config = load_model_config(config_path)
        if config:
            self.api_key = config.get("api_key")
            self.base_url = config.get("base_url")
            self.model = model or config.get("model", "gpt-4o")
        else:
            self.api_key = None
            self.base_url = None
            self.model = model or "gpt-4o"

        # 创建 agent
        self.agent, self.loader, self.tools = create_openai_agent_with_skills(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            skills_dir=skills_dir,
            config_path=config_path,
        )

        # 对话历史
        self.history = []
        self.turn_count = 0

    def reset(self):
        """重置对话历史"""
        self.history = []
        self.turn_count = 0
        print("[Tester] 对话历史已重置")

    def send_message(self, message: str) -> str:
        """
        发送消息并获取响应

        Args:
            message: 用户消息

        Returns:
            Agent 响应
        """
        self.turn_count += 1

        # 构建带上下文的查询
        if self.history:
            context = "\n".join([f"{h['role']}: {h['content']}" for h in self.history])
            full_query = f"""[对话历史]
{context}

[当前问题]
{message}

请根据上述对话历史，回答当前问题。"""
        else:
            full_query = message

        print(f"\n{'='*60}")
        print(f"Turn {self.turn_count} | 用户：{message}")
        print('-'*60)

        # 运行 agent
        result = asyncio.run(run_skill_agent(
            full_query,
            agent=self.agent,
            loader=self.loader,
        ))

        # 记录历史
        self.history.append({"role": "user", "content": message})
        self.history.append({"role": "assistant", "content": result})

        print(f"Turn {self.turn_count} | Agent: {result[:200]}...")
        print('='*60)

        return result

    def run_interactive(self, max_turns: int = 20):
        """
        运行交互式多轮对话

        Args:
            max_turns: 最大对话轮数
        """
        print("\n" + "="*60)
        print("多轮对话测试 - 交互模式")
        print("="*60)
        print(f"模型：{self.model}")
        print(f"可用 skills: {len(self.loader.list_skills())}")
        print(f"最大轮数：{max_turns}")
        print("-"*60)
        print("命令:")
        print("  /reset  - 重置对话历史")
        print("  /history - 显示对话历史")
        print("  /save [filename] - 保存对话到文件")
        print("  /quit - 退出")
        print("-"*60)

        while self.turn_count < max_turns:
            try:
                user_input = input(f"\n[Turn {self.turn_count + 1}] 你：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[Tester] 对话结束")
                break

            if not user_input:
                continue

            # 处理命令
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                if cmd == "/quit" or cmd == "/exit":
                    print("[Tester] 退出对话测试")
                    break
                elif cmd == "/reset":
                    self.reset()
                    continue
                elif cmd == "/history":
                    self._print_history()
                    continue
                elif cmd == "/save":
                    filename = user_input.split()[1] if len(user_input.split()) > 1 else None
                    self.save_history(filename)
                    continue
                else:
                    print(f"[Tester] 未知命令：{cmd}")
                    continue

            # 发送消息
            response = self.send_message(user_input)
            print(f"\nAgent: {response}")

        print(f"\n[Tester] 对话完成，共 {self.turn_count} 轮")

    def run_scenario(self, scenario: list) -> list:
        """
        运行预设对话场景

        Args:
            scenario: 预设对话列表，如 ["问题 1", "问题 2", ...]

        Returns:
            响应列表
        """
        print("\n" + "="*60)
        print("多轮对话测试 - 场景模式")
        print("="*60)

        responses = []
        for i, message in enumerate(scenario, 1):
            print(f"\n[场景 {i}/{len(scenario)}] 用户：{message}")
            response = self.send_message(message)
            responses.append(response)
            print(f"[场景 {i}/{len(scenario)}] Agent: {response[:100]}...")

        return responses

    def _print_history(self):
        """打印对话历史"""
        if not self.history:
            print("[History] 空")
            return

        print("\n" + "-"*60)
        for i, h in enumerate(self.history, 1):
            role = "你" if h["role"] == "user" else "Agent"
            content = h["content"][:100] + "..." if len(h["content"]) > 100 else h["content"]
            print(f"[{i}] {role}: {content}")
        print("-"*60)

    def save_history(self, filename: Optional[str] = None):
        """保存对话历史到文件"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"conversation_{timestamp}.json"

        filepath = Path(filename)
        data = {
            "model": self.model,
            "config_path": str(self.config_path) if self.config_path else None,
            "turn_count": self.turn_count,
            "timestamp": datetime.now().isoformat(),
            "history": self.history,
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[Tester] 对话历史已保存到：{filepath}")

    def get_statistics(self) -> dict:
        """获取对话统计信息"""
        return {
            "turn_count": self.turn_count,
            "history_length": len(self.history),
            "skills_loaded": len(self.loader.list_skills()),
            "model": self.model,
        }


# =============================================================================
# 预设测试场景
# =============================================================================
SCENARIOS = {
    "code_review": [
        "帮我看看当前目录下有哪些 Python 文件",
        "这些文件中哪个包含测试代码？",
        "能分析一下测试代码的覆盖率吗？",
        "如何改进测试覆盖率？",
    ],
    "project_exploration": [
        "当前项目使用什么技术栈？",
        "后端使用的是什么框架？",
        "前端框架是什么版本？",
        "项目的目录结构是怎样的？",
    ],
    "skill_usage": [
        "你有哪些可用的技能？",
        "加载 code-review 技能",
        "使用这个技能帮我分析一下项目代码质量",
        "有什么改进建议？",
    ],
}


# =============================================================================
# 命令行入口
# =============================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Skill Agent 多轮对话测试器")
    parser.add_argument("--config", "-c", type=Path, default=None, help="模型配置文件路径")
    parser.add_argument("--skills-dir", type=Path, default=None, help="Skill 目录")
    parser.add_argument("--model", "-m", type=str, default=None, help="模型名称")
    parser.add_argument("--max-turns", "-n", type=int, default=20, help="最大对话轮数")
    parser.add_argument("--scenario", "-s", type=str, choices=list(SCENARIOS.keys()), help="预设场景")
    parser.add_argument("--output", "-o", type=str, default=None, help="保存对话的文件名")

    args = parser.parse_args()

    # 创建测试器
    tester = MultiTurnTester(
        config_path=args.config,
        skills_dir=args.skills_dir,
        model=args.model,
    )

    print("\n" + "="*60)
    print("Skill Agent 多轮对话测试器")
    print("="*60)
    print(f"配置：{args.config or '默认'}")
    print(f"模型：{tester.model}")
    print(f"Skills: {tester.loader.list_skills()}")
    print("="*60)

    try:
        if args.scenario:
            # 运行预设场景
            scenario = SCENARIOS[args.scenario]
            print(f"\n运行场景：{args.scenario}")
            print(f"问题数量：{len(scenario)}")

            responses = tester.run_scenario(scenario)

            # 打印统计
            stats = tester.get_statistics()
            print("\n" + "="*60)
            print("测试统计")
            print("="*60)
            for key, value in stats.items():
                print(f"  {key}: {value}")
        else:
            # 交互模式
            tester.run_interactive(max_turns=args.max_turns)

        # 保存对话
        if args.output or tester.turn_count > 0:
            tester.save_history(args.output)

    except Exception as e:
        print(f"\n[Error] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
