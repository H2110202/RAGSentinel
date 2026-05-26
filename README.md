<div align="center">

# 🛡️ RAGSentinel

**Enterprise-Grade Permission Gateway for RAG Knowledge Bases**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://www.python.org/)
[![Vue 3](https://img.shields.io/badge/Vue-3-4FC08D.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688.svg)](https://fastapi.tiangolo.com/)
[![RAGFlow](https://img.shields.io/badge/RAGFlow-v0.25-FF6B35.svg)](https://github.com/infiniflow/ragflow)

[English](#overview) · [中文文档](#中文文档) · [Architecture](#architecture) · [Quick Start](#quick-start) · [API Docs](#api-reference)

</div>

---

## Overview

**RAGSentinel** is a fine-grained permission management middleware that sits between your enterprise users and [RAGFlow](https://github.com/infiniflow/ragflow) (or any RAG engine). It provides document-level access control, organizational structure synchronization, and approval workflows — ensuring that every employee only sees what they're authorized to see, even when interacting through AI chatbots.

### Why RAGSentinel?

RAGFlow is a powerful open-source RAG engine, but it lacks enterprise-grade permission control. When deploying knowledge bases in corporate environments, you need:

- 🔐 **Fine-grained permissions** — Not just "who can access which knowledge base", but "who can see **which document** within a knowledge base"
- 🏢 **Org-structure alignment** — Permissions that mirror your company's departments, teams, and reporting lines
- 🤖 **Bot-safe access** — When employees chat with AI agents via DingTalk/Slack bots, the same permission rules apply
- ✅ **Approval workflows** — Configurable multi-level approval chains before documents go live

RAGSentinel fills this gap by acting as a **permission gateway** that wraps around RAGFlow's API, injecting access control at every layer.

## Key Features

| Feature | Description |
|---------|-------------|
| 🏢 **Org Structure Sync** | Automatically sync departments & employees from DingTalk |
| 🔐 **4-Level Permission Hierarchy** | View → Download → Upload → Manage (higher includes lower) |
| 📄 **Document-Level ACL** | Different documents in the same KB can have different visibility per user |
| 👥 **4 Permission Targets** | Company-wide, Department, Individual, Project Group |
| 🤖 **Agent Permission Guard** | DingTalk bot chats respect the same permission rules |
| ✅ **Approval Workflows** | Multi-step configurable approval chains |
| ⚡ **Permission Caching** | In-memory cache with TTL for high-performance access checks |
| 🔄 **RAGFlow Auto-Sync** | Creating a KB → auto-creates a RAGFlow Dataset; uploading a doc → auto-uploads to RAGFlow |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Enterprise Users                        │
│         (DingTalk Bot / Web Portal / API Clients)            │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐    ┌──────────────────────────────────┐
│   RAGSentinel Web    │    │   RAGSentinel Agent Gateway       │
│   (Vue 3 + Element)  │    │   (DingTalk Bot Permission Check) │
└──────────┬───────────┘    └──────────────┬───────────────────┘
           │                               │
           ▼                               ▼
┌──────────────────────────────────────────────────────────────┐
│                    RAGSentinel Backend                        │
│              (FastAPI + SQLAlchemy + SQLite)                  │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ Permission   │  │ Org Sync     │  │ Approval Workflow   │ │
│  │ Engine       │  │ (DingTalk)   │  │ Engine              │ │
│  │ (4-level     │  │              │  │ (Multi-step chain)  │ │
│  │  hierarchy)  │  │              │  │                     │ │
│  └──────┬───────┘  └──────────────┘  └─────────────────────┘ │
│         │                                                    │
│         │  Permission-filtered API calls                     │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              RAGFlow Proxy Layer                      │   │
│  │  (Dataset CRUD / Document Upload / Chat Completion)  │   │
│  └──────────────────────┬───────────────────────────────┘   │
└─────────────────────────┼────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │     RAGFlow Engine    │
              │  (v0.25+ / Docker)    │
              │                       │
              │  ┌─────┐ ┌────────┐  │
              │  │ LLM │ │Embedding│  │
              │  └─────┘ └────────┘  │
              │  ┌─────────────────┐  │
              │  │ Vector Store    │  │
              │  │ (ES/Infinity)   │  │
              │  └─────────────────┘  │
              └───────────────────────┘
```

## Permission Model

RAGSentinel implements a **hierarchical permission system** with 4 levels and 4 target types:

### Permission Levels (Higher includes Lower)

```
Manage ──includes──▶ Upload ──includes──▶ Download ──includes──▶ View
```

### Permission Targets

| Target | Scope | Example |
|--------|-------|---------|
| 🏢 Company | All employees | "Everyone can view the employee handbook" |
| 🏗️ Department | Members of specific departments | "Only Engineering can see technical specs" |
| 👤 Individual | Specific person | "Only Zhang San can access salary data" |
| 👥 Project Group | Members of a project group | "Project Alpha team can see design docs" |

### Document-Level Override

When a document has its own permission rules, they **override** the knowledge base defaults. If no document-level rule exists, the KB-level permission is inherited.

```
KB Permission:  Engineering Dept → View
  └── Doc A:  (inherits) → Engineering can View ✓
  └── Doc B:  Zhang San → View  → Only Zhang San can View, Engineering CANNOT ✗
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend dev server)
- A running RAGFlow instance (v0.25+)
- (Optional) DingTalk App credentials for org sync

### 1. Clone & Setup

```bash
git clone https://github.com/RAGSentinel/RAGSentinel.git
cd RAGSentinel
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your RAGFlow URL, API Key, and DingTalk credentials
```

### 3. Start Backend

```bash
cd backend
pip install -r requirements.txt
python init_db.py    # Initialize database with default admin user
python run.py
# Backend runs at http://localhost:8088
# API docs at http://localhost:8088/docs
```

### 4. Start Frontend

```bash
cd frontend
node server.js
# Frontend runs at http://localhost:3000
```

### 5. Docker Compose (Production)

```bash
cp .env.example .env
# Edit .env with your configuration (RAGFLOW_API_KEY and SECRET_KEY are required)
docker compose up -d
```

### 6. First Login

Default admin account:
- Username: `admin`
- Password: Set via `ADMIN_DEFAULT_PASSWORD` env var (default: `changeme`)

> ⚠️ Change the default password immediately after first login!

## API Reference

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login (OAuth2 form) |
| GET | `/api/auth/me` | Get current user |

### Knowledge Bases

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge/bases` | List accessible KBs |
| POST | `/api/knowledge/bases` | Create KB (+ auto-sync to RAGFlow) |
| PUT | `/api/knowledge/bases/{id}` | Update KB |
| DELETE | `/api/knowledge/bases/{id}` | Delete KB |
| POST | `/api/knowledge/bases/{id}/upload` | Upload document (+ auto-sync to RAGFlow) |
| GET | `/api/knowledge/bases/{id}/permissions` | List KB permissions |
| POST | `/api/knowledge/bases/{id}/permissions` | Set KB permission |

### Document-Level Permissions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/knowledge/bases/{kb_id}/documents/{doc_id}/permissions` | List doc permissions |
| POST | `/api/knowledge/bases/{kb_id}/documents/{doc_id}/permissions` | Set doc permission |
| DELETE | `/api/knowledge/bases/{kb_id}/documents/{doc_id}/permissions/{perm_id}` | Remove doc permission |

### Agent (Bot) Gateway

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/knowledge/agent/check-access` | Check user's accessible KBs |
| POST | `/api/knowledge/agent/query` | Query KB with permission check |
| POST | `/api/knowledge/agent/filter-docs` | Filter accessible documents |
| POST | `/api/ragflow/agent-chat` | Chat via RAGFlow with auto permission filtering |

### RAGFlow Proxy

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/ragflow/status` | Test RAGFlow connection |
| GET | `/api/ragflow/datasets` | List RAGFlow datasets |
| POST | `/api/ragflow/datasets` | Create RAGFlow dataset |
| GET | `/api/ragflow/chats` | List chat assistants |
| POST | `/api/ragflow/chats` | Create chat assistant |
| POST | `/api/ragflow/chat` | Chat completion |

### DingTalk Sync

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dingtalk/sync` | Sync org structure from DingTalk |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3 + Element Plus (CDN, single HTML) |
| Backend | FastAPI + SQLAlchemy + SQLite |
| RAG Engine | RAGFlow v0.25+ (Docker) |
| LLM | Any OpenAI-compatible model |
| Embedding | BAAI/bge-large-zh-v1.5 |
| Auth | JWT (HS256) |
| Org Sync | DingTalk Open Platform API |

## 中文文档

### 项目简介

**RAGSentinel** 是一个面向企业级RAG知识库的细粒度权限管理网关。它作为中间件部署在用户和RAGFlow之间，提供文档级访问控制、组织架构同步和审批工作流，确保每位员工只能看到被授权的内容——即使通过AI智能体对话也不例外。

### 核心能力

- **4级权限层级**：查看 → 下载 → 上传 → 管理（高权限自动包含低权限）
- **4种授权对象**：全公司 / 部门 / 个人 / 项目组
- **文档级权限覆盖**：同一知识库中，不同文档对同一员工可见性不同
- **智能体权限守卫**：钉钉机器人对话时，自动按权限过滤可访问的知识库和文档
- **组织架构同步**：一键从钉钉同步部门和人员
- **审批工作流**：可配置多级审批链
- **RAGFlow自动同步**：创建知识库自动创建Dataset，上传文档自动上传到RAGFlow

### 快速开始

```bash
# 1. 克隆项目
git clone https://github.com/RAGSentinel/RAGSentinel.git
cd RAGSentinel

# 2. 配置环境变量
cp .env.example .env

# 3. 启动后端
cd backend && pip install -r requirements.txt && python init_db.py && python run.py

# 4. 启动前端
cd frontend && node server.js

# 5. 访问 http://localhost:3000
# 默认账号: admin / changeme (通过 ADMIN_DEFAULT_PASSWORD 环境变量设置)
# API文档: http://localhost:8088/docs
```

## Roadmap

- [ ] Support for more RAG engines (LangChain, LlamaIndex)
- [ ] RBAC role templates
- [ ] Audit logging & analytics dashboard
- [ ] Real-time permission sync via WebSocket
- [ ] Multi-language frontend (i18n)
- [ ] OIDC/SAML SSO integration
- [ ] Kubernetes Helm chart
- [ ] Plugin system for custom permission evaluators

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the Apache License 2.0 — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [RAGFlow](https://github.com/infiniflow/ragflow) — The RAG engine that RAGSentinel wraps around
- [FastAPI](https://fastapi.tiangolo.com/) — The blazing-fast Python web framework
- [Element Plus](https://element-plus.org/) — Vue 3 component library
- [DingTalk Open Platform](https://open.dingtalk.com/) — Organization structure data source

---

<div align="center">

**If RAGSentinel helps your enterprise, please consider giving us a ⭐!**

</div>
