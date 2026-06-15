# QuickMedia v4 Tasks

> to-issues 输出。基于 PRD.md。全部完成 ✅

## 依赖关系

```
Slice 4.1 (API 筛选后端) ──→ Slice 4.3 (筛选栏前端)
Slice 4.2 (标签清理) — 独立
```

---

## Slice 4.1: API 筛选后端 ✅

- **类型**: AFK
- **阻塞**: 无
- **覆盖**: US-1 (日期区间), US-2 (文件格式), US-3 (AI 状态), US-4 (组合筛选)

### 任务清单

- [x] `GET /api/assets` 新增查询参数：`date_from`, `date_to`, `mdate_from`, `mdate_to`
- [x] `GET /api/assets` 新增查询参数：`formats`（逗号分隔扩展名）
- [x] `GET /api/assets` 新增查询参数：`tags`（逗号分隔 tag ID）
- [x] `GET /api/assets` 新增查询参数：`ai_status`（逗号分隔状态值）
- [x] 所有筛选条件取交集，与已有 `type` 参数兼容
- [x] 筛选返回 `extension` 字段供前端展示

---

## Slice 4.2: 标签清理 ✅

- **类型**: AFK
- **阻塞**: 无
- **覆盖**: US-5 (标签列表整洁)

### 任务清单

- [x] 启动时识别并删除 source='auto' 的时间标签
- [x] 启动时识别并删除 source='auto' 的格式标签
- [x] 启动时识别并删除 source='auto' 的类型标签
- [x] 清理孤立的 tags 记录（无 asset_tags 关联的标签）
- [x] Scanner._auto_tags 不再生成时间/格式/类型标签
- [x] Scanner._auto_tags 保留时长段标签（短片/中片/长片）

---

## Slice 4.3: 筛选栏前端 ✅

- **类型**: AFK
- **阻塞**: Slice 4.1
- **覆盖**: US-1~6

### 任务清单

- [x] 类型筛选保留侧边栏展开式
- [x] 创建时间 + 修改时间日期区间控件
- [x] 文件格式下拉多选（默认「点击筛选」，选中显示「已选 N 项」+ ✕）
- [x] AI 状态下拉多选（同格式交互）
- [x] 标签下拉多选（输入框展示已选标签名，逗号分隔，高度自适应）
- [x] 标签多选取并集（OR）
- [x] 筛选条件变化通过 useEffect 自动触发 API 刷新
- [x] 已激活筛选用珊瑚色标记

---

## 完成统计

| 切片 | 状态 |
|------|------|
| 4.1 API 筛选后端 | ✅ |
| 4.2 标签清理 | ✅ |
| 4.3 筛选栏前端 | ✅ |
| **总计** | **136 tests** |
