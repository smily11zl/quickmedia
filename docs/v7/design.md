# QuickMedia v7 技术方案

## MiniMax 支持 — 零代码改动

只需在 `quickmedia/models.yaml` 新增 provider 条目：

```yaml
minimax:
  url: https://api.minimax.io/v1
  models:
    - name: MiniMax-M3
      capabilities: [vision, text]
    - name: MiniMax-M2.7
      capabilities: [vision, text]
    - name: MiniMax-M2.5
      capabilities: [vision, text]
    - name: MiniMax-M2.1
      capabilities: [vision, text]
    - name: MiniMax-M2
      capabilities: [vision, text]
    - name: MiniMax-M1
      capabilities: [text]
```

MiniMax 的 `/v1/chat/completions` 与 OpenAI 协议完全兼容，现有 `OpenAIAdapter` 无需改动。前端 `BUILTIN_PROVIDERS` 需添加 minimax。

## 设置弹窗重构

### 组件结构

```
SettingsModal (新增)
  ├── 标题 "设置"
  ├── Tab 切换按钮组
  ├── 基础配置 Tab
  │   ├── 视频采样帧数 (复用现有逻辑)
  │   ├── 请求超时 (复用现有逻辑)
  │   └── 保存按钮 (浅色初始，有修改激活)
  ├── 模型管理 Tab
  │   └── ModelManager (完全复用)
  └── AI 提示词 Tab
      ├── 类型切换按钮组 (复用)
      ├── 预设按钮 (复用)  
      ├── textarea (复用)
      ├── 系统格式预览 (复用)
      ├── "保存自定义" 按钮 (浅色初始，有修改激活)
      └── "恢复默认" 按钮 (复用)
```

### 修改文件

| 文件 | 变更 |
|------|------|
| `quickmedia/models.yaml` | 新增 minimax 条目 |
| `frontend/src/App.tsx` | 删除侧边栏设置面板；改为 SettingsModal 弹窗触发 |
| `frontend/src/ModelManager.tsx` | 删除确认弹窗；保存按钮激活逻辑 |
| `frontend/src/SettingsModal.tsx` (新增) | 模态弹窗组件，包含基础配置 Tab |

### 弹窗行为

- 点击侧边栏"⚙ 设置" → 打开模态弹窗
- 背后半透明遮罩（`rgba(0,0,0,0.2)`）
- 点击遮罩区域或右上角 ✕ 关闭
- 关闭时未保存内容直接丢弃（不提示）
- 弹窗内容从现有侧边栏设置面板迁移

### 保存按钮激活逻辑

```
有改动 → `backgroundColor: S.r, color: S.w`
无改动 → `backgroundColor: S.d, color: S.ms`
```

通过对比初始加载值和当前值判断是否有改动。

### Provider 删除确认

删除按钮点击 → 弹出 `window.confirm()` 或自定义确认弹窗：
```js
if (!confirm(`确定删除 provider "${name}"？`)) return;
```

## tests

无需新增测试。MiniMax 是纯数据变更，设置弹窗是纯 UI 重构。前端构建成功即可验证。

## Implementation Notes

- MiniMax API 域名为 `api.minimaxi.com`（非 `minimax.io`），`/v1/models` 需认证
- 设置弹窗打开时设置 `document.body.style.overflow = "hidden"`，阻止背景滚动穿透
- ModelManager 嵌入态（`standalone=false`）去除自身滚动层，由弹窗统一滚动
- 基础配置 / Provider 列表 / 任务配置均采用 `grid-cols-2` 布局
- Provider 添加表单：下拉选 provider + API Key 输入 + 添加按钮，位于列表上方
