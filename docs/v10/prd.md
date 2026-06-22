# QuickMedia v10 PRD — 可配置扫描文件夹 ✅ 完成

## Problem Statement

QuickMedia 装完后用户不知道去哪配扫描路径。现在 `watch_paths` 硬填在 `config.yaml` 里，对非技术用户不友好。首次进入 Web 看不到任何素材，没有引导，用户流失。

## Solution

**浏览器文件夹选择器 + 配置 UI**：用户通过 Web 界面添加/管理扫描目录。首次无配置时自动拉起配置弹框。配置后即时生效无需重启。

## User Stories

1. 作为新用户，安装后首次打开 Web，自动弹出设置弹框并定位到文件夹配置 Tab，引导我配置第一个扫描目录
2. 作为新用户，我看到设置入口有红点提示，知道还有未完成的必要配置
3. 作为用户，我点击"选择文件夹"按钮，系统拉起 Finder/文件夹选择器，我选中后路径自动填入
4. 作为 macOS 用户，文件夹选择器调用系统 Finder，体验原生流畅
5. 作为 Windows/Linux 用户，文件夹选择器不可用时，我可以手动输入路径并看到目录是否存在提示
6. 作为用户，我配置完文件夹后保存，Tab 上红点消失
7. 作为用户，模型配置和文件夹都配完后，设置入口的红点才消失
8. 作为用户，我给每个文件夹命名（"设计稿"、"参考图"），方便区分管理
9. 作为用户，我可以临时禁用某个文件夹的扫描而不删除配置
10. 作为用户，保存文件夹配置后立即可扫描，不需要重启服务
11. 作为用户，点击"扫描新素材"时如果未配任何文件夹，弹出提示并帮我打开文件夹配置
12. 作为旧用户升级到 v10，之前配置的 `watch_paths` 自动迁移为新格式，数据不丢失
13. 作为用户，我可以配置文件夹是否递归扫描及最大深度

## Implementation Decisions

- **存储**：`config.yaml` 的 `watch_paths` 数组，结构：`{name, path, recursive, max_depth, enabled}`
- **文件夹选择**：macOS 用 `osascript choose folder`（服务端），其他平台回退手动输入
- **自动迁移**：启动时检测 watch_paths 项无 `name` 字段，补 `name: "默认文件夹"` + `enabled: true`
- **热加载**：API 保存后调用 watcher 重启逻辑，不重启服务
- **红点逻辑**：设置总入口红点 = 模型+文件夹两项全部完成才消；Tab 红点 = 各自保存即消
- **首次引导**：`App.tsx` onMount 检测 `watch_paths` 是否为空，空则 `sso(true)` + 预设文件夹 Tab
- **扫描未配提示**：`/api/scan` 检测无 watch_paths 时返回错误提示，前端拉起配置
- **API 契约**：
  - `GET /api/config/watch-paths` → `{paths: [...]}`
  - `PUT /api/config/watch-paths` body: `{paths: [...]}` → 保存 + 热加载
  - `POST /api/folder-picker` → `{path: "..."}` 或 `{error: "..."}`

## Testing Decisions

- **API 层**：HTTP 测试（参考 `test_v6_config.py`），覆盖读/写/迁移/空列表
- **配置层**：单元测试 Config 的 watch_paths 读写和旧格式迁移
- **Scanner**：验证 `enabled=false` 的路径跳过扫描
- **前端**：HITL — 验证首次引导弹框、红点、文件夹选择 UI
- **文件夹选择器**：单元测试 osascript 调用返回路径解析

## Out of Scope

- 格式筛选（每个 watch path 的 include/exclude formats）
- 网络路径（NAS/SMB）支持
- Docker 环境文件夹选择

## Further Notes

- 用户现有配置 `~/Desktop/test_media` 将自动迁移为 `{name: "默认文件夹", path: "~/Desktop/test_media", recursive: true, max_depth: 2, enabled: true}`
- V10 完成后同步更新 CONTEXT.md、PRD.md、ROADMAP.md、docs/v10/tasks.md
