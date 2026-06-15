# QuickMedia PRD

> 全版本产品需求文档汇总。

---

## v1 — 已完成 ✅

### Problem Statement

用户有大量本地媒体素材（图片、视频、音频、文档），需要快速浏览、搜索和管理。

### Solution

基础素材管理工具：扫描索引、元数据提取、AI 图片分析、全文搜索。

### Key Features

- 扫描索引（SHA256 去重 + inode 追踪）
- 元数据提取（尺寸、分辨率、时长）
- AI 图片分析（场景描述 + 元素标签）
- 手动标签管理
- 全文搜索
- Web UI（暖色调设计系统）

---

## v2 — 已完成 ✅

### Problem Statement

截图中的文字无法检索，视频只有首帧分析，AI 分析阻塞扫描。

### Solution

OCR 文字提取、视频多帧采样、AI 分析异步化。

### Key Features

- OCR 图片文字提取（可搜索）
- 视频多帧采样分析（默认 1 帧）
- AI 分析异步队列（不阻塞扫描）
- 搜索结果高亮
- Finder 打开按钮

---

## v3 — 已完成 ✅

### Problem Statement

视频和音频中的语音内容无法检索，视频缺乏综合理解，分析结果无法刷新。

### Solution

whisper 语音转录、语音内容分析、视频综合总结、重新分析。

### Key Features

- whisper 语音转录（faster-whisper small）
- 语音 AI 标签 + 摘要
- 视频综合总结（语音 + 视觉融合）
- 重新分析（单个 + 批量）
- 素材删除
- 手动扫描

---

## v4 — 已完成 ✅

### Problem Statement

基础属性（时间、格式）污染标签系统，标签列表冗长，筛选能力不足，无法按日期区间、文件格式、AI 状态筛选。

### Solution

侧边栏筛选重构：类型、时间区间、文件格式、AI 状态、标签五组筛选组件，全部位于侧边栏，使用统一的下拉多选/日期控件交互。

### Key Features

- 创建时间 / 修改时间日期区间筛选
- 文件格式下拉多选（默认「点击筛选」，选中显示「已选 N 项」+ ✕）
- AI 状态下拉多选（交互同格式）
- 标签下拉多选（输入框展示已选标签名，逗号分隔，高度自适应，取并集）
- 启动时清理旧时间/格式/类型标签
- Scanner 不再生成这些标签

### User Stories

1. As a 用户，I want 按日期区间筛选素材，so that 能快速找到"上周拍的视频"。
2. As a 用户，I want 按文件格式筛选，so that 只看到"所有 PNG 图片"。
3. As a 用户，I want 按 AI 分析状态筛选，so that 能快速找到分析失败的素材并重试。
4. As a 用户，I want 多个筛选条件组合使用，so that 能精确筛选。
5. As a 用户，I want 标签列表不再被自动生成的格式化标签淹没。
6. As a 新用户，I want 筛选交互与标签筛选一致，降低学习成本。

### Implementation Decisions

详见 [docs/v4/plan.md](docs/v4/plan.md)、[docs/v4/design.md](docs/v4/design.md)、[docs/v4/tasks.md](docs/v4/tasks.md)。


---
