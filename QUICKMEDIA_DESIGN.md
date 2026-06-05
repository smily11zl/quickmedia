# QuickMedia 技术方案文档

## 1. 产品定位

QuickMedia 是一款本地素材管理工具，以 **索引模式** 工作——只记录文件的元数据、标签和描述，不复制、不移动原始文件。用户在磁盘上自由组织文件，QuickMedia 提供增强的搜索、标签和预览能力。

## 2. 核心原则

| 原则 | 说明 |
|------|------|
| 不碰原文件 | 只索引，不复制、不移动、不修改原始素材 |
| 扁平标签 | 标签无层级，通过搜索和多选交集组织 |
| AI 辅助 | 本地模型自动生成描述和标签，用户确认 |
| 本地优先 | 数据、缩略图、AI 分析全部本地处理 |
| 渐进扩展 | 每种素材类型逐步加深分析深度 |

## 3. 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 后端 | Python 3.11+ | FastAPI 做 Web API |
| 数据库 | SQLite + FTS5 | 全文搜索，零配置 |
| 前端 | React + TailwindCSS | 轻量 Web UI |
| 文件监听 | watchdog (fsevents) | macOS 原生文件事件 |
| 图片处理 | Pillow | 缩略图、EXIF、元数据 |
| 视频处理 | ffmpeg / ffprobe | 首帧提取、元数据 |
| 音频处理 | (MVP 暂缓) | 后续 whisper 转录 |
| AI 多模态 | Ollama + Qwen 3.5 | 本地图片描述、文档摘要、标签生成 |
| 哈希 | hashlib (SHA256) | 内容去重 |
| 打包 | (MVP 不打包) | 后续 PyInstaller |

## 4. Ollama 本地模型配置指南

QuickMedia 依赖 Ollama 提供本地 AI 能力。本章说明需要安装哪些模型、如何安装、以及
每种模型在素材分析中的角色。

### 4.1 安装 Ollama

```bash
# macOS（推荐）
brew install ollama

# 或从官网下载 .app
# https://ollama.com/download

# 启动 Ollama 后台服务
ollama serve
```

Ollama 默认监听 `http://localhost:11434`。

验证安装：
```bash
ollama --version
curl http://localhost:11434/api/tags   # 查看已安装模型
```

### 4.2 模型推荐

Qwen 3.5 是阿里推出的**统一多模态模型**，原生支持文字和图片输入，
一个模型就能同时处理素材图片识别和文档内容总结，不需要分开部署视觉模型和文本模型。

#### 推荐方案：Qwen 3.5 单模型

| 尺寸 | 安装命令 | 大小 | 适用场景 |
|------|---------|------|---------|
| 4B（轻量） | `ollama pull qwen3.5:4b` | ~2.5GB | 8GB RAM 机器，基础图片描述+文本摘要 |
| 9B（均衡） | `ollama pull qwen3.5:9b` | ~5.5GB | 16GB+ RAM，质量和速度兼顾（推荐） |
| 27B（高质量） | `ollama pull qwen3.5:27b` | ~16GB | 32GB+ RAM，最佳质量 |
| 最新版 | `ollama pull qwen3.5` | ~6.6GB | 跟随 Ollama 默认 tag，256K 上下文 |

Qwen 3.5 的特性：
- **统一多模态**：文字和图片同模型处理，不是视觉模块外挂
- **256K 上下文**：长文档也能一次分析
- **中文优秀**：阿里训练，中文能力是原生级别
- **Apache 2.0 开源**：无使用限制

#### 备选方案：视觉+文本双模型

如果 Qwen 3.5 在你的机器上效果不理想，可以回退到分离方案：

| 用途 | 模型 | 安装命令 | 大小 |
|------|------|---------|------|
| 图片分析 | minicpm-v | `ollama pull minicpm-v` | ~5GB |
| 文本分析 | qwen2.5:7b | `ollama pull qwen2.5:7b` | ~4.5GB |

双模型总大小约 10GB，不如一个 qwen3.5:9b（~5.5GB）省空间。

#### 语音转录

| 工具 | 安装 | 大小 | 说明 |
|------|------|------|------|
| whisper.cpp | `brew install whisper-cpp` | ~1.5GB | 推荐，Phase 2 扩展 |

### 4.3 推荐配置（按硬件）

#### 配置 A：标准（Apple Silicon M1+ / 16GB+ RAM）✓ 推荐

```bash
ollama pull qwen3.5:9b
```

总下载：约 5.5GB。一个模型处理图片描述 + 元素标签 + 文档摘要 + 关键词提取。

#### 配置 B：轻量（8GB RAM）

```bash
ollama pull qwen3.5:4b
```

总下载：约 2.5GB。基础多模态能力，适合内存有限的机器。

#### 配置 C：高质量（32GB+ RAM）

```bash
ollama pull qwen3.5:27b
```

总下载：约 16GB。图片描述和文本分析质量最高，适合素材量大的重度用户。

### 4.4 模型在 QuickMedia 中的具体用途

Qwen 3.5 是多模态模型，根据输入内容自动切换行为：

#### 图片分析（输入图片）

示例 prompt：
```
请描述这张图片的场景、整体风格和色调（50字以内）。
然后列出图片中出现的具体元素（人物、动物、物体、建筑、文字等），
以逗号分隔的标签形式输出，标签使用中文。

输出格式：
描述：<描述文本>
标签：<标签1>, <标签2>, <标签3>, ...
```

期望输出：
```
描述：室内场景，暖色调。一只橘猫趴在窗台上，阳光透过窗帘洒在地板上。
标签：猫, 橘猫, 宠物, 窗台, 阳光, 室内, 温馨, 摄影
```

#### 文本分析（输入文字）

示例 prompt：
```
总结以下文档内容（200字以内），提取 5-10 个主题关键词作为标签。
关键词以逗号分隔，使用中文。

文档内容：
<文档内容>
```

#### 素材类型与模型调用

| 素材类型 | 输入方式 | 说明 |
|---------|---------|------|
| 图片 (.png/.jpg/.webp) | 图片 | 直接分析图像内容 |
| 视频 (.mp4/.mov) | 首帧图片 | 提取首帧作为图片分析 |
| 文档 (.md/.txt) | 文字 | 直接分析文字内容 |
| PDF | 文字/图片 | 先提取文字；扫描版用图片分析 |

### 4.5 语音转录（Phase 2 扩展）

#### 方案一：Ollama Whisper 社区模型

```bash
ollama pull karanchopda333/whisper
```

#### 方案二：whisper.cpp（推荐）

```bash
# 安装 whisper.cpp
brew install whisper-cpp

# 下载模型（small 够用，约 466MB）
# 或 medium（约 1.5GB，质量更好）
bash scripts/download-ggml-model.sh small
```

QuickMedia 通过 subprocess 调用 whisper.cpp 完成语音转录，返回的文字再通过
Qwen 3.5 进行摘要和标签提取。

### 4.6 验证安装

```bash
# 1. 确认模型已安装
ollama list

# 2. 测试图片识别
ollama run qwen3.5:9b "描述这张图片：/path/to/test.jpg"

# 3. 测试文本总结
ollama run qwen3.5:9b "请用一句话总结这段内容：QuickMedia 是一款本地素材管理工具，
支持图片、视频、音频和文档的自动扫描、标签化和搜索。"

# 4. 如果用了 whisper.cpp
whisper-cpp -m models/ggml-small.bin -f test.wav
```

### 4.7 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| `connection refused` | Ollama 未启动 | `ollama serve` |
| 模型未找到 | 未 pull | `ollama pull qwen3.5:9b` |
| 推理很慢 | 模型太大/内存不足 | 换 qwen3.5:4b |
| 中文输出不准 | 模型尺寸太小 | 换更大的 qwen3.5:9b 或 27b |
| 图片分析超时 | 图片分辨率太高 | QuickMedia 自动缩放后再发送给模型 |
| 显存/内存不足 | 大模型吃太多资源 | 换轻量尺寸或关闭其他程序 |

### 4.8 配置文件对应设置

QuickMedia 的 `~/.asset-manager/config.yaml` 中 AI 配置对应的 key：

```yaml
ai:
  ollama_url: http://localhost:11434   # Ollama 服务地址
  model: qwen3.5:9b                    # 多模态模型（同时处理图片和文本）
  timeout: 60                           # 模型调用超时（秒）
```

## 5. 数据模型

### 5.1 SQLite 表结构

```sql
-- 素材主表
CREATE TABLE assets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hash            TEXT NOT NULL,           -- SHA256，内容唯一标识
    inode           INTEGER,                 -- 文件系统 inode，同卷快速匹配
    device          INTEGER,                 -- 设备号（stat 获取）
    path            TEXT NOT NULL,           -- 绝对路径
    filename        TEXT NOT NULL,           -- 文件名（含扩展名）
    extension       TEXT NOT NULL,           -- 扩展名（小写，含点）
    mime_type       TEXT,                    -- MIME 类型
    asset_type      TEXT NOT NULL,           -- image / video / audio / document / other
    size            INTEGER NOT NULL,        -- 文件大小（bytes）
    width           INTEGER,                 -- 图片/视频宽度
    height          INTEGER,                 -- 图片/视频高度
    duration        REAL,                    -- 音视频时长（秒）
    exif_data       TEXT,                    -- EXIF 原始数据（JSON）
    description     TEXT,                    -- 用户手动描述
    ai_description  TEXT,                    -- AI 生成的描述
    ai_summary      TEXT,                    -- AI 生成的摘要（文本/语音）
    notes           TEXT,                    -- 用户备注
    status          TEXT DEFAULT 'active',   -- active / deleted
    thumbnail_status TEXT DEFAULT 'pending', -- pending / processing / done / failed / skipped
    version_of      INTEGER,                 -- 指向被替换的旧版本 asset.id
    created_at      TEXT,                    -- 文件系统创建时间
    modified_at     TEXT,                    -- 文件系统修改时间
    scanned_at      TEXT,                    -- 最后扫描时间
    created         TEXT DEFAULT (datetime('now')),  -- 记录创建时间
    updated         TEXT DEFAULT (datetime('now'))   -- 记录更新时间
);

CREATE INDEX idx_assets_hash ON assets(hash);
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_asset_type ON assets(asset_type);
CREATE INDEX idx_assets_inode_device ON assets(inode, device);
CREATE UNIQUE INDEX idx_assets_inode_device_active 
    ON assets(inode, device) WHERE status = 'active';

-- FTS5 全文搜索虚拟表
CREATE VIRTUAL TABLE assets_fts USING fts5(
    filename,
    description,
    ai_description,
    ai_summary,
    notes,
    content='assets',
    content_rowid='id'
);

-- 标签表
CREATE TABLE tags (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL UNIQUE
);

-- 素材-标签关联（多对多）
CREATE TABLE asset_tags (
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    source   TEXT DEFAULT 'manual',  -- manual / auto (AI 生成，待确认)
    PRIMARY KEY (asset_id, tag_id)
);

-- 缩略图任务队列
CREATE TABLE thumbnail_queue (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id  INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    status    TEXT DEFAULT 'pending',  -- pending / processing / done / failed / skipped
    attempt   INTEGER DEFAULT 0,
    error     TEXT,
    created   TEXT DEFAULT (datetime('now'))
);

-- 监控路径配置
CREATE TABLE watch_paths (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    path          TEXT NOT NULL UNIQUE,
    recursive     INTEGER DEFAULT 1,           -- 是否递归子目录
    max_depth     INTEGER DEFAULT 3,           -- 最大递归深度
    enabled       INTEGER DEFAULT 1
);

-- 配置表（key-value 存储）
CREATE TABLE config (
    key   TEXT PRIMARY KEY,
    value TEXT
);
```

### 5.2 自动标签规则

素材首次扫描时自动生成以下标签：

| 标签 | 触发条件 | 示例 |
|------|---------|------|
| 素材类型 | 所有素材 | `图片`、`视频`、`音频`、`文档`、`其他` |
| 格式 | 按扩展名 | `PNG`、`MP4`、`PDF` |
| 时间段 | modified_at 分组 | `2026-06`、`2026` |
| 视频长度 | 视频 duration | `短片(<5min)`、`中片(5-30min)`、`长片(>30min)` |
| 监控来源 | 来自哪个监控路径 | `桌面`、`下载` |

## 6. 扫描与去重流程

### 6.1 启动全扫

```
quickmedia serve (首次或启动)
    │
    ▼
1. 读取 watch_paths 表，获取所有 enabled=1 的监控路径
    │
    ▼
2. 遍历每个路径（受 max_depth 约束）
    │
    ▼
3. 对每个文件：
   ├─ 扩展名白名单过滤 → 不在白名单则跳过
   ├─ 文件大小 > 500MB → 标记 heavy，仅做基础入库
   ├─ stat() 获取 inode + device
   │  ├─ (inode, device) 匹配 active 记录 → 路径未变，更新 modified_at → 继续
   │  └─ 无匹配 → 进入哈希判断
   ├─ SHA256 计算
   │  ├─ hash 匹配已有记录 → 重复文件（不同路径）
   │  │  ├─ 原记录路径存在 → 新路径视为副本
   │  │  └─ 原记录路径不存在 → 更新原记录路径为新路径（文件被移动）
   │  └─ hash 不匹配 → 新素材，入库
   ├─ 提取元数据（尺寸、时长、EXIF）
   └─ 放入缩略图队列
    │
    ▼
4. 清理：assets 表中路径在监控范围内但磁盘文件不存在的 → status='deleted'
    │
    ▼
5. 启动 fsevents 监听
```

### 6.2 fsevents 实时监听

| 事件 | 处理 |
|------|------|
| Created | 新文件 → 走新素材入库流程 |
| Modified | 路径未变 → 重新算 hash，hash 变了 → 旧记录标记为 replaced，新 hash 入库 |
| Moved (within scope) | inode 匹配 → 更新 path |
| Moved (out of scope) | 标记为 deleted |
| Deleted | 标记为 deleted |

## 7. AI 分析流水线

### 7.1 图片分析（首批实现）

```
新图片入库
    │
    ▼
1. PIL 读取 → 缩放到合适尺寸
    │
    ▼
2. 发送给 Ollama (Qwen 3.5)
   提示词："描述这张图片的场景、风格和色调。
            列出图片中出现的元素（人物、动物、物体、建筑、文字等），
            以逗号分隔的标签形式输出。"
    │
    ▼
3. 解析返回：
   ├─ ai_description → "这是一张室内场景的截图，展示了一个聊天界面..."
   └─ auto_tags → ["截图", "UI", "聊天界面", "深色模式", "中文"]
    │
    ▼
4. 入库：ai_description 写入 assets 表
          auto_tags 写入 asset_tags (source='auto')
    │
    ▼
5. UI 显示：auto 标签用虚线边框，用户点击确认 → source 变为 'manual'
             用户可移除不需要的标签
```

### 7.2 视频分析（首批实现——首帧）

```
新视频入库
    │
    ▼
1. ffprobe 提取元数据：时长、分辨率、编码、帧率
    │
    ▼
2. ffmpeg 提取首帧 → 保存为临时图片
    │
    ▼
3. 首帧发送给 Ollama，走图片分析流程
    │
    ▼
4. 自动标签额外添加视频长度分桶标签
```

### 7.3 文本分析（首批实现）

```
文本文档入库（.md / .txt / .pdf）
    │
    ▼
1. 读取文本内容（PDF 用 pymupdf 提取）
    │
    ▼
2. 发送给 Ollama (Qwen 3.5)
   提示词："总结以下内容（200字内），并提取5-10个关键词作为标签。
            标签以逗号分隔。"
    │
    ▼
3. 解析返回：
   ├─ ai_summary → 内容摘要
   └─ auto_tags → ["技术文档", "API设计", "Python", ...]
```

### 7.4 渐进扩展路线

```
阶段1 (MVP):  图片整体+元素  →  视频首帧  →  文本摘要+关键词
阶段2:        图片OCR文字提取  →  视频多帧采样
阶段3:        视频语音转录(whisper)  →  视频整体总结  →  音频转录+摘要
```

## 8. Web UI 设计

### 8.1 页面结构

```
┌─ 侧边栏（240px）────────────────┬─ 主内容区 ──────────────────────┬─ 详情面板（360px）─────┐
│                                 │                                  │                        │
│  [搜索框]                       │ ┌──────┐ ┌──────┐ ┌──────┐     │ 缩略图（大）            │
│                                 │ │      │ │      │ │      │     │                        │
│  全部素材   (2,340)             │ │ 🖼️  │ │ 🎬   │ │ 🖼️  │     │ cat.png                │
│  图片       (1,200)             │ │      │ │      │ │      │     │ ~/Desktop/img/cat.png  │
│  视频       (560)               │ └──────┘ └──────┘ └──────┘     │                        │
│  音频       (300)               │ ┌──────┐ ┌──────┐ ┌──────┐     │ ─────────────────────  │
│  文档       (280)               │ │      │ │      │ │      │     │ 类型: 图片 | 264KB     │
│  其他       (0)                 │ │      │ │      │ │      │     │ 尺寸: 1920×1080       │
│                                 │ │      │ │      │ │      │     │ 格式: PNG              │
│  ─────────────                  │ └──────┘ └──────┘ └──────┘     │ 创建: 2026-05-20       │
│  标签                           │                                  │ 修改: 2026-05-25       │
│  □ 截图      (489)              │  筛选栏:                         │ ─────────────────────  │
│  □ 设计      (145)              │  [类型▼] [标签▼] [时间▼]        │                        │
│  □ UI        (32)               │  [排序: 最新▼]  [视图: 网格]    │ 描述（可编辑）:         │
│  □ 图表      (89)               │                                  │ ┌────────────────────┐ │
│  □ 宠物      (67)               │                                  │ │ 一张橘猫趴在窗台上   │ │
│                                 │                                  │ │ 阳光透过窗帘洒在...  │ │
│  ─────────────                  │                                  │ └────────────────────┘ │
│  监控路径                       │                                  │                        │
│  📁 ~/Desktop                   │                                  │ AI 标签:               │
│  📁 ~/Documents                 │                                  │ ┌─🐱 猫 ─┐ (虚线边框)  │
│  📁 ~/Downloads                 │                                  │ │ 🖼️ 截图│              │
│  [+ 添加路径]                   │                                  │ │ 🌅 阳光│              │
│                                 │                                  │ └────────┘              │
│  ─────────────                  │                                  │                        │
│  [⚙ 设置]                       │                                  │ 手动标签:               │
│                                 │                                  │ [宠物] [桌面素材] [+添加]│
│                                 │                                  │                        │
│                                 │                                  │ 备注:                   │
│                                 │                                  │ [___可用于博客配图___]  │
└─────────────────────────────────┴──────────────────────────────────┴────────────────────────┘
```

### 8.2 交互说明

| 区域 | 交互 |
|------|------|
| 搜索框 | FTS5 全文搜索（描述、标签、文件名），实时过滤 |
| 左侧分类 | 点击切换类型，数字为素材数量 |
| 标签筛选 | 多选取交集，点标签名筛选，再次点击取消 |
| 缩略图网格 | 鼠标悬停显示文件名和标签摘要 |
| 缩略图状态 | pending→灰色占位 / processing→旋转动画 / done→缩略图 / failed→错误图标 |
| AI 标签 | 虚线边框展示，点击转为实线（确认），右键删除 |
| 详情面板 | 点击素材展开，描述可直接编辑，点击外部自动保存 |
| 路径 | 点击在 Finder 中打开 |

### 8.3 设置页

```
┌─ 设置 ──────────────────────────────┐
│                                      │
│  AI 配置                             │
│  Ollama URL:  [http://localhost:11434] │
│  视觉模型:    [minicpm-v ▼]          │
│  文本模型:    [qwen2.5 ▼]            │
│  [检测 Ollama 连接]                  │
│                                      │
│  ───────────────────────────────     │
│  监控路径                            │
│  ┌─────────────────────────────┐    │
│  │ ~/Desktop     递归:3 ✓     │    │
│  │ ~/Documents   递归:2 ✓     │    │
│  │ ~/Downloads   递归:2 ✗     │    │
│  │ [+ 添加]                   │    │
│  └─────────────────────────────┘    │
│                                      │
│  ───────────────────────────────     │
│  文件格式白名单                      │
│  图片: jpg jpeg png gif webp heic svg │
│  视频: mp4 mov avi                   │
│  音频: mp3 wav m4a                   │
│  文档: pdf txt md                    │
│                                      │
│  ───────────────────────────────     │
│  超大文件阈值: [500] MB               │
│                                      │
└──────────────────────────────────────┘
```

## 9. CLI 命令集

```
quickmedia scan [path]
    扫描指定路径（无参数则扫描全部已配置的监控路径）

quickmedia list [--type image|video|audio|document|other] [--tag 标签名]
    列出素材，支持类型和标签筛选

quickmedia search "关键词"
    全文搜索素材的描述、标签和文件名

quickmedia tag <asset-id> "标签名"
    给素材手动添加标签

quickmedia edit <asset-id>
    编辑素材的描述和备注（打开 $EDITOR 或交互式编辑）

quickmedia serve [--port 8080]
    启动 Web UI（默认端口随机）

quickmedia paths
    查看和管理监控路径

quickmedia stats
    查看素材库统计（总数、分类数量、存储占用等）

quickmedia config [key] [value]
    查看或修改配置（等同于编辑 config.yaml）
```

## 10. 配置文件

文件位置：`~/.asset-manager/config.yaml`

```yaml
# QuickMedia 配置文件

# AI 配置
ai:
  ollama_url: http://localhost:11434
  model: qwen3.5:9b           # 多模态模型（同时处理图片识别和文本总结）

# 监控路径
watch_paths:
  - path: ~/Desktop
    recursive: true
    max_depth: 3
    enabled: true
  - path: ~/Documents
    recursive: true
    max_depth: 2
    enabled: true
  - path: ~/Downloads
    recursive: true
    max_depth: 2
    enabled: false

# 文件格式白名单
formats:
  image: [jpg, jpeg, png, gif, webp, heic, svg]
  video: [mp4, mov, avi]
  audio: [mp3, wav, m4a]
  document: [pdf, txt, md]

# 系统配置
system:
  max_file_size: 524288000    # 超大文件阈值 (bytes) — 500MB
  thumbnail_size: 256          # 缩略图最大边长 (px)
  db_path: ~/.asset-manager/data.db
  thumbnails_path: ~/.asset-manager/thumbnails

# Web UI 配置
web:
  default_port: 8088
  auto_open_browser: true
```

## 11. API 设计（FastAPI 路由）

```
GET    /api/assets              # 素材列表（分页、筛选）
GET    /api/assets/:id          # 素材详情
PUT    /api/assets/:id          # 更新描述、备注
DELETE /api/assets/:id          # 删除素材（只删记录，不删文件）

GET    /api/assets/:id/versions # 查看版本历史

POST   /api/scan                # 触发扫描
GET    /api/scan/status         # 扫描状态

GET    /api/tags                # 标签列表（含素材计数）
POST   /api/tags                # 创建标签
DELETE /api/tags/:id            # 删除标签
POST   /api/assets/:id/tags     # 给素材添加标签
DELETE /api/assets/:id/tags/:tag_id  # 移除标签

GET    /api/thumbnails/:id      # 获取缩略图（二进制流）

GET    /api/search?q=xxx        # FTS5 搜索

GET    /api/stats               # 统计概览

GET    /api/config              # 获取配置
PUT    /api/config              # 更新配置

GET    /api/paths               # 监控路径列表
POST   /api/paths               # 添加路径
DELETE /api/paths/:id           # 删除路径
PUT    /api/paths/:id           # 更新路径配置
```

## 12. 项目结构

```
quickmedia/
├── quickmedia/
│   ├── __init__.py
│   ├── __main__.py          # python -m quickmedia 入口
│   ├── cli.py               # CLI 命令
│   ├── config.py            # 配置管理
│   ├── database.py          # SQLite 连接 + schema 迁移
│   ├── models.py            # 数据模型（dataclass）
│   ├── scanner.py           # 扫描引擎
│   ├── watcher.py           # fsevents 监听
│   ├── hasher.py            # SHA256 哈希
│   ├── metadata.py          # 元数据提取（EXIF, ffprobe）
│   ├── thumbnailer.py       # 缩略图生成
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── vision.py        # 图片分析（Ollama + 视觉模型）
│   │   ├── text.py          # 文本分析（摘要+标签）
│   │   └── models.py        # AI 响应解析
│   ├── api/
│   │   ├── __init__.py
│   │   ├── server.py        # FastAPI 应用
│   │   ├── routes_assets.py
│   │   ├── routes_tags.py
│   │   ├── routes_search.py
│   │   ├── routes_scan.py
│   │   ├── routes_config.py
│   │   └── routes_paths.py
│   └── web/                 # 前端静态文件
│       ├── index.html
│       ├── assets/
│       └── ... (React build 输出)
├── frontend/                # React 前端源码
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── AssetGrid.tsx
│   │   │   ├── AssetCard.tsx
│   │   │   ├── DetailPanel.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── TagChip.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── hooks/
│   │   │   ├── useAssets.ts
│   │   │   ├── useTags.ts
│   │   │   └── useSearch.ts
│   │   └── api/
│   │       └── client.ts
│   ├── package.json
│   └── tailwind.config.js
├── pyproject.toml
└── README.md
```

## 13. 实现计划

### Phase 1 — 核心骨架（扫描 + 存储）

- [x] 需求分析完成
- [ ] 项目初始化（pyproject.toml, 目录结构）
- [ ] SQLite schema + 迁移
- [ ] 配置管理（config.yaml 读写）
- [ ] 文件扫描引擎（扩展名白名单、inode 匹配、SHA256）
- [ ] 元数据提取（图片尺寸、视频/音频信息）
- [ ] 缩略图生成（异步队列）
- [ ] CLI 命令：scan, list, search, paths, stats

### Phase 2 — Web UI MVP

- [ ] FastAPI 基础框架
- [ ] 素材列表 + 筛选 API
- [ ] 标签 CRUD API
- [ ] FTS5 搜索 API
- [ ] React 前端搭建
- [ ] 侧边栏 + 素材网格
- [ ] 详情面板（查看 + 编辑描述/标签）
- [ ] CLI 命令：serve

### Phase 3 — 实时监听

- [ ] fsevents 监听器
- [ ] 文件变更事件处理（create/modify/move/delete）
- [ ] 启动全扫 + 监听自动衔接
- [ ] 缩略图状态标记（pending → done）

### Phase 4 — AI 分析

- [ ] Ollama 连接管理
- [ ] 图片分析流水线（视觉模型 → 描述 + 标签）
- [ ] 视频首帧分析
- [ ] 文本分析流水线（LLM → 摘要 + 标签）
- [ ] AI 标签 UI（虚线边框 + 确认/移除）
- [ ] 设置页（模型配置）

### Phase 5 — 打磨

- [ ] 视图切换（网格/列表）
- [ ] 排序选项
- [ ] 重复文件展示
- [ ] 版本历史查看
- [ ] 性能优化（大批量滚动）
- [ ] 错误处理 + 日志

## 14. 风险与注意事项

| 风险 | 应对 |
|------|------|
| SHA256 大文件慢 | 异步后台计算，超大文件可选跳过 |
| fsevents 事件丢失 | 启动全扫 + 定时校验兜底 |
| AI 模型质量不稳定 | 标签为辅助，用户可编辑覆盖 |
| 中文分词搜索不准 | FTS5 unicode61 tokenizer + 后续接 jieba |
| 缩略图存储膨胀 | 256px max，定期清理无引用缩略图 |
| Ollama 未安装/未运行 | 首次启动引导检测，提示安装，AI 功能可降级 |

---

文档版本: v1.0
创建日期: 2026-06-01
