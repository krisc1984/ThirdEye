# ThirdEye 评审与决策分析

## 证据分级体系

**证据来源**：
- `apps/api/app/schemas/playbook.py` - EvidenceLevel

```python
EvidenceLevel = Literal["confirmed", "inferred", "preference", "unknown"]
```

**分级定义**：
| 级别 | 含义 | 使用场景 |
|------|------|----------|
| confirmed | 有明确代码证据 | 直接从代码/文档提取的事实 |
| inferred | 基于行为的推断 | 从代码模式推断的偏好 |
| preference | 可配置的偏好 | 可调整的规则或设置 |
| unknown | 证据不足 | 无法确定的判断 |

## 规则严重性分级

**证据来源**：
- `apps/api/app/schemas/playbook.py` - RuleSeverity

```python
RuleSeverity = Literal["blocker", "major", "minor", "nit"]
```

**分级策略**：
- `blocker`: 必须修复，阻止通过
- `major`: 重要问题，建议修复
- `minor`: 次要问题
- `nit`: 细微改进建议

## 敏感信息处理

**证据来源**：
- `apps/api/app/services/project_scanner.py` - SENSITIVE_NAMES
- `apps/api/app/services/secret_scanner.py`（推断）

```python
SENSITIVE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_dsa",
    "secrets.json",
}
```

**处理策略**：
- 敏感文件不纳入证据
- 发现敏感内容时记录警告，不记录具体内容
- 审计日志中对密钥做脱敏处理

## 文件扫描决策

**证据来源**：
- `apps/api/app/services/project_scanner.py`

**接受的文件**：
- 语言文件：`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.rs`, `.java`, `.kt`
- 文档：`.md`
- 配置文件：`package.json`, `tsconfig.json`, `pyproject.toml`, `requirements.txt`, `dockerfile` 等

**拒绝的文件**：
- 二进制文件：`.png`, `.jpg`, `.jpeg`, `.gif`, `.pdf`, `.zip`
- 日志文件：`.log`
- 大文件：> 512KB
- 敏感文件：`.env*`, 私钥等

**忽略的目录**：
```python
DEFAULT_IGNORE_PATTERNS = [
    ".git", "node_modules", "dist", "build", ".next", ".venv", "__pycache__",
]
```

## 项目文件选择策略（Agent 蒸馏）

**证据来源**：
- `apps/api/app/agents/sdk_distillation.py`

```python
def _candidate_priority(relative_path: str, scan: ProjectScanSummary) -> tuple[int, str]:
    lower = relative_path.lower()
    if lower in {item.lower() for item in scan.docs}:
        return (0, relative_path)  # 文档优先
    if lower in {item.lower() for item in scan.entrypoint_candidates}:
        return (1, relative_path)  # 入口文件
    if lower in {item.lower() for item in scan.tests}:
        return (2, relative_path)  # 测试
    if lower in {item.lower() for item in scan.config_files}:
        return (3, relative_path)  # 配置
    if "src/" in lower or "/src/" in lower:
        return (4, relative_path)  # 源码
    return (5, relative_path)  # 其他
```

**优先级判断**：
1. 文档（README, design doc）- 理解项目意图
2. 入口文件 - 理解架构入口
3. 测试文件 - 理解预期行为
4. 配置文件 - 理解工具链和约束
5. src/ 源码 - 核心实现
6. 其他

**数量限制**：
- `MAX_PROJECT_FILES = 24` - 最多读取 24 个文件
- `MAX_READ_CHARS = 12000` - 单文件最多 12KB

## 明确非目标（项目定位）

**证据来源**：
- `README.md`

```markdown
## 明确非目标

- 不做 PR review
- 不做 diff review
- 不接入 GitHub/GitLab
- 不自动修改代码
- 不做 IDE 插件
- 不做多人审批流
```

**判断**：明确边界，拒绝范围蔓延
