# QuickMedia PRD

## Problem Statement

用户在本地磁盘积累了大量的图片、视频、音频和文档素材，分散在桌面、下载、文稿等多个目录中。当前面临三个核心痛点：

1. **找不到** — 文件散落各处，依靠文件夹命名和系统搜索无法有效检索。"上个月那张有橘猫的截图在哪？"Finder 无法回答这类内容问题。

2. **无标签** — 即使找到了文件，也没有内容上下文：这张图是什么？什么风格？能用在什么场景？全靠文件名和记忆。

3. **重复冗余** — 同一张图复制了多份散在不同目录，占空间也混乱，但手动去重成本极高。

现有方案（Finder Tags、Eagle 等）要么太弱（无内容感知），要么太重（导入库模式，强迫用户改变文件组织习惯）。

## Solution

QuickMedia 是一款不碰原文件的本地素材索引工具。用户保持现有文件组织习惯，QuickMedia 在后台扫描、去重、提取元数据，并用本地 AI 模型自动生成内容描述和标签，最终通过 Web UI 提供搜索、浏览和管理能力。

核心差异：
- **索引模式** — 不复制、不移动原始文件。数据库记录引用，文件丢失只丢元数据，素材本身毫发无损。
- **本地 AI** — Qwen 3.5 多模态模型在本地运行，图片描述和标签不出本机，零隐私风险。
- **扁平标签 + 内容搜索** — 无层级标签系统，通过多选交集和全文搜索组织素材，不需要预先设计分类体系。
- **实时监听** — fsevents 感知文件增删改，拖入新文件自动入库。

## User Stories

1. As a 设计师，I want 桌面上的截图自动被扫描和索引，so that 我能快速浏览和搜索历史参考图，不用一个一个翻文件夹。

2. As a 素材管理者，I want AI 自动给图片生成描述和内容标签（人物、物体、场景），so that 我不需要手动为每张图写描述就能按内容搜索。

3. As a 注重隐私的用户，I want 所有 AI 分析都在本地完成，so that 我的素材图片不出本机，不上传任何云端服务。

4. As a 内容创作者，I want 手动给素材添加标签和描述，so that 我可以用自己的语言体系组织素材库。

5. As a 视频编辑，I want 看到所有视频的时长、分辨率和首帧画面，so that 快速筛选出可用的素材片段。

6. As a 开发者，I want 搜索项目文档的全文内容，so that 通过关键词直接定位到相关的 md 或 txt 文件。

7. As a 多类型素材用户，I want 图片、视频、音频、文档统一管理，so that 不用为每种类型使用不同的工具。

8. As a macOS 用户，I want 拖动新文件到监控目录后在 Web UI 中自动出现，so that 不需要手动执行任何命令。

9. As a 标签使用者，I want AI 自动标签用虚线边框展示（待确认状态），点击确认后变实线，so that 我能快速区分和确认 AI 建议的标签。

10. As a 素材管理者，I want 自动检测并标记重复文件，so that 我能清理冗余节省磁盘空间。

11. As a 用户，I want 在网格视图和列表视图之间切换，按名称、大小、时间排序，so that 根据不同场景选择最方便的浏览方式。

12. As a 管理员，I want 在设置页面配置 Ollama 连接和模型，so that 我能根据硬件条件选择合适的 AI 模型。

13. As a 命令行用户，I want 通过 CLI 完成扫描、搜索、打标签、查看统计，so that 不需要打开浏览器也能操作。

14. As a 新用户，I want 启动 `quickmedia serve` 后自动打开浏览器，so that 零学习成本开始使用。

## Implementation Decisions

### 架构

- 索引模式（不碰原文件），只记录文件引用路径和元数据
- Python + FastAPI 后端，React + TailwindCSS 前端（暖色调设计系统）
- SQLite 本地数据库，FTS5 虚拟表支持全文搜索
- 监控路径由用户自由配置，每个路径可独立设置递归深度

### 去重与文件追踪

- 优先用 inode + device 做同卷快速匹配
- SHA256 哈希兜底处理跨卷或复制场景
- 相同哈希的文件合并为一条素材记录，标记有 N 个副本
- 文件移动（同卷）：inode 匹配 → 静默更新路径
- 文件修改：哈希变化 → 版本归档旧记录，新哈希入库
- 文件删除：标记 deleted，保留标签和描述元数据

### AI 分析

- 图片：本地多模态模型生成场景描述 + 元素标签
- 视频：ffmpeg 提取首帧 → 走图片分析流程；附加长度分桶标签
- 文档：本地模型生成摘要 + 关键词
- AI 标签存入时 source 标记为 auto，UI 中虚线边框展示，用户确认后转 manual

### 标签系统

- 扁平标签，无层级
- 自动标签（类型、格式、时间段、长度分桶）扫描时生成
- AI 标签和手动标签通过 source 字段区分

### 缩略图

- 256px max，扫描后异步生成队列
- 状态流转：pending → processing → done / failed
- 图片直接缩放，视频 ffmpeg 提取首帧

### 实时监听

- 基于 watchdog（fsevents）监听监控目录
- 创建事件 → 新文件入库 + AI 分析 + 缩略图入队
- 删除事件 → 素材标记 deleted
- 启动时先全扫建立基准，再开启监听

## Testing Decisions

- 所有功能通过最高 seam（API endpoints）验证，测试不依赖内部实现
- 测试只验证外部行为：请求-响应格式、状态码、数据正确性
- 单元测试覆盖核心模块逻辑（Scanner/Metadata/AI/Thumbnailer/Watcher/Database）
- 现有测试文件作为新测试的 prior art
- 新功能测试加在 test_api.py 中，覆盖以下端点：
  - `POST /api/config/test-ollama` — Ollama 连接检测
  - `POST /api/assets/:id/analyze` — 手动 AI 重分析
  - `POST /api/assets/:id/tags/by-name` — 按名称添加标签
  - `PUT /api/config` — 配置更新持久化
  - `POST /api/tags` — 通过名称创建标签

## Out of Scope

- 外接硬盘 / NAS 网络路径
- 多人协作 / 云同步
- 图片编辑功能
- 素材导出 / 打包
- 移动端 App
- 视频语音转录（whisper）
- OCR 图片文字提取
- 语义相似度搜索（embedding 向量）
- 标签层级结构

## Further Notes

- 设计系统遵循 DESIGN.md 中的暖色调规范（cream canvas + coral accent + serif display）
- 所有数据存储于 `~/.asset-manager/`
- 术语表参见 CONTEXT.md
- 后续 Phase 扩展：视频多帧采样、语音转录、OCR
