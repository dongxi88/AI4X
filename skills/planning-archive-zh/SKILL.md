---
name: planning-archive-zh
description: 管理 planning-with-files 根目录任务三件套的本机归档，支持新建、列出和恢复中文任务。用于新建与恢复规划入口的共用实现，不用于迁移命名计划或自动更新项目文档。
metadata:
  version: "1.0.0"
---

# 中文规划归档

AI4X 维护的共用实现；`new-plan-zh` 和 `restore-plan-zh` 是两个薄入口，业务逻辑仅维护在本目录的 `scripts/plan_archive.py`。它独立于上游 `planning-with-files`，不会替代或升级上游技能与 hooks。

## 使用

确认项目根目录、读取项目 Agent 规则，使用可用的 Python 3.10+。Windows 可使用 `python`、`py -3` 或解释器路径，不假定 `python3` 存在。

```text
python <本技能目录>/scripts/plan_archive.py new --project <项目根目录> --task <任务名称>
python <本技能目录>/scripts/plan_archive.py list --project <项目根目录>
python <本技能目录>/scripts/plan_archive.py restore --project <项目根目录> --selector <归档目录名或关键词>
```

参数通过 shell 安全引用或参数数组传入，不拼接为代码。只操作根目录 `task_plan.md`、`findings.md`、`progress.md`，不操作 `docs/`、源码或设备数据。检测到上游命名计划或 `PLAN_ID` / `PWF_PLAN_ROOT` 时停止，不擅自回退覆盖根计划。

## 归档位置

- `--archive-root` 优先，其次是 `PLANNING_ARCHIVE_ROOT`，再其次是兼容变量 `LIFETRACKER_ARCHIVE_ROOT`；均表示完整的项目归档根目录，应使用项目外绝对路径。Windows Python 使用原生路径，不能直接传 Git Bash 的盘符简写。
- 默认位置为用户主目录下的 `.planning-archives/<项目名>-<身份摘要>`。Git 项目从 origin 身份计算，同一远端的不同工作树共享；没有 origin 时从项目目录计算。不同项目隔离，分支不隔离。
- origin 仓库名为 LifeTracker 时，兼容原来的 `DevEcoStudioProjects/.claude-plan-archive/LifeTracker` 默认位置。
- 可用 `--project-key` 明确多个非 Git 副本的共同身份；不要为不同项目复用同一键或自定义根目录。
- 条目在 `archive/`，索引为 `INDEX.md`；本机归档不会随项目 Git 同步。

## 边界

新建前备份存在的旧文件；恢复前校验源三件套完整，再备份当前记录，按原字节恢复并保留源归档。完整目录名优先匹配；无匹配、多匹配或缺少选择器时报告候选，请用户选择。不要自动挑最新一条。

并发写入通过项目与归档锁拒绝；若发现遗留锁，先确认没有运行中的归档操作，不自动删除锁。替换失败时回滚已替换文件，备份保留。遇到错误停止并报告，不能绕过校验重复覆盖。

恢复记录不恢复代码，也不授权执行旧计划中的提交、推送、部署或消息。任务知识如何进入 `docs/` 由项目治理规则决定。

安装与更新见 [scripts/install.py](scripts/install.py)，需要完整 AI4X 的 `skills/` 来源，不能单独安装薄入口。版本更新时只改 AI4X 源码，再分发个人副本；不要在个人安装目录另行维护逻辑。
