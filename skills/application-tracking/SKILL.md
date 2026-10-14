---
name: application-tracking
description: 管理金融校招申请状态、截止提醒和面试反馈。
---

# 投递追踪

项目路径：`/home/wangxinghan/人生规划/项目/金融秋招Agent`。先读项目 README.md，所有数据和脚本以项目为唯一来源。

使用 agent.py track/list-applications 记录状态和事件。prepared 只表示材料就绪；submitted 必须有用户确认或回执证据。状态：prepared/submitted/test/interview/offer/rejected/withdrawn。截止未知列为待核实，日期为 Asia/Shanghai。记录下次动作与时间，国考和事业单位单列赛道。不把打开投递页或点击按钮等同于提交成功。重复任务先检查回执和申请记录。
