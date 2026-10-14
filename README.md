# 金融秋招 Agent

面向金融校招的投递副驾驶。当前交付为 **Codex 技能组合 + 本地 Python/SQLite MVP**，不依赖 API Key。岗位解析、材料定制和面试由 Codex 按技能执行；确定性的数据处理交给 agent.py。

## 使用

六个 Skill 已安装在本机 `/home/wangxinghan/.codex/skills/`，项目 skills/ 留有可迁移副本。新会话中可以请求：

> 使用 $campus-application-agent，为我汇总 2027 届深圳金融科技岗，先匹配，再生成简历草稿和投递清单。

编排技能调用五个业务技能：金融岗位汇总、精准匹配、简历定制、投递追踪、模拟面试。技能安装后通常在新会话中发现；当前会话也可直接读取 SKILL.md 使用。

```bash
cd 金融秋招Agent
python3 agent.py sources
python3 agent.py fetch boc
python3 agent.py discover data/raw/抓取文件.raw --keyword '校园招聘'
python3 agent.py fetch boc --url https://www.boc.cn/aboutboc/bi4/202609/t20260903_25689311.html
python3 agent.py import /绝对路径/jobs.json
python3 agent.py match /绝对路径/profile.json
python3 agent.py track 岗位job_key prepared --next-action '核实期限并人工网申'
python3 agent.py track 岗位job_key submitted --evidence '用户确认已提交，回执编号…'
python3 agent.py list-applications
python3 agent.py health
python3 -m unittest discover -s tests -v
```

`fetch` 下载注册入口或同域公告详情，失败返回非零退出码。`discover` 从已下载页面中提取符合关键词的同域公告链接（目前支持 UTF-8 HTML，不执行 JavaScript）。官方动态源的本轮研究快照和分页采集器位于 `data/research/2026-10-13/` 与 `scripts/`，仅复用已在匿名浏览器中观察到的真实请求形状；不会使用未验证的接口模板或绕过验证。

本轮岗位总览见 [`项目概述.md`](项目概述.md)、[`汇总/2026-10-13/岗位总览.html`](汇总/2026-10-13/岗位总览.html) 和 [`汇总/2026-10-13/覆盖与缺口.md`](汇总/2026-10-13/覆盖与缺口.md)。总表、Excel、CSV、JSON 和 SQLite 快照都在同一目录。采集器依赖见 `requirements-collection.txt`；`agent.py` 本身仍只使用标准库。

## 跑通验证（2026-10-13）

执行以下命令可以重跑联网验证，结果写入独立的 data/verification/时间戳/ 目录，不影响正式岗位库：

```bash
python3 scripts/verify_flow.py --live
```

已实测中国银行与邮储入口抓取、中国银行公告发现及详情抓取、3 条真实岗位摘要导入、重复导入去重、截止过滤、状态幂等与证据检查。9 项单元测试通过。`examples/boc-2027-jobs.json` 是 Codex 根据已保存的官方公告整理的摘要，重跑脚本使用该固定摘要，不会重新自动解析最新公告。`examples/demo-profile.json` 是虚构测试画像。

本次中行公告截止日期为 2026-10-09，三个岗位在测试中全部正确排除。模拟 submitted 事件仅写入隔离测试库，未执行真实投递。本轮已对一批官方动态源完成只读分页核验，但仍有源故障、公告项目未拆岗和跨源语义重复，具体见覆盖说明。登录网申尚未自动化；材料定制和模拟面试由 Codex 按 Skill 交互执行。

## 数据源

`data/sources.json` 当前登记 325 个来源条目，包含机构入口、公告地址、聚合入口及待核实渠道。条目数不是机构数，也不是可运行适配器数。用户提供的 13 家银行、6 家券商、4 家保险等原始名单仍保留；本轮扩展的来源和原始页面存入 `data/research/2026-10-13/`。

每个来源的实际采集结果见[覆盖与缺口](汇总/2026-10-13/覆盖与缺口.md)。页面可访问不代表岗位在招；没有确切 URL 的源保留空值。建信部分子公司、公众号和监管报名平台仍有待补齐的细节。

官方源优先；聚合源补充发现；BOSS/猎聘只接收用户主动采集。用户提供的公告数量、招聘计划及聚合工具统计未当作已核验事实，也不写入岗位条件。招聘季时间只用于背景提示，实际提醒必须依据具体公告。

## 已实现与后续

已实现：注册表、公开页面原文保存、字段校验、机构层级与招聘批次去重、幂等更新、关键词可解释匹配、证据化状态追踪、页面抓取健康统计；简历和模拟面试通过 Skill 交互完成。

待实现：把已验证的分页采集器纳入定时任务、自动公告发现与 JD 抽取、语义召回、LangGraph 编排服务、Web 看板、浏览器扩展、日程提醒、PDF/DOCX 导出。当前不是完整联网自动投递应用。用户画像和岗位数据默认为本地文件，脚本不上传简历。

## 核验参考

- [中国银行招聘公告](https://www.boc.cn/aboutboc/bi4/)
- [邮储银行校园招聘](https://www.psbc.com/cn/gyyc/rczp/xyzp/)
- [中国人民银行](https://www.pbc.gov.cn/)
