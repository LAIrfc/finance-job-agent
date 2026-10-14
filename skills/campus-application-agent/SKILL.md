---
name: campus-application-agent
description: 编排金融校招岗位汇总、精准匹配、简历定制、投递追踪和模拟面试。
---

# 金融秋招 Agent

项目路径：`/home/wangxinghan/人生规划/项目/金融秋招Agent`。先读项目 README.md，所有数据和脚本以项目为唯一来源。

按用户目标选择技能，不需要每次全部调用。完整闭环：画像 → financial-job-collection → financial-job-matching → financial-resume-tailoring → application-tracking → financial-mock-interview。先检查画像是否完整，缺失条件标记待核实。投递默认由用户完成；只有用户明确授权特定岗位及材料的提交，才可执行外部投递。保存提交凭证后才能记为 submitted。失败停止，禁止盲目重复提交。
