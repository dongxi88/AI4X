---
name: new-plan-zh
description: 归档当前项目的 planning-with-files 根目录三件套并创建新的中文任务记录。用户要求新建规划、切换任务或调用 new-plan-zh 时使用，延续当前任务无需新建。
metadata:
  version: "1.0.0"
---

# 新建中文规划

先读取同级 [planning-archive-zh/SKILL.md](../planning-archive-zh/SKILL.md)，遵循共用工具的路径、权限与数据保护约束。若共用技能缺失，停止并提示从 AI4X 完整安装，不重写替代脚本。

1. 确认项目根目录和用户给定的新任务名称。缺少名称时询问，不自行猜测。
2. 使用 Python 3.10+ 运行同级共用脚本：

   ```text
   python <本技能目录>/../planning-archive-zh/scripts/plan_archive.py new --project <项目根目录> --task <任务名称>
   ```

3. 读取输出中的备份位置及新三件套，填写实际需求、相关项目文档和验收条件。执行失败则停止并报告，不丢弃备份。
4. 后续复杂任务可继续使用已安装的上游 `planning-with-files`；此入口不负责安装上游，也不改动 `docs/` 或自动提交。
