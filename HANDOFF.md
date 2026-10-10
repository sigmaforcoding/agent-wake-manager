# 隔离开发核心小里程碑 — 2026-10-10

本轮已完成，停在此处；不自动进入下一阶段。

## 当前状态

- 独立本地 Git 仓库，无远程，不发布。MIT只是倾向，未创建 LICENSE，来源审查见 SOURCES.md。
- 已引入 Python Core、标准JSON白名单契约、有限 normalize_hook 函数、显式独立数据目录的 CLI、三份 canonical schema、合成实例示例与测试。
- 不含 GUI/lease二进制、服务、安装器、登录注册、Scanner、真实进程观察器、账户测试或电源调用。
- pause保留任务且继续事件归约；resume恢复仍活跃任务意图；reset需确认，仅清任务，不隐式pause/resume。
- 39项合成测试成功，完整原文 docs/TEST-RESULTS.txt。敏感标记覆盖直接Core和CLI入口的DB、审计日志、错误、状态输出；输入元数据本身仍是本地敏感信息，不声称任意字段投毒都能过滤。
- ID/generation处理更严格：旧代际不产生额外hold、终态不被迟到事件复活、关闭session不接受新主任务。未来真实会话恢复需adapter定义新逻辑session身份，不能假装已经处理所有Provider情况。
- 模型/API、凭据、业务内容不配置/读取；JSON接收上游附带内容字段允许，但不使用正文。

## 实验版隔离检查

对43个实验版静态源码/文档/app资源/CLI链接及用户Hooks/LaunchAgent记录了尺寸、mtime、权限和链接目标。只有用户授权更新的 OPEN_SOURCE-V1-DESIGN.md 改变；其余无变更、无新增实验版静态文件。服务仍running、PID78002、last exit0，没有安装/重启/切换。实验版runtime及Hooks对本聊天的自动记录会自行更新，未作为静态不变断言。

没有访问Amphetamine容器plist或调用其写配置/会话操作；因此没有把“未访问”伪装成已比对其文件字节。用户人工截图结论已限范围记录在设计支持矩阵和 docs/SUPPORT.md，不伪造图像路径，不扩展GUI按钮/其他客户端/合盖。

## 精确下一步建议（需下一轮指令）

只完成Codex adapter的脱敏原生元数据fixture：明确native event ID/turn/generation映射、遗漏终止事件降级、稳定owner采集边界，并用合成测试验证，不安装Hook、不读取真实账号会话。然后再决定是否授权小范围真实客户端验证。

禁止主动做：Swift迁移、GUI设置页、安装器/登录、Python打包、GitHub发布或开源许可证正式采用。当前实验版继续使用，不能把此开发目录替换其服务根。
