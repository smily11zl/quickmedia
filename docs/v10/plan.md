# QuickMedia v10 — 可配置扫描文件夹

> 需求访谈记录。grill-me 时间：2026-06-22。✅ 完成

## 设计决策

### 1. 存储位置

`config.yaml` 的 `watch_paths` 数组。已有 Config 体系，改动最小。API 保存后热加载 watcher，无需重启。

### 2. 文件夹选择控件

浏览器 `showDirectoryPicker` + macOS 服务端 `osascript choose folder` 双通道。macOS 优先用 Finder，其他平台回退手动输入。

### 3. 授权

`showDirectoryPicker` 默认持久化授权，选一次永久生效。

### 4. 首次无配置时

进入 Web 自动拉起 SettingsModal，切到"文件夹配置"Tab。用 `sso(true)` + 预设 Tab 索引。

### 5. 红点提示

- 设置总入口：两项（模型配置 + 文件夹路径）都完成才消红点
- Tab 红点：各自保存即消
- 缺模型配置或缺文件路径都标红

### 6. 扫描按钮

未配路径时点击"扫描新素材" → Toast + 拉起文件夹配置 Tab。

### 7. 路径结构

```yaml
watch_paths:
  - name: "默认文件夹"       # 用户可命名
    path: "~/Desktop/test_media"  # 真实路径
    recursive: true
    max_depth: 2
    enabled: true
```

### 8. 文件夹选择器

前端按钮调 API → Python `osascript choose folder` → 返回真实路径填充输入框。同时保留手动输入 + 目录存在性验证（绿色/红色提示）。

### 9. 跨平台

macOS 用 Finder（osascript），Windows/Linux 回退手动输入。

### 10. 向后兼容

现有 `watch_paths` 配置自动迁移：启动时检测无 `name` 字段，补 `name: "默认文件夹"` + `enabled: true`。

### 11. 热加载

保存后调 `watcher.reload()` 即时生效，不重启。

## 涉及文件

| 文件 | 变更 |
|------|------|
| `quickmedia/config.py` | watch_paths 结构升级 + 迁移逻辑 |
| `quickmedia/api/server.py` | GET/PUT watch_paths 接口；文件夹选择器 API |
| `frontend/src/SettingsModal.tsx` | FoldersTab 新组件 |
| `frontend/src/App.tsx` | 红点逻辑；首次无配置自动拉起 |
| `quickmedia/cli.py` | 增强 watch_paths 读取 |
| `quickmedia/scanner.py` | 支持 enabled=true/false 过滤 |
