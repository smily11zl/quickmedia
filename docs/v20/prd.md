# V20 PRD

## Problem Statement

排序仅 keyword 模式生效，语义/综合/AI 模式顺序混乱。用户无法按热度筛选高频素材。详情页缩略图模糊。

## Solution

1. 4 模式统一排序，语义/综合默认分数
2. 热度排序（view_count + open_count×3，等同→最近添加优先）
3. 新增"最近添加"排序（scanned_at）
4. 详情页原图缩略图（图片 800px + 视频 ffmpeg 首帧）
5. RGBA/CMYK 转 RGB 兼容

## User Stories

1. 用户切换任意搜索模式时排序生效
2. 向量/综合模式出现"相关性"排序项
3. 按热度找经常查看的素材
4. 按最近添加查看最新入库素材
5. 详情页缩略图清晰可见
6. 点击打开文件后热度权重提升（open×3）

## Implementation Decisions

- view_count/open_count 存 assets 表，DEFAULT 0
- 仅 Web UI 计数（?click=1），MCP 和 5 秒轮询不触发
- 缩略图：列表保留 256px 逻辑，详情用新 API 生成原图质量缩放
- 按修改时间：原名"按时间"，改名为"按修改时间"（modified_at）
- 排序切换：仅热度重新拉数据，其他重排内存

## Testing Decisions

- Seam: 前端排序逻辑修条件
- Seam: API GET /api/assets/{id} → view_count+1
- Seam: 新 thumbnail 参数控制质量

## Out of Scope

- MCP 访问计数
- 列表缩略图质量升级
