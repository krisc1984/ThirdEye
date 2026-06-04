#!/usr/bin/env python3
"""
test_skill_agent_openai.py - 使用原生 OpenAI 客户端测试 skill

这个脚本直接使用 OpenAI 客户端调用 skill，绕过 agents 库的兼容性问题。
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(override=True)

# 导入 SkillLoader
sys.path.insert(0, str(Path(__file__).parent))
from skill_agent import SkillLoader, WORKDIR, load_model_config


class OpenAISkillAgent:
    """使用原生 OpenAI 客户端的 Skill Agent"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
    ):
        # 加载配置
        config = load_model_config(config_path)
        if config:
            self.api_key = api_key or config.get("api_key")
            self.base_url = base_url or config.get("base_url")
            self.model = model or config.get("model", "gpt-4o")
            print(f"[配置] 已加载：{config.get('id', 'unknown')} | 模型：{self.model}")
        else:
            self.api_key = api_key
            self.base_url = base_url
            self.model = model or "gpt-4o"
            print(f"[配置] 使用默认配置 | 模型：{self.model}")

        # 创建 OpenAI 客户端
        from openai import OpenAI

        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = OpenAI(**client_kwargs)
        print(f"[客户端] Base URL: {self.base_url or 'default'}")

        # 加载 skills
        self.loader = SkillLoader(skills_dir or WORKDIR / ".skills")
        print(f"[Skills] 已加载 {len(self.loader.list_skills())} 个技能")

        # 构建工具定义
        self.tools = self._build_tools()

        # 构建 system prompt
        self.system_prompt = self._build_system_prompt()

        # 对话历史
        self.history = []

    def _build_system_prompt(self) -> str:
        """构建 system prompt"""
        skill_desc = self.loader.get_descriptions()
        return f"""你是一个在 {WORKDIR} 工作的编程助手。
你可以使用以下技能来获取专业知识：

{skill_desc}

当面对不熟悉的任务时：
1. 首先使用 list_skills 检查是否有相关技能
2. 使用 load_skill 获取详细指导
3. 按照技能的指导完成任务

可用工具：
- bash: 执行 shell 命令
- read_file: 读取文件
- write_file_chunk: 分块写入文件
- load_skill: 加载技能
- list_skills: 列出技能

请用中文回答。"""

    def _build_tools(self) -> list:
        """构建工具定义"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "执行 shell 命令",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令"}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取文件内容",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "limit": {"type": "integer", "description": "最大行数（可选）"},
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file_chunk",
                    "description": "分块写入文件，首块使用 overwrite，后续块使用 append",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "文件内容"},
                            "mode": {
                                "type": "string",
                                "description": "写入模式：overwrite 或 append",
                                "enum": ["overwrite", "append"],
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_skills",
                    "description": "列出所有可用技能",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "load_skill",
                    "description": "加载技能获取详细指导",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "技能名称"}
                        },
                        "required": ["name"],
                    },
                },
            },
        ]

    def _execute_tool(self, name: str, args: dict) -> str:
        """执行工具"""
        from skill_agent import (
            run_bash,
            run_read,
            run_write,
            run_list_skills,
        )

        try:
            if name == "bash":
                return run_bash(args["command"], WORKDIR)
            elif name == "read_file":
                return run_read(args["path"], WORKDIR, args.get("limit"))
            elif name == "write_file_chunk":
                overwrite = args.get("mode", "append") == "overwrite"
                return run_write(args["path"], args["content"], WORKDIR, overwrite=overwrite)
            elif name == "list_skills":
                return run_list_skills(self.loader)
            elif name == "load_skill":
                return self.loader.get_content(args["name"])
            else:
                return f"未知工具：{name}"
        except Exception as e:
            return f"工具执行错误：{e}"

    def chat(self, message: str, max_turns: int = 50) -> str:
        """
        发送消息并获取响应

        Args:
            message: 用户消息
            max_turns: 最大工具调用轮数

        Returns:
            Agent 响应
        """
        # 添加到历史
        self.history.append({"role": "user", "content": message})

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history,
        ]

        for turn in range(max_turns):
            # 调用 API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # 检查是否有工具调用
            if assistant_message.tool_calls:
                # 执行工具
                tool_results = []
                for tool_call in assistant_message.tool_calls:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    print(f"  [工具 {turn+1}] {func_name}({func_args})")

                    result = self._execute_tool(func_name, func_args)
                    result_str = result[:500] if len(result) > 500 else result
                    print(f"  [结果] {result_str[:100]}...")

                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": func_name,
                        "content": result,
                    })

                # 添加助手消息和工具结果到历史
                messages.append(assistant_message)
                messages.extend(tool_results)

            else:
                # 没有工具调用，返回最终响应
                final_response = assistant_message.content
                self.history.append({"role": "assistant", "content": final_response})
                return final_response

        return "达到最大工具调用轮数限制"

    def reset(self):
        """重置对话历史"""
        self.history = []
        print("[Agent] 对话历史已重置")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="OpenAI Skill Agent 测试")
    parser.add_argument("--config", "-c", type=Path, default=None, help="模型配置文件路径")
    parser.add_argument("--query", "-q", type=str, default=None, help="单次查询")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互模式")

    args = parser.parse_args()

    # 创建 agent
    agent = OpenAISkillAgent(config_path=args.config)

    if args.query:
        # 单次查询
        print(f"\n查询：{args.query}")
        response = agent.chat(args.query)
        print(f"\nAgent: {response}")
    elif args.interactive:
        # 交互模式
        print("\n" + "="*50)
        print("OpenAI Skill Agent 交互测试")
        print("="*50)
        print("命令：/quit 退出，/reset 清空历史，/show 显示历史")
        print("-"*50)

        while True:
            try:
                user_input = input("\n你：").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n再见！")
                break

            if user_input.lower() == "/quit" or user_input.lower() == "/exit":
                print("再见！")
                break
            elif user_input.lower() == "/reset":
                agent.reset()
                continue
            elif user_input.lower() == "/show":
                if agent.history:
                    print("\n--- 对话历史 ---")
                    for i, h in enumerate(agent.history, 1):
                        role = "你" if h["role"] == "user" else "Agent"
                        content = h["content"][:80] + "..." if len(h["content"]) > 80 else h["content"]
                        print(f"[{i}] {role}: {content}")
                    print("---")
                else:
                    print("[历史] 空")
                continue

            if not user_input:
                continue

            response = agent.chat(user_input)
            print(f"Agent: {response}")
    else:
        # 默认显示帮助
        parser.print_help()


if __name__ == "__main__":
    main()
