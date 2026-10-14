---
name: financial-job-collection
description: 汇总金融校招官方渠道、解析 JD、标准化去重并检查数据源健康度。
---

# 金融岗位汇总

项目路径：`/home/wangxinghan/人生规划/项目/金融秋招Agent`。先读项目 README.md，所有数据和脚本以项目为唯一来源。

子能力：source_registry → fetch_official_job → parse_financial_jd → normalize_job → dedupe_job → source_health。注册表是数据源事实来源。优先官方；聚合信息用于发现，投递前回查官方。使用 agent.py sources/fetch/import/health。fetch 只保存页面原文，不宣称已获取职位列表。解析时把公告拆成具体岗位；每个条件附 evidence 原文。缺失值为 null 或空列表，不推测截止日期、届别和机构层级。读项目的字段契约.md。动态页需要浏览器只读核验；zhiye/hotjob 接口先确认真实网络请求，禁止套用未验证通用端点。BOSS/猎聘只接收用户主动提供的当前 JD，不后台抓取。公众号名称是用户提供线索，不等于已验证账号。
