# ThirdEye 文档与原则分析

## 核心原则

**证据来源**：
- `README.md` - 开发原则

```markdown
## 开发原则

1. 代码优先，再读文档
2. 多源采集：代码、文档、测试、配置
3. 证据分级：`confirmed | inferred | preference | unknown`
4. 证据不足时明确暴露不确定性
5. 敏感内容不进入证据摘要和审计日志
```

**原则解读**：

### 1. 代码优先
- 第一手证据是代码本身
- 文档用于补充和验证，不作为唯一来源
- 当代码行为与文档冲突时，以代码为准

### 2. 多源采集
- 不依赖单一来源
- 代码、文档、测试、配置相互印证
- 提高结论的可信度

### 3. 证据分级
- 明确区分事实和推断
- 不将推测包装为确定结论
- 允许"unknown"状态存在

### 4. 诚实边界
- 证据不足时明确说明
- 不虚构确定性
- 承认推断的局限性

### 5. 安全优先
- 敏感信息不进入日志
- 密钥脱敏处理
- 审计日志也需遵守安全规则

## 方法论来源

**证据来源**：
- `README.md` - 致谢部分

```markdown
## 致谢

本项目借鉴 [`oss-skill`](https://github.com/lianchi/oss-skill) 的方法论和实现思路。
```

**方法论继承**：
- 从开源作者/仓库蒸馏工程判断
- 生成可复用的 Playbook/Skill
- 用于技术方案评审

## MVP 定位

**证据来源**：
- `README.md` - MVP 能力

```markdown
## MVP 能力

- 本地项目扫描：读取代码、文档、测试、配置并生成项目概览
- Playbook 蒸馏：产出 `playbook.skill.md`、规则、证据和 metadata
- Playbook 管理：浏览列表、查看详情、查看证据
- 技术方案评审：基于选定 playbook 返回结构化评审结果
- 模型提供方配置：支持 OpenAI 与 OpenAI-compatible provider
- 本地审计日志：记录蒸馏与评审事件，并对密钥与敏感文本做脱敏
```

**MVP 限制**：
```markdown
## MVP 限制

- 当前以 deterministic workflow 为基础，provider 增强能力仍是轻量封装
- Provider 连接测试是配置校验，不是完整的真实模型调用验证
- 数据存储仍为本地 JSON/Markdown，不适合生产
- Review 结果目前以项目规则和基础 heuristics 为主，不是完整 agentic reasoning 系统
```

## 技术栈选择

**证据来源**：
- `README.md`

```markdown
## 技术栈

- 后端：Python 3.12+, FastAPI, Pydantic, OpenAI Agents SDK
- 前端：Next.js 15, React 19, TypeScript
- 存储：本地文件系统 JSON/Markdown artifacts
```

**选择判断**：
- 后端：Python 生态成熟，适合 AI 集成
- 前端：Next.js 15 + React 19 - 追求最新稳定特性
- 存储：MVP 阶段简单优先，避免数据库复杂度

## 快速启动设计

**证据来源**：
- `README.md` - 快速开始

```bash
# 后端
cd apps/api
uv sync
uv run uvicorn app.main:app --reload

# 前端
cd apps/web
npm install
npm run dev
```

**设计判断**：
- 推荐使用 `uv` 管理 Python 依赖 - 追求速度
- 前后端分离启动 - 独立开发和调试
- 默认端口：后端 8000，前端 3000
