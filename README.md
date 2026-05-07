# ThirdEye - AI 技术评审系统

基于 `oss-skill` 方法，将本地项目的工程判断蒸馏为可复用的 playbook skill，用于技术方案评审。

## 背景

团队在设计新功能、重构模块、引入依赖、调整架构边界时，通常缺少一套可复用的工程判断协议。代码库中的 README、设计文档、目录结构、测试、配置和历史实现已经隐含了大量维护共识，但这些共识没有被结构化沉淀。

ThirdEye 从代码、文档和工程痕迹中提炼可运行的工程判断，帮助你在动手前检查技术方案是否符合项目工程标准。

## 功能特性

- **项目蒸馏**: 选择本地项目文件夹，自动分析代码库和文档，生成项目评审 playbook
- **Playbook 管理**: 查看、编辑、启用/禁用和重新生成 playbook
- **技术方案评审**: 在对话界面输入技术方案，获取基于项目工程判断的结构化评审意见
- **多模型支持**: 支持 OpenAI API 和其他 OpenAI-compatible 协议大模型

## 技术栈

- **后端**: Python 3.12+, FastAPI, OpenAI Agents SDK
- **前端**: Next.js 15, React 19, TypeScript
- **数据存储**: PostgreSQL + pgvector (规划中), 当前使用文件系统

## 快速开始

### 后端

```bash
cd apps/api

# 安装依赖
uv sync

# 开发服务器
uv run uvicorn app.main:app --reload

# 运行测试
uv run pytest
```

### 前端

```bash
cd apps/web

# 安装依赖
npm install

# 开发服务器
npm run dev

# 构建
npm run build
```

## 项目结构

```
ThirdEye/
├── apps/
│   ├── api/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── api/      # REST API 路由
│   │   │   ├── core/     # 核心配置
│   │   │   ├── schemas/  # 数据模型
│   │   │   ├── services/ # 业务服务
│   │   │   └── main.py   # 应用入口
│   │   └── tests/        # 测试
│   └── web/              # Next.js 前端
├── data/
│   └── playbooks/        # 生成的 playbook 存储
├── docs/                 # 产品文档
└── oss-skill/            # 方法论参考
```

## 核心概念

### 项目蒸馏

系统读取项目的代码、文档、测试和配置，提炼出：
- 架构边界和模块依赖
- API 设计规范
- 状态管理策略
- 依赖引入规则
- 测试策略
- 反模式清单

### Playbook Skill

每个项目生成的评审标准，包含：
- 核心维护共识
- 结构化规则
- 证据来源
- 评审流程
- 检查清单

### 技术方案评审

输入技术方案，选择对应 playbook，获取：
- 总体判断（通过/有条件通过/建议修改/不建议采用）
- 关键风险
- 与项目规则的冲突点
- 建议改法
- 必须补充的信息
- 验证要求
- 证据等级

## API 端点

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/api/projects` | 创建项目 |
| GET | `/api/projects` | 项目列表 |
| POST | `/api/playbooks` | 生成 playbook |
| GET | `/api/playbooks` | Playbook 列表 |
| POST | `/api/reviews` | 技术方案评审 |
| GET/POST | `/api/model-providers` | 模型配置 |

## 开发原则

1. **代码优先**: 先读取代码结构，再读取文档
2. **多源采集**: 代码、文档、测试、配置、示例
3. **三重验证**: 跨文件复现、能指导新方案、有项目特异性
4. **证据分级**: confirmed | inferred | preference | unknown
5. **诚实边界**: 证据不足时明确说明，不虚构结论

## 非目标 (MVP)

- 不做代码评审、diff review、PR review
- 不接入 GitHub/GitLab
- 不自动修改代码
- 不做 IDE 插件
- 不做多人审批流

## 许可证

MIT

## 致谢

本项目借鉴 [`oss-skill`](https://github.com/lianchi/oss-skill) 的方法论和实现思路。
