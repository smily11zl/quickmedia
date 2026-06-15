# QuickMedia v3 PRD

## Problem Statement

v2 完成了视觉分析和文档分析，但素材中有大量语音信息未被利用：

1. **视频和音频中的语音内容无法检索** — 会议录像、采访录音、教程视频中的对话内容完全不可搜索。用户搜「预算审批」找不到那段关键会议录像。
2. **视频缺乏综合理解** — v2 的视频分析只有画面维度（首帧 + 多帧标签），没有语音维度。一段视频讲了什么、讨论了什么，系统完全不知道。
3. **分析结果无法刷新** — AI 模型升级或 prompt 改进后，已分析的素材没有途径重新分析。用户只能手动改数据库状态。

## Solution

v3 主攻语音识别 + 分析增强：

- **whisper 语音转录** — 使用 faster-whisper (small) 对视频和音频素材进行语音转文字。转录原文可检索，支持中英文混合识别。
- **语音内容分析** — 基于转录文本通过 Ollama 提取主题标签和内容摘要。
- **视频综合总结** — 语音摘要 + 画面对比描述融合，生成视频整体内容总结。
- **重新分析功能** — 支持单个素材和批量素材的 AI 分析重新执行。
- **素材删除** — 支持从数据库中移除素材记录，磁盘文件不受影响，下次扫描可重新入库。
- **手动扫描** — Web UI 中一键触发扫描，检查监控路径是否有新文件并自动入库分析。

## User Stories

1. As a 会议参与者，I want 搜索会议录像中的对话关键词，so that 能快速定位到关键讨论片段。

2. As a 视频编辑，I want 看到视频的整体内容总结（不只画面 + 语音分别说了什么），so that 能快速判断视频是否需要深入观看。

3. As a 播客听众，I want 音频文件自动生成转录文本和内容摘要，so that 不需听完就能了解主题。

4. As a 用户，I want 修改 prompt 或升级模型后能一键重新分析已有素材，so that 已有素材能获得更好的标签和描述。

5. As a 用户，I want 批量选中素材后一次性重新分析，so that 不需要逐个手动操作。

6. As a 素材管理者，I want 在素材详情中看到语音转录的完整文本，so that 可以直接阅读对话内容。

7. As a 用户，I want 无音轨的视频不会因语音分析报错，so that 无声录屏也能正常完成分析流程。

8. As a 用户，I want 删除不需要的素材记录，so that 素材库保持整洁，且文件本身不被删除。

9. As a 用户，I want 在 Web UI 中一键扫描新素材，so that 不需要重启服务就能发现新添加的文件。

## Implementation Decisions

### 语音转录

- 使用 faster-whisper (small) 模型，pip 安装，无需额外系统依赖
- 视频和音频素材扫描时入队 `task_type='transcribe'`
- transcriber 检测到无音轨时直接标记 done，不报错
- 转录原文存入 `assets.transcript` 字段

### 语音内容分析

- 基于转录文本，通过 Ollama 调用 TextAnalyzer 提取主题标签和内容摘要
- 语音标签以虚线边框展示（来源 source='auto'），与视觉标签一致
- 语音摘要存入 `assets.ai_summary` 字段（音频和视频共用，视频原未使用此字段）

### 视频综合总结

- 分析链路：转录 → 语音分析 → 画面分析 → 综合总结
- 综合总结等待语音摘要和视觉描述都就绪后执行
- 通过一次 Ollama 调用融合语音摘要 + 视觉描述 + 视觉标签
- 结果存入 `assets.video_summary` 字段

### 数据库变更

- `assets` 表新增 `transcript` TEXT（语音转录原文）
- `assets` 表新增 `video_summary` TEXT（视频综合总结）
- `assets` 表新增 `analyzed_at` TEXT（最近一次 AI 分析完成时间）
- `ai_queue` 新增 `task_type` 值：`'transcribe'`、`'summarize'`
- FTS 全文索引覆盖 `transcript` 和 `video_summary`

### API 变更

- `GET /api/assets/{id}` — 新增返回 `transcript`、`video_summary`、`analyzed_at`
- `POST /api/assets/{id}/reanalyze` — 触发单个素材重新分析
- `POST /api/assets/batch-reanalyze` — 批量重新分析（接收 asset_ids 数组）

### 重新分析

- 重新分析时清除素材的现有 AI 分析结果，所有任务类型重新入队
- 支持单个素材（详情面板按钮）和批量素材（网格/列表多选模式）
- 多选模式：checkbox 勾选，顶部出现操作栏「重新分析已选」

### 前端变更

- 详情面板新增「语音转录」展示区（在 OCR 文字区域下方）
- 详情面板新增「综合总结」展示区（仅视频素材）
- 「重新分析」按钮替代/扩展当前的「重试」按钮（不仅覆盖 failed 状态）
- 批量多选模式（网格/列表视图 checkbox + 操作栏）

### 素材删除

- `DELETE /api/assets/{id}` — 删除素材及所有关联数据（ai_queue, asset_tags, thumbnail_queue 等，由 CASCADE 处理）
- 详情面板标题栏 🗑 删除按钮，带确认弹窗
- 磁盘文件不受影响，下次扫描时如仍存在可重新入库

### 手动扫描

- `POST /api/scan` — 遍历所有配置的监控路径，发现新文件自动入库并入队分析
- 侧边栏底部 🔍 扫描新素材按钮，扫描完成后显示新增数量

## Testing Decisions

- 通过 API 端点验证（最高 seam），不测试内部实现细节
- 音频和视频素材使用测试 fixture 数据，mock whisper 和 Ollama 调用
- 数据库迁移测试覆盖列新增和 FTS 索引
- 重新分析端点测试验证 ai_queue 状态重置和任务重新入队
- 搜索测试验证 transcript 字段命中
- 无音轨场景：transcriber 对无音轨文件返回 done，不报错

## Out of Scope

- 实时语音识别（流式转录）
- 说话人分离（diarization）
- 多语言自动检测（用户需手动配置语言偏好）
- 语音情感分析
- 自定义 whisper 模型选择（固定 small）
- 重新分析时的历史版本保留

## Further Notes

- v3 技术方案细节见 docs/v3/design.md（待创建）
- 术语定义见 CONTEXT.md（语音转录、语音分析、视频综合总结、重新分析）
- roadmap 见 ROADMAP.md
