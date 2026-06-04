# ThirdEye 架构分析

## 核心架构维度

### 1. 项目结构边界

**证据来源**：
- `apps/api/app/services/project_scanner.py` - 项目扫描逻辑
- `apps/api/app/services/ignore_rules.py` - 忽略规则定义
- `apps/api/app/schemas/project.py` - 项目数据结构

**架构判断**：
- 明确区分 `apps/api` 和 `apps/web` 两个独立应用
- 数据层统一存放在 `data/` 目录，与代码分离
- 使用 `Path.resolve()` 确保路径安全，防止路径逃逸

**边界划分策略**：
```python
# 路径安全校验
candidate = (root / relative_path).resolve()
if candidate != root and root not in candidate.parents:
    continue  # 拒绝路径逃逸
```

### 2. 分层架构

**证据来源**：
- `apps/api/app/` 目录结构

```
app/
├── agents/          # AI Agent 逻辑（distillation, review）
├── api/             # FastAPI 路由层
├── core/            # 核心配置
├── model_providers/ # 模型提供商适配
├── schemas/         # Pydantic 数据模型
├── services/        # 业务服务层
└── templates/       # 模板文件
```

**分层原则**：
- `api/` 层只负责路由和请求/响应转换
- `services/` 层封装核心业务逻辑（扫描、证据构建、Playbook 生成）
- `agents/` 层封装 AI 驱动的蒸馏和评审逻辑
- `schemas/` 层定义所有数据结构，使用 Pydantic 进行验证

### 3. 依赖策略

**证据来源**：
- `apps/api/app/services/ignore_rules.py` - DEFAULT_IGNORE_PATTERNS
- `apps/api/app/services/project_scanner.py` - 语言支持列表

**依赖偏好**：
- 最小化外部依赖：使用标准库 `fnmatch`、`hashlib`、`pathlib`
- 核心依赖只有：FastAPI、Pydantic、OpenAI SDK
- 明确拒绝的文件类型：二进制文件、大型文件（>512KB）

### 4. 状态管理

**证据来源**：
- `apps/api/app/schemas/playbook.py` - PlaybookMetadata

**状态策略**：
- 无状态服务设计：Scanner、EvidenceBuilder、PlaybookGenerator 都是无状态类
- 数据持久化通过 `JsonStorage` 统一处理
- Playbook 状态使用枚举：`draft | active | archived`

### 5. 抽象深度

**证据观察**：
- 适度的抽象：每个服务类职责单一
- 拒绝过度抽象：没有复杂的继承层次
- 数据模型使用 Pydantic BaseModel，提供验证但不引入复杂 ORM

**抽象边界**：
```python
# 简单清晰的接口
class ProjectScanner:
    def scan(self, root_path: Path | str, extra_ignore_patterns: list[str] | None = None) -> ProjectScanSummary

class EvidenceBuilder:
    def build(self, project_id: str, scan: ProjectScanSummary) -> list[EvidenceItem]
```

## 架构决策记录

| 决策点 | 选择 | 拒绝 | 证据 |
|--------|------|------|------|
| 数据存储 | 本地 JSON/Markdown | 数据库 | MVP 简单性优先 |
| 路径处理 | pathlib.Path | os.path | 类型安全、跨平台 |
| 数据验证 | Pydantic | 手动验证 | 统一验证逻辑 |
| AI 集成 | OpenAI SDK + 回退机制 | 仅依赖 LLM | 确定性回退 |
| 文件扫描 | 白名单语言 + 大小限制 | 全文件扫描 | 性能和安全性 |

## 信息不足

- `storage.py` 完整实现未读取
- `review.py` agent 完整逻辑未读取
- 前端架构细节未分析
