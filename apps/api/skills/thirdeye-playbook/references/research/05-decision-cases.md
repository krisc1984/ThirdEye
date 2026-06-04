# ThirdEye 关键决策分析

## 决策 1: 确定性回退 vs 纯 LLM

**决策内容**：当 LLM 蒸馏失败时，回退到确定性生成

**证据来源**：
- `apps/api/app/api/playbooks.py`
- `apps/api/app/services/playbook_generator.py`

**决策逻辑**：
```python
try:
    artifacts = asyncio.run(run_playbook_distillation(...))
except Exception as error:
    if provider is None:
        raise
    artifacts = generator.generate(project, scan, evidence)  # 确定性回退
    artifacts.metadata.execution_mode = "deterministic"
    artifacts.metadata.execution_note = f"LLM distillation failed...: {summarize_provider_error(error)}"
```

**取舍分析**：
| 选项 | 优点 | 缺点 |
|------|------|------|
| 纯 LLM | 质量可能更高 | 完全依赖外部服务，失败则无法使用 |
| 确定性回退 | 保证 MVP 可用性 | 回退质量较低 |
| **选择** | ✅ 保证基本功能可用 | 接受回退质量较低 |

**判断**：MVP 阶段可用性优先于质量

---

## 决策 2: 本地 JSON 存储 vs 数据库

**决策内容**：使用本地 JSON/Markdown 文件存储数据

**证据来源**：
- `README.md` - 技术栈
- `apps/api/app/services/storage.py`（推断）

**取舍分析**：
| 选项 | 优点 | 缺点 |
|------|------|------|
| 数据库 | 查询效率高，适合生产 | 增加部署复杂度，需要迁移管理 |
| 本地 JSON | 零配置，易于开发调试 | 不适合高并发，无事务保证 |
| **选择** | ✅ MVP 简单性优先 | 明确标注"不适合生产" |

**判断**：MVP 阶段追求最小部署复杂度

---

## 决策 3: 证据分级体系

**决策内容**：引入四级证据分级（confirmed/inferred/preference/unknown）

**证据来源**：
- `apps/api/app/schemas/playbook.py`

**决策逻辑**：
```python
EvidenceLevel = Literal["confirmed", "inferred", "preference", "unknown"]
```

**取舍分析**：
| 选项 | 优点 | 缺点 |
|------|------|------|
| 二元分级（真/假） | 简单 | 无法表达不确定性 |
| 四级分级 | 精确表达可信度 | 增加复杂度 |
| **选择** | ✅ 诚实表达不确定性 | 需要使用者理解分级含义 |

**判断**：追求诚实的工程判断，不掩盖不确定性

---

## 决策 4: 文件扫描限制

**决策内容**：限制扫描的文件类型和大小

**证据来源**：
- `apps/api/app/services/project_scanner.py`

```python
MAX_FILE_SIZE_BYTES = 512 * 1024  # 512KB
LANGUAGE_BY_SUFFIX = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".kt", ".md"}
```

**取舍分析**：
| 选项 | 优点 | 缺点 |
|------|------|------|
| 全文件扫描 | 不遗漏 | 性能差，可能包含敏感文件 |
| 白名单 + 大小限制 | 性能好，安全 | 可能遗漏特殊文件 |
| **选择** | ✅ 性能和安全优先 | 需要时可扩展白名单 |

**判断**：MVP 阶段追求性能和安全性

---

## 决策 5: 明确非目标

**决策内容**：明确列出不做的功能

**证据来源**：
- `README.md` - 明确非目标

```markdown
## 明确非目标

- 不做 PR review
- 不做 diff review
- 不接入 GitHub/GitLab
- 不自动修改代码
- 不做 IDE 插件
- 不做多人审批流
```

**决策逻辑**：防止范围蔓延，聚焦核心价值

**判断**：克制功能冲动，聚焦 MVP 核心价值主张

---

## 决策 6: Agent 分块处理

**决策内容**：当上下文过大时，分块蒸馏再合并

**证据来源**：
- `apps/api/app/agents/sdk_distillation.py`

```python
MAX_CONTEXT_TOKENS = 256_000
TARGET_CONTEXT_TOKENS = 180_000

if estimated_tokens <= TARGET_CONTEXT_TOKENS:
    response = await _request_orchestrated_distillation(provider_config, payload)
else:
    # 分块处理
    chunks = _chunk_project_file_payloads(project_file_payloads, per_chunk_budget)
    for index, chunk in enumerate(chunks, start=1):
        chunk_outputs.append(await _request_chunk_distillation(...))
    response = await _request_merge_distillation(...)
```

**取舍分析**：
| 选项 | 优点 | 缺点 |
|------|------|------|
| 单次请求 | 简单，上下文完整 | 可能超出 token 限制 |
| 分块 + 合并 | 处理大项目 | 增加复杂度，可能丢失跨文件上下文 |
| **选择** | ✅ 支持大项目 | 实现复杂度高 |

**判断**：为支持大项目，接受实现复杂度
