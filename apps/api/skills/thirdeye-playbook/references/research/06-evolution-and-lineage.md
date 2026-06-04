# ThirdEye 演化与谱系分析

## 方法论来源

**证据来源**：
- `README.md` - 致谢

```markdown
## 致谢

本项目借鉴 [`oss-skill`](https://github.com/lianchi/oss-skill) 的方法论和实现思路。
```

**谱系**：
```
oss-skill (lianchi/oss-skill)
    └── ThirdEye (本项目)
        └── 目标：将 oss-skill 方法论应用于本地项目评审
```

## 演化阶段推断

基于代码结构和注释，推断项目演化阶段：

### 阶段 1: MVP 基础架构（当前）

**特征**：
- 确定性工作流为基础
- LLM 增强为可选能力
- 本地 JSON 存储
- 基础扫描和证据构建

**证据**：
```python
# README.md - MVP 限制
- 当前以 deterministic workflow 为基础，provider 增强能力仍是轻量封装
- 数据存储仍为本地 JSON/Markdown，不适合生产
```

### 阶段 2: Agent 增强（进行中）

**特征**：
- `apps/api/app/agents/` 目录存在
- `sdk_distillation.py` 实现分块蒸馏逻辑
- 支持多种 provider 配置

**证据**：
```python
# sdk_distillation.py
async def run_agent_distillation(...) -> dict[str, object]:
    # 完整的分块蒸馏和合并逻辑
```

### 阶段 3: 生产化（未来，未实现）

**预期特征**（基于当前限制推断）：
- 加密存储或 secret manager
- 完整的 agentic reasoning 系统
- 生产级数据存储

**证据**：
```python
# README.md - MVP 限制
- 生产环境应改为使用加密存储或 secret manager
- Review 结果目前以项目规则和基础 heuristics 为主，不是完整 agentic reasoning 系统
```

## 影响关系

### ThirdEye 受 oss-skill 影响

**影响维度**：
1. **方法论**：从代码和维护痕迹中蒸馏工程判断
2. **证据分级**：`confirmed | inferred | preference | unknown`
3. **Playbook 概念**：生成可复用的评审规则集
4. **诚实边界**：证据不足时明确说明

### ThirdEye 对 oss-skill 的扩展

**扩展维度**：
1. **应用场景**：从"蒸馏开源作者"扩展到"蒸馏本地项目"
2. **自动化**：将方法论封装为可运行的 API 服务
3. **证据构建**：自动扫描项目并构建证据库
4. **评审集成**：将 Playbook 用于实际的技术方案评审

## 风格形成

### 代码风格特征

**观察**：
- 类型注解完整：`from __future__ import annotations`
- 使用 Pydantic 进行数据验证
- 服务类无状态设计
- 错误处理明确

**示例**：
```python
from __future__ import annotations

from collections import Counter
from pathlib import Path

class ProjectScanner:
    def scan(self, root_path: Path | str, extra_ignore_patterns: list[str] | None = None) -> ProjectScanSummary:
        # 清晰的接口定义
```

### 架构风格特征

**观察**：
- 分层清晰：api/services/agents/schemas
- 职责单一：每个服务类只做一件事
- 依赖注入：通过构造函数传入依赖

**示例**：
```python
class PlaybookGenerator:
    def __init__(self, storage: JsonStorage) -> None:
        self.storage = storage

    def generate(self, project: Project, scan: ProjectScanSummary, evidence: list[EvidenceItem]) -> PlaybookArtifacts:
        # 单一职责
```

## 信息不足

- 没有 git 历史，无法确认实际演化路径
- 没有 issue/PR 讨论，无法确认决策过程
- 无法确认 oss-skill 的具体影响深度
