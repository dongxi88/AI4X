# AI4X 技能

- [terminal-notify](terminal-notify/README.md)：Windows 终端通知。
- [planning-archive-zh](planning-archive-zh/SKILL.md)：中文规划归档的共用实现。
- [new-plan-zh](new-plan-zh/SKILL.md)：新建任务入口。
- [restore-plan-zh](restore-plan-zh/SKILL.md)：恢复任务入口。

## 规划归档安装与更新

在 AI4X 仓库根目录使用 Python 3.10+：

```text
python skills/planning-archive-zh/scripts/install.py --dry-run
python skills/planning-archive-zh/scripts/install.py --targets codex claude
```

三个技能需要同级安装。安装脚本先检查完整来源，为已有安装保留备份，统一更新两个 Agent 的个人副本，不修改模型、权限、上游插件或 hooks 配置。备份在用户主目录的 `.planning-skill-backups/`；安装副本在 `.codex/skills/` 和 `.claude/skills/`。不覆盖其他技能。CLI 或桌面端需要刷新技能或开启新会话以发现新增入口；Claude Code 的个人技能优先于项目中同名的旧 command 文件。

Codex 使用 `$new-plan-zh`、`$restore-plan-zh`，Claude Code CLI 和桌面端本地 Code 会话使用 `/new-plan-zh`、`/restore-plan-zh`。上游 [planning-with-files](https://github.com/othmanadi/planning-with-files) 独立安装和升级；此安装脚本不会安装它。其他 Agent 可适配这套标准技能文件，但本包尚未验证对应平台的加载机制。

从 AI4X 拉取经过审查的更新后，重复运行安装脚本；源码只在本仓库维护。若旧项目 `.claude/commands/` 还保留同名文件，应改为指向本技能的薄入口，避免继续维护另一套执行逻辑。若只用通用 skill 下载器安装两个入口而漏掉 `planning-archive-zh`，入口会停止并提示补齐安装。

## 归档兼容与项目隔离

只处理项目根目录三件套；命名计划 `.planning/<id>/` 尚不支持，检测到选定命名计划时停止。默认按 origin 项目身份隔离，同一 origin 的不同工作树可共享；没有 origin 时按目录身份隔离，可用 `--project-key` 明确共享身份。

LifeTracker origin 保留原本的默认归档位置与 `LIFETRACKER_ARCHIVE_ROOT` 变量。通用变量为 `PLANNING_ARCHIVE_ROOT`，优先级低于 `--archive-root`、高于旧变量。归档布局仍为 `archive/<时间戳>-<任务>/` 与 `INDEX.md`，旧的秒级时间戳记录也可恢复，不会迁移或删除已有归档。

## 与项目 docs 的分工

三件套记录任务上下文；归档负责保存和恢复这些记录。项目长期知识按所在项目的规则整理到 `docs/modules/`、`docs/adr/`、`docs/runbooks/`、`docs/plans/` 或 `docs/reports/`。工具不会自动发布、移动或提交项目文档，恢复记录也不会回退代码。

## 验证

```text
python -m unittest discover -s skills/planning-archive-zh/tests -v
```

测试在临时目录验证归档恢复、项目隔离、异常与失败回滚、安装备份，不使用真实任务记录。所有脚本仅依赖 Python 标准库。
