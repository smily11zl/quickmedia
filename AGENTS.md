# AGENTS.md — QuickMedia 项目指南

> Hermes Agent 进入本目录时自动加载。面向 AI 开发者。

## 开发环境

- **Python 虚拟环境**：`.venv/bin/python`（`~/Documents/quickmedia/.venv/`）
- **测试命令**：`.venv/bin/python -m pytest tests/ -q`
- **前端构建**：`cd frontend && npm run build`
- **启动服务**：`.venv/bin/quickmedia serve 8088`

## 文档地图

| 文件 | 类型 | 说明 |
|------|------|------|
| PRD.md | 活文档 | 产品需求：问题、用户故事、范围 |
| CONTEXT.md | 活文档 | 领域术语表（Asset/Tag/Scan 等定义） |
| DESIGN.md | 活文档 | UI 设计规范（色彩/字体/圆角/组件） |
| ROADMAP.md | 活文档 | 版本路线图：已完成 / 计划中 / 远期 |
| STARTUP.md | 活文档 | 环境要求、依赖安装、启动命令 |
| README.md | 入口 | 项目概览 |
| docs/v1/design.md | 快照 | v1 技术方案（schema/API/架构） |
| docs/v1/tasks.md | 快照 | v1 开发任务拆解 |
| docs/v2/plan.md | 快照 | v2 需求决策 + 实现计划 |
| docs/v2/design.md | 快照 | v2 技术方案（schema/API/架构） |
| docs/v2/tasks.md | 快照 | v2 开发任务拆解 |
| docs/adr/ | 快照合集 | 架构决策记录 |

**活文档**=持续演进，新功能直接在原文件追加。
**快照**=按版本归档，新功能新建对应版本目录（如 docs/v2/）。

## 术语

使用 CONTEXT.md 中的标准术语。不要造新词。如果新概念没有对应术语，先在 CONTEXT.md 中定义再使用。

## 新功能开发流程

```
grill-me → grill-with-docs → to-prd → to-issues → tdd
```

1. **grill-me** — 需求面试，逐个决策
2. **grill-with-docs** — 同上 + 同步更新 CONTEXT.md（新术语）和 docs/adr/（重大决策）
3. **to-prd** — 合成 PRD 到 PRD.md（追加），确认测试 seams
4. **to-issues** — 拆成独立垂直切片 issue
5. **tdd** — 按 issue 逐个实现，RED→GREEN→REFACTOR

## 每个版本发布前必做

- 更新 `DB_VERSION` 至当前版本号（`quickmedia/database.py`）
- 如有新增术语，更新 `CONTEXT.md`
- 如有重大技术决策，在 `docs/adr/` 写 ADR

## 技术栈

Python 3.11+ / FastAPI / SQLite / React + TailwindCSS / Ollama (Qwen 3.5) / watchdog

## 测试

- 92 个测试，`python -m pytest tests/`
- 新功能优先走最高 seam（API endpoints）测试
- 测试只测外部行为，不测实现细节

## 文件组织

```
quickmedia/          ← Python 后端包
frontend/            ← React 前端（Vite + TailwindCSS）
tests/               ← pytest
```

## 运行

```bash
~/.hermes/hermes-agent/.venv/bin/python -m quickmedia serve
```
