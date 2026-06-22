# QuickMedia v10 技术方案 ✅ 完成

## 涉及模块

| 文件 | 变更 |
|------|------|
| quickmedia/config.py | _migrate_watch_paths + DEFAULT_CONFIG 更新 |
| quickmedia/api/server.py | GET/PUT watch-paths, /api/folder-picker, /api/task-models, scan 日志 |
| quickmedia/scanner.py | reload_watch_paths, scan 缩略图即时处理 |
| frontend/src/App.tsx | ckCfg, 首次引导, 红点, 扫描保护 |
| frontend/src/SettingsModal.tsx | FoldersTab, tabDots, 保存提示 |
| frontend/src/ModelManager.tsx | onModelsSaved 回调 |

