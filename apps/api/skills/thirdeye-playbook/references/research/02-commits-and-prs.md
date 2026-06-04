# ThirdEye 变更与演进分析

## 变更模式

### 1. 版本策略

**证据来源**：
- `apps/api/app/schemas/playbook.py` - PlaybookMetadata.version

**版本规范**：
```python
@field_validator("version")
@classmethod
def validate_version(cls, value: str) -> str:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError("version must use semantic version format, e.g. 1.0.0")
    return value
```

**判断**：强制语义化版本，拒绝非标准格式

### 2. Playbook ID 生成

**证据来源**：
- `apps/api/app/services/playbook_generator.py`

```python
playbook_id = f"pb_{project.slug}_v1"
```

**命名策略**：
- 前缀 `pb_` 标识 Playbook
- 使用项目 slug 保证唯一性
- 版本号直接嵌入 ID（当前固定为 v1）

### 3. 证据 ID 稳定性

**证据来源**：
- `apps/api/app/services/evidence_builder.py`

```python
def _stable_id(self, project_id: str, path: str, symbol: str) -> str:
    digest = hashlib.sha1(f"{project_id}:{path}:{symbol}".encode("utf-8")).hexdigest()[:12]
    return f"ev_{digest}"
```

**判断**：使用稳定哈希 ID，确保同一证据多次生成 ID 一致

## 回退机制

### LLM 蒸馏失败处理

**证据来源**：
- `apps/api/app/api/playbooks.py`

```python
try:
    artifacts = asyncio.run(
        run_playbook_distillation(project, scan, evidence, generator, provider_config=provider)
    )
except Exception as error:
    if provider is None:
        raise
    artifacts = generator.generate(project, scan, evidence)
    artifacts.metadata.execution_mode = "deterministic"
    artifacts.metadata.resolved_provider_id = None
    artifacts.metadata.execution_note = f"LLM distillation failed and fell back to deterministic mode: {summarize_provider_error(error)}"
```

**变更策略**：
- LLM 失败时自动回退到确定性生成
- 记录失败原因到 `execution_note`
- 不中断流程，保证 MVP 可用性

## 分块处理策略

**证据来源**：
- `apps/api/app/agents/sdk_distillation.py`

```python
MAX_CONTEXT_TOKENS = 256_000
TARGET_CONTEXT_TOKENS = 180_000
CHARS_PER_TOKEN_ESTIMATE = 4

def _chunk_project_file_payloads(project_files: list[dict[str, str]], token_budget: int) -> list[list[dict[str, str]]]:
    # 分块逻辑
```

**判断**：
- 预估 token 数，超过阈值时分块处理
- 先分块蒸馏，再合并结果
- 每块预算：`TARGET_CONTEXT_TOKENS - base_tokens`

## 信息不足

- 没有 CHANGELOG 或 release notes 证据
- 无法从当前代码判断历史演进路径
- 需要更多 git 历史来确认风格演化
