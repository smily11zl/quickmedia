# ADR-0004: 语音转录视频文件音频提取

## 状态

已采纳

## 背景

V19 新增远端口语音转 API（OpenRouter Whisper/Qwen ASR）作为转录模型。视频文件需先提取音轨再发送给 API。

## 决策

- 调度器检测到视频文件进入转录任务时，先用 ffmpeg 提取 MP3 音频到临时文件
- 本地 faster-whisper 直接传原文件路径（ffmpeg 内建处理），不提取临时文件
- 临时文件在分析完毕时删除

## 影响

- API 传输体积从几百 MB 视频降至几 MB 音频
- 需确认 ffmpeg 在目标环境可用
