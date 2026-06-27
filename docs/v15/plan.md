# V15 开发计划

> 版本目标：AI 搜索 + 节点树状列表
> 状态：✅ completed

## 开发流程

1. grill-me ✅
2. grill-with-docs ✅ (CONTEXT.md updated)
3. to-prd ✅ (PRD.md updated, docs/v15/prd.md)
4. to-issues ✅ (docs/v15/tasks.md, 10 slices)
5. tdd → 待开始

## 切片总览

| # | 切片 | 类型 | 依赖 | 用户可测 |
|---|------|------|------|----------|
| s1 | search_ai prompt + task_models 基础设施 | 后端 | 无 | ❌ |
| s2 | 搜索模式 UI 改名+重排 | 前端 | 无 | ✅ |
| s3 | /api/search?mode=ai 端点实现 | 后端 | s1 | ❌ |
| s4 | AI 搜索集成 | 全栈 | s1,s2,s3 | ✅ |
| s5 | 树节点展开/折叠基础 | 前端 | 无 | ✅ |
| s6 | 树素材加载+点击详情 | 前端 | s5 | ✅ |
| s7 | 未分配虚拟节点展示 | 前端 | s6 | ✅ |
| s8 | 树拖放 | 前端 | s6,s7 | ✅ |
| s9 | 树联动刷新 | 全栈 | s6 | ✅ |
| s10 | MCP search_assets ai 模式 | 后端 | s3 | ❌ |
| s11 | 聚合 _asset_text() video_summary 修复 | 后端 | 无 | ❌ |

## 可并行执行

- 线 A: s1 → s3 → s4 → s10
- 线 B: s2 → s4
- 线 C: s5 → s6 → s7 / s8 / s9

详细任务见 [tasks.md](tasks.md)。
