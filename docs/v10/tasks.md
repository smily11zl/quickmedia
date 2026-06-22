# QuickMedia v10 任务拆分 ✅ 全部完成

## Slice 10.1 — Config + 迁移 ✅

**目标：** watch_paths 结构升级、旧格式自动迁移、API 端点。

- [x] `quickmedia/config.py`: _migrate_watch_paths 方法，旧 string→dict 格式自动迁移
- [x] `quickmedia/api/server.py`: GET/PUT /api/config/watch-paths
- [x] `quickmedia/api/server.py`: /api/task-models 端点（红点判断用）
- [x] `quickmedia/scanner.py`: reload_watch_paths 热加载
- [x] 自动补齐 name/enabled 字段，向后兼容

## Slice 10.2 — 文件夹选择器 ✅

**目标：** macOS Finder 文件夹选择 + 跨平台回退。

- [x] `_parse_osascript_path` 函数：解析 osascript 输出为 POSIX 路径
- [x] `POST /api/folder-picker` 端点
- [x] macOS HFS 路径（冒号）自动转换为 POSIX（斜杠），去卷名
- [x] 跨平台 fallback

## Slice 10.3 — Settings FoldersTab ✅

**目标：** 文件夹配置 UI、增删改、保存热加载。

- [x] `SettingsModal.tsx`: FoldersTab 新 Tab
- [x] 添加/删除/编辑文件夹（名称/路径/递归/深度/启用）
- [x] 文件夹选择器按钮集成
- [x] 保存按钮 + 内联状态提示（与任务配置一致）
- [x] Tab 红点：未配置时显示
- [x] Scanner scan_directory 缩略图即时处理

## Slice 10.4 — 首次引导 + 红点 + 扫描保护 ✅

**目标：** 引导用户完成初始配置，视觉提示未完成项。

- [x] `App.tsx`: 首次无配置时自动拉起设置弹框
- [x] 设置入口红点：文件夹+模型都完成才消
- [x] Tab 红点：各自保存即消
- [x] `every` 模型检查（所有任务都配了才消红点）
- [x] 扫描按钮保护：未配路径时提示+拉起配置
- [x] SettingsModal initialTab 支持
- [x] `ckCfg` 实时刷新红点

## v10 测试覆盖

| 测试类 | 数量 | 覆盖 |
|--------|------|------|
| TestV10WatchPathsConfig | 6 | 迁移、结构、持久化 |
| TestV10FolderPicker | 3 | osascript 解析 |
| TestV10WatchPathsAPI | 4 | API 读写、删除 |
| TestV10FirstLaunchGuide | 2 | 空/非空检测 |
| **总计** | **15** | 15/15 passed |
