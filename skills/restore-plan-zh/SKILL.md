---
name: restore-plan-zh
description: 从本机归档恢复 planning-with-files 根目录中文任务三件套，恢复前备份当前记录。用户要求恢复旧规划、继续归档任务或调用 restore-plan-zh 时使用。
metadata:
  version: "1.0.0"
---

# 恢复中文规划

先读取同级 [planning-archive-zh/SKILL.md](../planning-archive-zh/SKILL.md)，遵循共用工具的路径、权限与数据保护约束。若共用技能缺失，停止并提示从 AI4X 完整安装，不重写替代脚本。

1. 确认项目根目录与用户提供的归档目录名或关键词。没有选择器时，用以下命令列出最近 20 条记录，询问用户选择，不自动选最新一条：

   ```text
   python <本技能目录>/../planning-archive-zh/scripts/plan_archive.py list --project <项目根目录>
   ```

2. 选择明确时运行：

   ```text
   python <本技能目录>/../planning-archive-zh/scripts/plan_archive.py restore --project <项目根目录> --selector <归档目录名或关键词>
   ```

3. 零匹配、多匹配或归档缺少文件时停止并报告，让用户选择具体记录，不猜测。
4. 读取恢复后的全部三件套，说明目标、当前阶段、下一步及恢复前备份位置，并核对当前分支、代码和项目文档是否已变化。
5. 恢复记录不回退代码，也不自动授权旧计划中的提交、推送、部署或消息；按当前用户要求继续。此入口不操作 `docs/`。
