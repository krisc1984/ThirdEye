#!/usr/bin/env python3
"""
skill_agent_example.py - Skill Agent 使用示例

展示如何使用 OpenAI Agent SDK 调用 skill 执行 agent 任务
"""

import asyncio
from pathlib import Path

# 导入 skill_agent 模块
from skill_agent import (
    SkillLoader,
    create_openai_agent_with_skills,
    run_skill_agent,
    run_skill_agent_sync,
)


def example_1_basic_usage():
    """示例 1: 基本用法 - 使用同步 API"""
    print("\n" + "=" * 60)
    print("示例 1: 基本用法 - 同步 API")
    print("=" * 60)

    query = "列出当前目录下的所有 Python 文件"
    result = run_skill_agent_sync(
        query,
        model="gpt-4o",  # 替换为你的模型
        # api_key="your-api-key",  # 可选
        # base_url="http://localhost:1234/v1",  # 可选，用于本地模型
    )
    print(f"结果：{result}")


def example_2_list_skills():
    """示例 2: 列出所有可用的 skills"""
    print("\n" + "=" * 60)
    print("示例 2: 列出所有可用的 skills")
    print("=" * 60)

    loader = SkillLoader(Path.cwd() / ".skills")
    print("\n可用 skills:")
    for name in loader.list_skills():
        skill = loader.skills.get(name, {})
        meta = skill.get("meta", {})
        desc = meta.get("description", "无描述")
        print(f"  - {name}: {desc}")


def example_3_load_skill():
    """示例 3: 加载特定 skill 的内容"""
    print("\n" + "=" * 60)
    print("示例 3: 加载特定 skill 的内容")
    print("=" * 60)

    loader = SkillLoader(Path.cwd() / ".skills")

    # 尝试加载一个 skill
    skill_name = "code-reviewer"  # 替换为实际存在的 skill
    content = loader.get_content(skill_name)
    print(f"\nSkill '{skill_name}' 内容:")
    print(content[:500] + "..." if len(content) > 500 else content)


async def example_4_async_usage():
    """示例 4: 异步用法"""
    print("\n" + "=" * 60)
    print("示例 4: 异步用法")
    print("=" * 60)

    # 创建 agent
    agent, loader, tools = create_openai_agent_with_skills(
        model="gpt-4o",
        # api_key="your-api-key",
        # base_url="http://localhost:1234/v1",
    )

    # 运行 agent
    query = "帮我检查当前目录下是否有测试文件"
    result = await run_skill_agent(query, agent, loader)
    print(f"结果：{result}")


def example_5_custom_tools():
    """示例 5: 添加自定义工具"""
    print("\n" + "=" * 60)
    print("示例 5: 添加自定义工具")
    print("=" * 60)

    from agents import function_tool

    # 定义自定义工具函数
    @function_tool
    def get_project_info() -> str:
        """获取当前项目的基本信息"""
        return "ThirdEye - AI 技术评审系统"

    @function_tool
    def analyze_code_quality(file_path: str) -> str:
        """分析指定文件的代码质量"""
        return f"分析文件：{file_path}"

    print("自定义工具已定义:")
    print(f"  - {get_project_info.name}: {get_project_info.description}")
    print(f"  - {analyze_code_quality.name}: {analyze_code_quality.description}")


def example_6_batch_queries():
    """示例 6: 批量查询"""
    print("\n" + "=" * 60)
    print("示例 6: 批量查询")
    print("=" * 60)

    queries = [
        "当前项目使用什么技术栈？",
        "有哪些测试文件？",
        "项目的目录结构是怎样的？",
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] 查询：{query}")
        # result = run_skill_agent_sync(query)
        # print(f"结果：{result}")
        print("(跳过实际执行，避免过多 API 调用)")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("Skill Agent 使用示例")
    print("=" * 60)

    # 运行示例
    example_2_list_skills()
    example_3_load_skill()
    example_5_custom_tools()
    example_6_batch_queries()

    print("\n" + "=" * 60)
    print("所有示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
