# Skill Agent - 使用 OpenAI Agent SDK 调用 skill

基于 `s05_skill_loading.py` 的双层 skill 注入逻辑，使用 OpenAI Agent SDK 实现。

## 核心思想

**不要把所有内容都放在 system prompt 中，按需加载**

### 双层注入架构

```
Layer 1 (cheap): skill 名称和描述在 system prompt (~100 tokens/skill)
Layer 2 (on demand): 完整 skill body 在 tool_result 中返回
```

```
System prompt:
+--------------------------------------+
| You are a coding agent.              |
| Skills available:                    |
|   - git: Git workflow helpers        |  <-- Layer 1: metadata only
|   - test: Testing best practices     |
+--------------------------------------+

当模型调用 load_skill("git") 时:
+--------------------------------------+
| tool_result:                         |
| <skill>                              |
|   Full git workflow instructions...  |  <-- Layer 2: full body
|   Step 1: ...                        |
|   Step 2: ...                        |
| </skill>                             |
+--------------------------------------+
```

## 快速开始

### 1. 安装依赖

```bash
cd apps/api
uv sync
```

确保已安装 `openai-agents`：

```bash
uv add openai-agents
```

### 2. 配置环境变量

在 `.env` 文件中配置：

```bash
# OpenAI API 配置
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1  # 可选，用于兼容 API

# 或者使用本地模型
# OPENAI_BASE_URL=http://localhost:1234/v1
```

### 2.1 使用配置文件（推荐）

也可以直接使用 JSON 配置文件（如讯飞模型配置）：

```bash
# 使用配置文件运行
uv run python scripts/skill_agent.py --config ../../data/model-providers/xunfei.json "查询内容"
```

配置文件格式示例 (`xunfei.json`)：

```json
{
  "api_key": "your-api-key",
  "base_url": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
  "model": "astron-code-latest",
  "provider_type": "openai_compatible",
  "timeout_seconds": 60
}
```

### 3. 准备 Skills

将 skill 文件放在 `.skills/` 目录下：

```
.skills/
├── code-reviewer.md
├── security-auditor.md
├── test-engineer.md
└── ...
```

每个 skill 文件使用 YAML frontmatter 格式：

```markdown
---
name: code-reviewer
description: 代码审查专家
tags: review, quality
---

# Code Reviewer Skill

## 审查流程

1. 首先检查代码风格...
2. 然后检查潜在 bug...
3. 最后检查性能问题...
```

### 4. 运行脚本

#### 交互模式

```bash
cd apps/api
uv run python scripts/skill_agent.py
```

#### 命令行模式

```bash
# 单行查询
uv run python scripts/skill_agent.py "帮我检查当前目录下的 Python 文件"

# 使用配置文件
uv run python scripts/skill_agent.py --config ../../data/model-providers/xunfei.json "帮我检查当前目录下的 Python 文件"

# 列出 skills
uv run python scripts/skill_agent.py --list
```

#### 运行示例

```bash
uv run python scripts/skill_agent_example.py
```

## API 使用

### 同步 API

```python
from skill_agent import run_skill_agent_sync

# 使用默认配置（从配置文件加载）
result = run_skill_agent_sync(
    "列出当前目录下的所有测试文件",
    # config_path=Path("../../data/model-providers/xunfei.json"),  # 可选
)
print(result)

# 或者手动指定 API 配置
result = run_skill_agent_sync(
    "列出当前目录下的所有测试文件",
    model="gpt-4o",
    api_key="your-api-key",
    base_url="http://localhost:1234/v1",
)
```

### 异步 API

```python
import asyncio
from skill_agent import create_openai_agent_with_skills, run_skill_agent
from agents import Runner

async def main():
    # 创建 agent
    agent, loader, tools = create_openai_agent_with_skills(
        model="gpt-4o",
    )

    # 运行 agent
    result = await run_skill_agent("分析项目结构", agent, loader)
    print(result)

asyncio.run(main())
```

### 直接使用 SkillLoader

```python
from pathlib import Path
from skill_agent import SkillLoader

loader = SkillLoader(Path.cwd() / ".skills")

# 列出所有 skills
print(loader.list_skills())

# 获取 skill 描述（Layer 1）
print(loader.get_descriptions())

# 获取 skill 完整内容（Layer 2）
print(loader.get_content("code-reviewer"))
```

## 可用工具

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `bash` | 执行 shell 命令 | `command`: 命令字符串 |
| `read_file` | 读取文件 | `path`: 文件路径，`limit`: 最大行数（可选） |
| `write_file_chunk` | 分块写入文件 | `path`: 文件路径，`content`: 本次文本块，`mode`: `overwrite` 或 `append` |
| `replace_in_file` | 定点替换文件内容 | `path`: 文件路径，`old_text`: 原文本，`new_text`: 新文本 |
| `load_skill` | 加载 skill | `name`: skill 名称 |
| `list_skills` | 列出所有 skills | 无参数 |

## 自定义 Agent

```python
from openai import OpenAI
from agents import Agent, function_tool
from skill_agent import SkillLoader, WORKDIR

# 初始化
loader = SkillLoader(WORKDIR / ".skills")
client = OpenAI(api_key="your-key")

# 构建 system prompt（包含 Layer 1 skill 元数据）
skill_descriptions = loader.get_descriptions()
system_prompt = f"""You are a helpful assistant.

Available skills:
{skill_descriptions}

Use load_skill to get detailed instructions.
"""

# 定义自定义工具
@function_tool
def my_custom_tool() -> str:
    return "Custom result"

# 创建自定义 agent
agent = Agent(
    name="MyAgent",
    instructions=system_prompt,
    model="gpt-4o",
    tools=[my_custom_tool],
    client=client,
)
```

## 架构说明

### 模块结构

```
scripts/
├── skill_agent.py          # 核心模块
│   ├── SkillLoader         # skill 加载器
│   ├── create_openai_agent_with_skills()  # 创建 agent
│   ├── run_skill_agent()   # 异步运行
│   └── run_skill_agent_sync()  # 同步运行
├── skill_agent_example.py  # 使用示例
└── SKILL_AGENT_README.md   # 本文档
```

### 工具执行流程

```
用户查询
    │
    ▼
Agent 处理 → 决定使用工具
    │
    ▼
工具调用 (load_skill)
    │
    ▼
SkillLoader.get_content()
    │
    ▼
返回完整 skill body
    │
    ▼
Agent 根据 skill 指导执行任务
    │
    ▼
返回结果
```

## 与 Anthropic 版本的区别

| 特性 | Anthropic (原版本) | OpenAI Agent SDK (新版本) |
|------|-------------------|-------------------------|
| 客户端 | `anthropic.Anthropic` | `openai.OpenAI` + `agents` |
| Agent 抽象 | 手动实现 agent 循环 | `Agent` 类 + `Runner` |
| 工具调用 | 手动处理 `tool_use` | 自动处理工具调用 |
| 消息历史 | 手动管理 | `Runner.run()` 自动管理 |
| 工具定义 | 手动定义 schema | `@function_tool` 装饰器 |
| 流式输出 | 支持 | 支持（通过 `Runner`） |

## 故障排查

### Skills 未加载

检查 `.skills/` 目录是否存在，文件是否为 `.md` 格式。

### API 调用失败

1. 检查 `OPENAI_API_KEY` 环境变量
2. 检查 `base_url` 是否正确（用于兼容 API）
3. 检查模型名称是否有效

### 工具调用失败

1. 确保文件路径在工作目录内（安全限制）
2. 检查命令是否包含危险操作（会被阻止）

## 参考

- [s05_skill_loading.py](../../../opencode/learn-claude-code/agents/s05_skill_loading.py) - 原始 Anthropic 实现
- [OpenAI Agents SDK](https://github.com/openai/openai-agents-python) - OpenAI Agents SDK 文档
