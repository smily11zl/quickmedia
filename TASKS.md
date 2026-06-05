# QuickMedia 开发任务文档

> 基于 QUICKMEDIA_DESIGN.md 拆分为 10 个 tracer-bullet 垂直切片。
> 每个 slice 完成后可独立验证。

## 依赖关系

```
Slice 1 (骨架)
  └─→ Slice 2 (扫描)
        ├─→ Slice 3 (元数据+缩略图)
        │     └─→ Slice 5 (Web浏览) ──→ Slice 6 (详情编辑)
        │           ├─→ Slice 8 (AI图片) ──→ Slice 9 (AI视频+文本)
        │           └─→ Slice 10 (打磨)
        ├─→ Slice 4 (搜索+标签) ──→ Slice 5
        └─→ Slice 7 (fsevents)
```

---

## Slice 1: 项目骨架 + 第一个 CLI 命令

- **类型**: AFK
- **阻塞**: 无
- **覆盖**: 项目可运行，数据库可连接，配置可读写

### 任务清单

- [ ] 创建项目目录结构（quickmedia/quickmedia/ 包）
- [ ] pyproject.toml（依赖声明：无外部依赖起步）
- [ ] 配置管理模块（~/.asset-manager/config.yaml 读写）
- [ ] SQLite 数据库连接 + schema 创建（assets / tags / asset_tags）
- [ ] CLI 入口（quickmedia 命令）
- [ ] CLI 子命令：`quickmedia stats`（显示素材总数）

### 验证标准

```
$ quickmedia stats
素材总数: 0
图片: 0  视频: 0  音频: 0  文档: 0  其他: 0
```

---

## Slice 2: 扫描引擎

- **类型**: AFK
- **阻塞**: Slice 1
- **覆盖**: 文件扫描 → SHA256 哈希 → inode 匹配 → 入库 → 列表

### 任务清单

- [ ] 扫描引擎：遍历目录 + 扩展名白名单过滤
- [ ] SHA256 哈希计算
- [ ] inode + device 快速匹配
- [ ] 自动标签生成（素材类型、格式、时间段、监控来源）
- [ ] 重复文件处理（同 hash → 合并记录）
- [ ] 文件删除检测（磁盘文件不存在 → status='deleted'）
- [ ] CLI: `quickmedia scan [path]`
- [ ] CLI: `quickmedia list [--type image]`

### 验证标准

```
$ quickmedia scan ~/Desktop
扫描完成。新增 12，更新 3，跳过 45（已存在）

$ quickmedia list --type image
  ID  文件名              类型    大小       路径
  1   cat.png            图片    264KB     ~/Desktop/img/cat.png
  2   screenshot.png     图片    1.2MB     ~/Desktop/screenshot.png
```

---

## Slice 3: 元数据提取 + 缩略图

- **类型**: AFK
- **阻塞**: Slice 2
- **覆盖**: 图片/视频详细元数据 + 缩略图异步生成

### 任务清单

- [ ] 图片元数据提取（Pillow: 宽高、格式）
- [ ] 视频元数据提取（ffprobe: 分辨率、时长、编码、帧率）
- [ ] 音频元数据提取（ffprobe: 时长、编码、采样率）
- [ ] 缩略图生成队列（SQLite 任务表 + 后台线程）
- [ ] 缩略图状态标记（pending → processing → done → failed → skipped）
- [ ] 缩略图存储（~/.asset-manager/thumbnails/，256px max）
- [ ] 缩略图 API（GET /api/thumbnails/:id，返回二进制图片流）
- [ ] CLI: `quickmedia list` 增加显示宽高/时长

### 验证标准

```
$ quickmedia list --type video
  ID  文件名         类型    大小    时长     分辨率
  5   demo.mp4      视频    45MB    2:30    1920×1080

$ ls ~/.asset-manager/thumbnails/
  1.jpg  2.jpg  3.jpg  5.jpg
```

---

## Slice 4: 搜索 + 手动标签

- **类型**: AFK
- **阻塞**: Slice 2
- **覆盖**: FTS5 全文搜索 + 手动标签 CRUD

### 任务清单

- [ ] FTS5 全文索引（filename, description, ai_description, ai_summary, notes）
- [ ] 标签 CRUD（tags 表 + asset_tags 关联表）
- [ ] CLI: `quickmedia search "关键词"`
- [ ] CLI: `quickmedia tag <id> "标签名"`
- [ ] CLI: `quickmedia edit <id>`（编辑描述/备注）
- [ ] CLI: `quickmedia list --tag "标签名"`（标签筛选）

### 验证标准

```
$ quickmedia tag 1 "宠物"
已添加标签: 宠物 → cat.png

$ quickmedia search "猫"
  ID  文件名       描述                         标签
  1   cat.png      (无描述)                     宠物
  3   neko.jpg     AI: 一只猫躺在沙发上           猫, 室内

$ quickmedia list --tag 宠物
  ID  文件名       类型
  1   cat.png     图片
```

---

## Slice 5: Web UI — 浏览素材

- **类型**: AFK
- **阻塞**: Slice 3, Slice 4
- **覆盖**: 浏览器打开 localhost，看到缩略图网格

### 任务清单

- [ ] FastAPI 应用框架 + CORS
- [ ] 素材列表 API（GET /api/assets，分页、类型筛选）
- [ ] 素材详情 API（GET /api/assets/:id）
- [ ] 搜索 API（GET /api/search?q=xxx）
- [ ] 标签列表 API（GET /api/tags）
- [ ] 统计 API（GET /api/stats）
- [ ] React 项目脚手架（Vite + TypeScript + TailwindCSS）
- [ ] 侧边栏组件（类型导航 + 素材计数）
- [ ] 素材网格组件（缩略图 + 文件名 + 标签摘要）
- [ ] 缩略图状态渲染（pending→灰色 / processing→旋转 / done→图片 / failed→错误图标）
- [ ] CLI: `quickmedia serve [--port 8088]`

### 验证标准

```
$ quickmedia serve
QuickMedia Web UI: http://localhost:8088

浏览器打开 → 看到缩略图网格 → 左侧点击"图片"/"视频"切换类型 → 计数显示正确
```

---

## Slice 6: Web UI — 详情 + 标签编辑

- **类型**: AFK
- **阻塞**: Slice 5
- **覆盖**: 点击素材看详情，编辑描述和标签

### 任务清单

- [ ] 右侧详情面板组件
- [ ] 元数据显示（类型/大小/尺寸/格式/创建时间/修改时间）
- [ ] 描述编辑（点击编辑，失焦自动保存）
- [ ] 手动标签管理（添加/删除，实线边框）
- [ ] 搜索框（实时过滤网格）
- [ ] 标签筛选联动（左侧点标签→网格过滤→取交集）
- [ ] 路径点击在 Finder 打开
- [ ] 更新素材 API（PUT /api/assets/:id）
- [ ] 素材标签管理 API（POST/DELETE /api/assets/:id/tags）

### 验证标准

- 点击素材 → 右侧显示详情
- 编辑描述 → 点别处自动保存 → 刷新还在
- 添加标签 → 左侧标签栏出现 → 计数+1
- 左侧点「宠物」→ 只显示有宠物标签的素材
- 搜索「cat」→ 所有相关素材显示

---

## Slice 7: fsevents 实时监听

- **类型**: AFK
- **阻塞**: Slice 2
- **覆盖**: 文件增删改自动感知，UI 实时更新

### 任务清单

- [ ] fsevents 监听器（watchdog Observer）
- [ ] 文件创建事件 → 新素材入库 + 缩略图入队
- [ ] 文件修改事件 → 重算哈希，hash 变 → 版本化 + 新记录入库
- [ ] 文件移动事件 → inode 匹配 → 静默更新路径
- [ ] 文件删除事件 → status='deleted'
- [ ] 启动全扫 + 监听自动衔接（serve 时先全扫再启动监听）
- [ ] WebSocket 推送（素材变更通知前端刷新）
- [ ] 监控路径管理 API（GET/POST/DELETE /api/paths）

### 验证标准

- 启动 serve → 全扫执行
- 拖一张图到监控目录 → 几秒后 UI 自动出现新素材（缩略图 pending→done）
- 重命名文件 → UI 路径更新
- 删除文件 → 素材标记 deleted，不出现在列表

---

## Slice 8: AI — 图片分析

- **类型**: HITL（需确认 AI 标签质量）
- **阻塞**: Slice 5, Ollama 环境（已就绪）
- **覆盖**: 新图片自动获得 AI 描述和标签

### 任务清单

- [ ] Ollama HTTP 客户端封装（调用 localhost:11434）
- [ ] 图片预处理（PIL 缩放到合适尺寸发给模型）
- [ ] 视觉分析 prompt 模板（场景描述 + 元素标签）
- [ ] 响应解析（提取 ai_description + auto_tags）
- [ ] AI 标签入库（source='auto'，虚线边框展示）
- [ ] AI 标签 UI 交互（点击确认→变实线，右键移除）
- [ ] 扫描时自动触发 AI 分析（异步，不阻塞扫描）
- [ ] 手动触发单个素材重新分析

### 验证标准

- 扫描一张新图片 → 等待分析完成
- UI 中素材出现 AI 描述（如"室内场景，暖色调..."）
- AI 标签显示虚线边框（如 [🐱 猫] [🌅 阳光]）
- 点击虚线标签 → 变实线（确认）
- 右键虚线标签 → 移除

---

## Slice 9: AI — 视频首帧 + 文本分析

- **类型**: AFK
- **阻塞**: Slice 8
- **覆盖**: 视频和文档也有 AI 分析 + 设置页

### 任务清单

- [ ] 视频首帧提取（ffmpeg 截取第 1 秒画面）
- [ ] 首帧走图片分析流水线
- [ ] 视频长度分桶自动标签（短片<5min/中片5-30min/长片>30min）
- [ ] 文档文本提取（.md/.txt 直接读，.pdf 用 pymupdf）
- [ ] 文本分析 prompt 模板（摘要 + 关键词）
- [ ] 文本分析响应解析（ai_summary + auto_tags）
- [ ] Web 设置页（Ollama URL + 模型选择 + 连接检测）
- [ ] 配置 API（GET/PUT /api/config）

### 验证标准

- 扫描视频 → 首帧描述 + 长度分桶标签
- 扫描 md 文件 → 摘要 + 关键词标签
- 打开设置页 → 显示当前模型 → 可切换 qwen3.5:4b/9b/27b
- 点「检测连接」→ 显示 Ollama 状态

---

## Slice 10: 打磨

- **类型**: HITL（需用户决定优先级）
- **阻塞**: Slice 5
- **覆盖**: 体验优化

### 任务清单

- [ ] 视图切换（网格 / 列表）
- [ ] 排序选项（按修改时间 / 文件大小 / 文件名）
- [ ] 重复文件展示（同 hash 素材合并显示 + 副本路径）
- [ ] 版本历史查看（文件被修改后的旧版本记录）
- [ ] 超大文件性能优化
- [ ] 错误处理 + 日志（~/.asset-manager/logs/）
- [ ] 自动打开浏览器（serve 时）

### 验证标准

- 切换到列表视图 → 表格展示
- 按大小排序 → 最大文件排前面
- 有副本的素材 → 显示「有 2 个副本」标记
- 文件被编辑过 → 详情显示版本历史入口

---

## 开发约定

- **TDD**: 每个功能模块先写测试（RED），再写实现（GREEN），通过后重构（REFACTOR）
- **垂直切片**: 每个 slice 是一次 tracer bullet，完成后可独立验证
- **测试只测行为**: 测试通过公共接口验证行为，不测内部实现
- **禁止水平切片**: 不要把所有测试写完再写实现
