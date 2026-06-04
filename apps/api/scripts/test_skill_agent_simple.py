#!/usr/bin/env python3
"""
test_skill_agent_simple.py - 简易多轮对话测试脚本

快速测试 skill_agent 的多轮对话能力，无需复杂配置。
"""

import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from skill_agent import (
    create_openai_agent_with_skills,
    run_skill_agent,
    load_model_config,
)


class SimpleChatTester:
    """简易对话测试器"""

    def __init__(self, config_path: Path = None):
        # 加载配置
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent.parent / "data" / "model-providers" / "xunfei.json"

        config = load_model_config(config_path)
        if config:
            self.api_key = config.get("api_key")
            self.base_url = config.get("base_url")
            self.model = config.get("model", "gpt-4o")
            print(f"[配置] 已加载模型配置：{config.get('id', 'unknown')}")
        else:
            self.api_key = None
            self.base_url = None
            self.model = "gpt-4o"
            print("[配置] 未找到配置文件，使用默认配置")

        # 创建 agent
        print("[配置] 创建 Agent...")
        self.agent, self.loader, _ = create_openai_agent_with_skills(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
        )
        print(f"[配置] 已加载 {len(self.loader.list_skills())} 个 skills")
        print(f"  Skills: {', '.join(self.loader.list_skills())}")

        # 对话历史
        self.history = []

    async def chat(self, message: str) -> str:
        """发送消息并获取响应"""
        # 构建带上下文的查询
        if self.history:
            context = "\n".join([f"{h['role']}: {h['content']}" for h in self.history[-6:]])  # 最近 6 条
            full_query = f"""[对话历史]
{context}

[当前问题]
{message}

请根据对话历史回答。"""
        else:
            full_query = message

        # 运行 agent
        result = await run_skill_agent(full_query, agent=self.agent, loader=self.loader)
        return result

    async def run_chat(self):
        """运行对话"""
        print("\n" + "="*50)
        print("简易多轮对话测试")
        print("="*50)
        print("输入 '/quit' 退出，'/clear' 清空历史，'/show' 显示历史")
        print("-"*50)

        turn = 0
        while True:
            try:
                user_input = input(f"\n[第{turn+1}轮] 你：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[结束] 再见！")
                break

            if not user_input:
                continue

            # 命令处理
            if user_input.lower() == "/quit" or user_input.lower() == "/exit":
                print("[结束] 对话测试结束，再见！")
                break
            elif user_input.lower() == "/clear":
                self.history = []
                print("[操作] 对话历史已清空")
                continue
            elif user_input.lower() == "/show":
                self._show_history()
                continue

            # 发送消息
            turn += 1
            print(f"[第{turn}轮] 思考中...", end="\r")
            response = await self.chat(user_input)

            # 记录历史
            self.history.append({"role": "user", "content": user_input})
            self.history.append({"role": "assistant", "content": response})

            print(f"[第{turn}轮] Agent: {response}")

        # 显示统计
        if turn > 0:
            print(f"\n[统计] 共 {turn} 轮对话，{len(self.history)} 条消息")

    def _show_history(self):
        """显示对话历史"""
        if not self.history:
            print("[历史] 空")
            return

        print("\n" + "-"*50)
        for i, h in enumerate(self.history, 1):
            role = "你" if h["role"] == "user" else "Agent"
            content = h["content"][:80] + "..." if len(h["content"]) > 80 else h["content"]
            print(f"[{i}] {role}: {content}")
        print("-"*50)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Skill Agent 简易对话测试")
    parser.add_argument("--config", "-c", type=Path, default=None, help="模型配置文件路径")
    parser.add_argument("--query", "-q", type=str, default=None, help="单次查询（非交互模式）")

    args = parser.parse_args()

    # 创建测试器
    tester = SimpleChatTester(config_path=args.config)

    if args.query:
        # 单次查询模式
        print(f"\n查询：{args.query}")
        response = await tester.chat(args.query)
        print(f"\nAgent: {response}")
    else:
        # 交互模式
        await tester.run_chat()


if __name__ == "__main__":
    asyncio.run(main())
