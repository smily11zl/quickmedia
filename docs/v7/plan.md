# QuickMedia v7 — MiniMax 支持 + 设置弹窗重构

> 需求访谈记录。grill-me 时间：2026-06-17。

## 设计决策

### 1. MiniMax 支持

- MiniMax 提供 OpenAI 兼容接口：`https://api.minimax.io/v1/chat/completions`
- 适配器无需改动，只需在 models.yaml 加 provider 条目
- 模型：MiniMax-M3 / M2.7 / M2.5 / M2.1 / M2（均支持 vision+text），M1（text）
- Key 机制：积分制和订阅制都走 Bearer token 认证，不区分

### 2. 设置弹窗重构

- **模态弹窗** — 居中覆盖，背后半透明遮罩，点空白处关闭
- 关闭时未保存内容直接丢弃（和现有行为一致）
- **三个 Tab：** 基础配置 / 模型管理 / AI 分析提示词
- 每个 Tab 的内容完全复用现有逻辑

### 3. 保存按钮激活逻辑

三个 Tab 的保存按钮初始为浅色（不可用），有修改后才变亮：

| Tab | 保存按钮 | 激活条件 |
|-----|---------|---------|
| 基础配置 | "保存" | 视频帧数 / 超时任一被修改 |
| 模型管理 | "保存配置" | provider 选择 / model 选择有改动 |
| AI 提示词 | "保存自定义" | textarea 内容 != 已保存的 custom |

### 4. Provider 删除确认

- Provider 添加即为即时保存，无确认
- 删除 provider 时弹出确认框（取消 / 确认），确认后即时保存
- 确认框样式沿用系统设定

## 涉及文件

| 文件 | 变更 |
|------|------|
| `quickmedia/models.yaml` | 新增 minimax provider × 6 模型 |
| `frontend/src/App.tsx` | 设置面板改为模态弹窗 + 三个 Tab |
| `frontend/src/ModelManager.tsx` | 删除 provider 确认弹窗；保存按钮激活逻辑 |
