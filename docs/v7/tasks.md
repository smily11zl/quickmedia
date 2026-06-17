# QuickMedia v7 任务拆分

## Slice 7.1 — MiniMax 支持

**目标：** 添加 MiniMax provider，零代码改动。

- [ ] `quickmedia/models.yaml` 新增 minimax provider × 6 模型
- [ ] `frontend/src/ModelManager.tsx` BUILTIN_PROVIDERS 添加 minimax

**验证：** 重启后模型管理页面可选 MiniMax，测试连接通过。

---

## Slice 7.2 — 设置弹窗重构

**目标：** 模态弹窗替代侧边栏设置面板，三个 Tab。

**前端：**
- [ ] `frontend/src/SettingsModal.tsx` (新增) — 模态弹窗组件
  - 遮罩层 + 居中弹窗
  - 三个 Tab 切换（基础配置 / 模型管理 / AI 提示词）
  - 基础配置 Tab：帧数 + 超时 + 保存（浅色初始，修改后激活）
  - 模型管理 Tab：直接嵌入 `<ModelManager />`
  - AI 提示词 Tab：迁移现有逻辑
- [ ] `frontend/src/App.tsx` — 删除 `sh` 侧边栏代码；"⚙ 设置"改为打开模态弹窗
- [ ] `frontend/src/ModelManager.tsx` — 删除 provider 加确认弹窗；"保存配置"按钮浅色激活逻辑

**验证：** 点击设置 → 弹窗居中显示 → Tab 切换正常 → 修改后保存按钮变亮 → 关闭丢弃。

## 完成统计

| 切片 | 状态 |
|------|------|
| 7.1 MiniMax 支持 | ✅ |
| 7.2 设置弹窗重构 | ✅ |
