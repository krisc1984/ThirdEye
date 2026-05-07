# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 技术评审系统 (ThirdEye) - 基于 `oss-skill` 方法，从本地项目中蒸馏工程判断为 playbook skill，用于技术方案评审。

**技术栈**:
- 后端：Python 3.12+, FastAPI, OpenAI Agents SDK
- 前端：Next.js 15, React 19, TypeScript
- 数据存储：PostgreSQL + pgvector (待实现)，当前使用文件系统存储

## 目录结构

```
ThirdEye/
├── apps/
│   ├── api/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── api/      # 路由层 (health, projects, playbooks, model_providers)
│   │   │   ├── core/     # 核心配置
│   │   │   ├── schemas/  # Pydantic 数据模型
│   │   │   ├── services/ # 业务服务 (扫描、蒸馏、证据构建)
│   │   │   └── main.py   # 应用入口
│   │   ├── tests/        # pytest 测试
│   │   └── pyproject.toml
│   └── web/              # Next.js 前端
│       ├── src/app/      # App Router 页面
│       └── package.json
├── data/
│   └── playbooks/        # 生成的 playbook skill 存储
├── docs/                 # 产品文档和计划
├── .spec-workflow/       # Spec 工作流模板
└── oss-skill/            # 方法论参考 (只读)
```

## 常用命令

### 后端 (apps/api)

```bash
cd apps/api

# 开发环境运行
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest

# 运行单个测试
uv run pytest tests/test_health.py

# 安装依赖
uv sync
```

### 前端 (apps/web)

```bash
cd apps/web

# 开发服务器
npm run dev

# 构建
npm run build

# Lint
npm run lint
```

## 架构要点

### 后端 API 路由

- `GET /health` - 健康检查
- `POST /api/projects` - 创建项目 (扫描本地文件夹)
- `GET /api/projects` - 项目列表
- `POST /api/playbooks` - 生成 playbook (项目蒸馏)
- `GET /api/playbooks` - Playbook 列表
- `POST /api/reviews` - 技术方案评审
- `GET/POST /api/model-providers` - 模型提供商配置

### 核心服务

1. **Project Scanner** - 扫描项目目录，识别语言/框架/文档
2. **Document Extractor** - 提取 README/docs/ADR 中的规则
3. **Code Extractor** - 分析代码结构和模块边界
4. **Evidence Builder** - 构建证据索引和证据等级
5. **Playbook Generator** - 生成 `playbook.skill.md` 和 `rules.json`

### 数据模型 (schemas/)

- `Project` - 项目元数据
- `Playbook` - 项目评审 playbook
- `Rule` - 结构化评审规则
- `Evidence` - 证据项
- `ReviewSession` - 评审会话记录
- `ModelProvider` - 模型配置

### oss-skill 集成

系统基于 `oss-skill` 方法论：
- 代码优先：先读取代码结构，再读取文档
- 多源采集：代码、文档、测试、配置、示例
- 三重验证：跨文件复现、能指导新方案、有项目特异性
- 证据分级：`confirmed` | `inferred` | `preference` | `unknown`

生成的 playbook 存储在 `data/playbooks/<project-slug>/`:
- `playbook.skill.md` - 可被 Agent 调用的 skill
- `rules.json` - 结构化规则
- `evidence.jsonl` - 证据来源
- `project-summary.md` - 项目摘要

## 开发注意事项

1. **文件存储**: MVP 阶段使用文件系统存储，后续迁移到 PostgreSQL
2. **模型适配**: 支持 OpenAI 和 OpenAI-compatible endpoint (Chat Completions 协议)
3. **忽略规则**: 默认忽略 `.git`, `node_modules`, `dist`, `build`, `.next`, `__pycache__`
4. **敏感文件**: 不读取/不存储密钥、token、私有配置
