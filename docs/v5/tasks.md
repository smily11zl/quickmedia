# QuickMedia v5 Tasks

> to-issues 输出。基于 PRD.md。

## 依赖关系

```
Slice 5.1 (Prompt 配置)
  └─→ Slice 5.2 (AIWorker 接入)
        └─→ Slice 5.3 (设置面板 UI)
```

---

## Slice 5.1: Prompt 配置 + API

- **类型**: AFK
- **阻塞**: 无
- **覆盖**: US-1~3

### 任务清单

- [ ] 新增 `PromptConfig` 类：加载 `prompts.yaml`，提供各分析类型的 prompt
- [ ] 14 个预设模板 + 4 个默认 prompt + 4 个 system_format 硬编码在 PromptConfig 中
- [ ] prompts.yaml 不存在时自动生成（包含所有预设和默认值）
- [ ] `GET /api/prompts` — 返回所有分析类型的完整 prompt 配置
- [ ] `PUT /api/prompts` — 更新指定分析类型的 custom 字段

### 验证标准

- 首次启动自动生成 prompts.yaml
- API 返回正确的预设列表和当前 prompt
- 修改 custom 后再次读取返回新值

---

## Slice 5.2: AIWorker 接入 PromptConfig

- **类型**: AFK
- **阻塞**: Slice 5.1
- **覆盖**: US-1~3

### 任务清单

- [ ] VisionAnalyzer 从 PromptConfig 读取 prompt 替代硬编码
- [ ] TextAnalyzer.analyze 从 PromptConfig 读取
- [ ] TextAnalyzer.analyze_speech 从 PromptConfig 读取
- [ ] AIWorker._try_generate_video_summary 从 PromptConfig 读取
- [ ] 每次分析调用时实时读取（不缓存），prompt 修改后即时生效

### 验证标准

- 修改 prompts.yaml 中的 vision.custom 后，下次图片分析使用新 prompt
- 所有分析类型均从配置读取
- prompts.yaml 不存在时使用硬编码默认值

---

## Slice 5.3: 设置面板 AI 分析区域

- **类型**: AFK
- **阻塞**: Slice 5.1
- **覆盖**: US-1~4

### 任务清单

- [ ] 设置面板新增「AI 分析」独立区域（与现有 Ollama 设置区分）
- [ ] Tab 切换：图片 · 文档 · 语音 · 视频
- [ ] 每个 Tab：预设模板按钮行 + 自定义编辑 textarea + 保存按钮
- [ ] 切换预设时填入编辑区
- [ ] 保存时调用 PUT /api/prompts
- [ ] 未编辑时显示默认 prompt 作为 placeholder

### 验证标准

- 点击预设「摄影」→ 编辑区显示对应 prompt
- 修改 prompt → 保存 → 重新加载设置 → 保留修改
- 切换 Tab 不影响其他分析类型

---

## 完成统计

| 切片 | 状态 |
|------|------|
| 5.1 Prompt 配置 + API | ✅ |
| 5.2 AIWorker 接入 | ✅ |
| 5.3 设置面板 UI | ✅ |
