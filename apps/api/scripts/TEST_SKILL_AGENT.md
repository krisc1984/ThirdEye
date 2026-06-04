# Skill Agent 测试脚本

## 测试脚本列表

| 脚本 | 用途 | 模式 |
|------|------|------|
| `test_skill_agent_openai.py` | 原生 OpenAI 客户端测试（推荐） | 交互/单次 |
| `test_skill_agent_simple.py` | 简易多轮对话测试（使用 agents 库） | 交互/单次 |
| `test_skill_agent_multi_turn.py` | 完整多轮对话测试（使用 agents 库） | 交互/场景 |

## 快速开始

### 1. 原生 OpenAI 客户端测试（推荐）

```bash
cd apps/api

# 单次查询
uv run python scripts/test_skill_agent_openai.py \
  -c ../../data/model-providers/xunfei.json \
  -q "列出可用的 skills"

# 交互模式
uv run python scripts/test_skill_agent_openai.py \
  -c ../../data/model-providers/xunfei.json \
  -i
```

**交互命令**:
- `/quit` - 退出
- `/reset` - 清空对话历史
- `/show` - 显示对话历史

### 2. 简易测试（使用 agents 库）

```bash
# 交互模式
uv run python scripts/test_skill_agent_simple.py

# 使用配置文件
uv run python scripts/test_skill_agent_simple.py -c ../../data/model-providers/xunfei.json

# 单次查询
uv run python scripts/test_skill_agent_simple.py -q "当前项目有哪些技能？"
```

**注意**: 如果 agents 库与某些 API 不兼容，请使用原生 OpenAI 客户端版本。

### 3. 完整测试（使用 agents 库）

```bash
# 交互模式
uv run python scripts/test_skill_agent_multi_turn.py

# 预设场景测试
uv run python scripts/test_skill_agent_multi_turn.py -s code_review
uv run python scripts/test_skill_agent_multi_turn.py -s project_exploration
uv run python scripts/test_skill_agent_multi_turn.py -s skill_usage

# 指定最大轮数
uv run python scripts/test_skill_agent_multi_turn.py -n 10

# 保存对话
uv run python scripts/test_skill_agent_multi_turn.py -o conversation.json
```

## 预设场景

### code_review
代码审查场景，测试多轮代码分析能力：
1. 帮我看看当前目录下有哪些 Python 文件
2. 这些文件中哪个包含测试代码？
3. 能分析一下测试代码的覆盖率吗？
4. 如何改进测试覆盖率？

### project_exploration
项目探索场景，测试项目理解能力：
1. 当前项目使用什么技术栈？
2. 后端使用的是什么框架？
3. 前端框架是什么版本？
4. 项目的目录结构是怎样的？

### skill_usage
技能使用场景，测试 skill 加载能力：
1. 你有哪些可用的技能？
2. 加载 code-review 技能
3. 使用这个技能帮我分析一下项目代码质量
4. 有什么改进建议？

## 输出示例

### 简易测试

```
$ uv run python scripts/test_skill_agent_simple.py

[配置] 已加载模型配置：xunfei
[配置] 创建 Agent...
[配置] 已加载 5 个 skills
  Skills: agent-builder, code-review, mcp-builder, oss-skill, pdf

==================================================
简易多轮对话测试
==================================================
输入 '/quit' 退出，'/clear' 清空历史，'/show' 显示历史
--------------------------------------------------

[第 1 轮] 你：当前有哪些技能？
[第 1 轮] 思考中...
[第 1 轮] Agent: 当前可用技能如下：
1. agent-builder - Design and build AI agents...
...
```

### 场景测试

```
$ uv run python scripts/test_skill_agent_multi_turn.py -s code_review

============================================================
多轮对话测试 - 场景模式
============================================================

[场景 1/4] 用户：帮我看看当前目录下有哪些 Python 文件
[场景 1/4] Agent: 当前目录下的 Python 文件有...

[场景 2/4] 用户：这些文件中哪个包含测试代码？
[场景 2/4] Agent: 包含测试代码的文件是...
...
```

## 对话历史保存

测试完成后，对话历史会自动保存为 JSON 文件：

```json
{
  "model": "astron-code-latest",
  "config_path": ".../xunfei.json",
  "turn_count": 4,
  "timestamp": "2026-05-08T10:30:00",
  "history": [
    {"role": "user", "content": "问题 1"},
    {"role": "assistant", "content": "回答 1"},
    ...
  ]
}
```

## 自定义场景

可以在 `test_skill_agent_multi_turn.py` 中添加自定义场景：

```python
SCENARIOS = {
    "my_custom_scenario": [
        "问题 1",
        "问题 2",
        "问题 3",
    ],
}
```

然后运行：

```bash
uv run python scripts/test_skill_agent_multi_turn.py -s my_custom_scenario
```

## 故障排查

### 模型配置加载失败

确保配置文件路径正确：

```bash
# 检查文件是否存在
ls ../../data/model-providers/xunfei.json
```

### Agent 创建失败

检查 API key 和 base_url 是否正确：

```python
from skill_agent import load_model_config
config = load_model_config()
print(config)
```

### 对话无响应

可能是 API 调用超时，增加 `--max-turns` 参数或检查网络连接。
