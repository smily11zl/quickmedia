# V16 开发计划 — 聚合 Prompt 自定义

> 状态：grill-me ✅ → grill-with-docs ✅ → to-prd ✅ → to-issues ✅ → tdd ✅

## 切片总览

| # | 切片 | 类型 | 依赖 | 用户可测 |
|---|------|------|------|----------|
| s1 | DEFAULT_PROMPTS 加 4 个聚合条目 + PUT validator | 后端 | 无 | ❌ |
| s2 | DEFAULT_CONFIG 加 aggregation task_model | 后端 | 无 | ❌ |
| s3 | aggregation/prompts.py 改为 PromptConfig 读取 | 后端 | s1 | ❌ |
| s4 | aggregation/core.py 改为 task_models.aggregation | 后端 | s2 | ❌ |
| s5 | SettingsModal 三组布局 + 占位符说明 + ModelManager | 前端 | s1 | ✅ |

## 可并行执行

- 线 A: s1 → s3 → s5
- 线 B: s2 → s4

详细任务见 [tasks.md](tasks.md)。
