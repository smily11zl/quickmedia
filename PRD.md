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

## v5 — 自定义 AI Prompt

### Problem Statement

当前 AI 分析的 prompt 硬编码在代码中，所有用户使用同一套分析维度。摄影师想要构图/色彩分析，宠物主人想要品种识别，设计师想要版式/色彩方案——不同场景需要不同的分析指令。

### Solution

将 AI prompt 从代码中分离为配置文件，用户可自定义分析指令。系统固定追加格式尾巴确保解析不受影响。

### Key Features

- 独立配置文件 `prompts.yaml`，4 个分析类型 × 14 个预设模板（vision:4, text:3, speech:3, video:1+default）
- 双层 prompt：用户自定义优先，系统默认兜底
- JSON 统一输出格式，解析稳定
- 设置面板 AI 分析 Tab 页：模板选择 + 自定义编辑 + 保存/恢复默认
- 修改后即时生效（每次分析实时读取配置）
- Ollama `think` 参数控制思考过程开关

### Implementation Decisions

- 配置位置：`~/.asset-manager/prompts.yaml`
- 配置结构：扁平式（custom/presets 与 system_format/default 同级）
- Prompt 读取：每次分析实时读取，不缓存
- 预设模板硬编码在 `DEFAULT_PROMPTS` 中，启动时自动同步至 prompts.yaml
- 输出格式：JSON（解析器提取 markdown 代码块或 `{...}`）
- 重新分析：清除旧描述和 auto 标签后重新入队
- AI 状态：检查 ai_description/ai_summary 判断是否已完成，无数据显示"待分析"

### Testing Decisions

- PromptConfig 类加载和 fallback 逻辑
- API 读写端点
- 各分析方法从配置读取而非硬编码

### Tasks

详见 [docs/v5/tasks.md](docs/v5/tasks.md)。


---
