# QuickMedia v5 需求规划

> 基于 [PRD.md](../../PRD.md) 的需求细化。

## 需求决策

| # | 决策项 | 决策 |
|---|--------|------|
| 1 | Prompt 存储 | 独立文件 `~/.asset-manager/prompts.yaml` |
| 2 | 配置结构 | 扁平式（custom/presets 与 system_format/default 同级） |
| 3 | 分析类型 | 全部 4 个开放自定义（vision/text/speech/video_summary） |
| 4 | 预设数量 | 图片 5 + 文档 4 + 语音 4 + 视频 1 = 14 个 |
| 5 | UI 交互 | Tab 切换 + 预设按钮行 + textarea 编辑 + 保存 |
| 6 | 读取时机 | 每次分析时实时读取，修改即时生效 |

## prompts.yaml 结构

```yaml
vision:
  system_format: |
    输出格式：
    描述：<描述文本>
    标签：<标签1>, <标签2>, <标签3>, ...
    文字：<文字1>, <文字2>, ...
  default: |
    请描述这张图片的场景、整体风格和色调（50字以内）。
    然后列出图片中出现的具体元素（人物、动物、物体、建筑、文字等），
    以逗号分隔的标签形式输出，标签使用中文。
    如果图片中有文字，请识别并以逗号分隔输出。
  custom: ""
  presets:
    - name: 摄影
      content: |
        请分析这张照片的构图方式（三分法/中心/对称等）、光线方向与强度、
        色彩搭配和景深效果。列出画面中的摄影元素和视觉焦点。
    - name: 设计
      content: |
        请分析这张图片的版式布局、色彩方案、字体风格和设计风格。
        识别 UI 组件、图标和交互元素。
    - name: 宠物
      content: |
        请描述图片中宠物的品种、毛色、体态和数量。
        描述宠物所在环境和行为状态，列出画面中的宠物相关元素。
    - name: 人物
      content: |
        请描述图片中人物的性别、大致年龄、表情、穿着风格和姿态。
        识别配饰、妆容特征和人物在画面中的位置关系。

text:
  system_format: |
    输出格式：
    摘要：<摘要文本>
    标签：<标签1>, <标签2>, ...
  default: |
    总结以下文档内容（200字以内），并提取5-10个主题关键词作为标签。
    关键词以逗号分隔，使用中文。
  custom: ""
  presets:
    - name: 技术文档
    - name: 笔记日记
    - name: 学习总结

speech:
  system_format: |
    输出格式：
    摘要：<摘要文本>
    标签：<标签1>, <标签2>, ...
  default: |
    以下是一段语音转录文本。请总结这段语音的主要内容（150字以内），
    并提取5-10个主题关键词作为标签。关键词以逗号分隔，使用中文。
  custom: ""
  presets:
    - name: 会议记录
    - name: 采访对话
    - name: 学习总结

video_summary:
  system_format: ""
  default: |
    请将以下两段关于同一视频的描述融合为一段综合总结（200字以内）：
  custom: ""
  presets: []
```

## 生效机制

```
用户自定义 prompt（custom 字段不为空）
    ↓ 如果 custom 为空
系统默认 prompt（default 字段）
    ↓
+ system_format 追加
    ↓
最终发送给 AI 的 prompt
```
