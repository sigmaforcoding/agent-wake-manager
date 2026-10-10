# Milestone contracts (draft)

`awm.event/1`、`awm.config/1`、`awm.status/1` 是本里程碑草案，尚非公开稳定 v1。canonical 字段为 `generation`（与设计示例统一）；JSON schema 描述投影后的对象，入口代码先白名单投影，未知/body 字段被忽略，不记录拒绝值。完整 JSON 解析允许接收上游附带字段，不承诺从未接收正文字节。

## Event

Required: schema、event_id、instance_id、provider、kind、session_id；非 session 事件须 task_id。generation 默认1。开始/等待事件须 owner 的正整数 pid 和 bounded birth；本核心不自行查询或认证真实进程，这些身份是输入元数据。tool 事件须 tool_id。

任务键为 `(instance_id, session_id, task_id, generation)`。instance 必须在配置注册、启用、provider匹配。event_id 按实例幂等，同 ID 不同 canonical 元数据报 EVENT_CONFLICT。UTC occurred_at 只用于元数据，不作为超时结束依据。错误是固定代码，不输出字段值。

开始/恢复只更新该逻辑任务；新代际替代同逻辑键旧 hold。旧代际、终态后迟到 start/tool 不能复活。明确 session.closed 封闭该 session 的主任务，新会话须使用新逻辑 ID；已存在独立 child/background 不被父 Stop/SessionEnd 清掉。每个持有者须自己终止或有完整可信进程表证明死亡。

Pause 只停止 lease 意图，不停止事件处理。Reset 需显式确认，只清任务、写终态，不改 paused。进程观察为 None 时保留；有效空表表示确实没有进程；完整表验证通过后才事务 reap。真实观察器尚未实现，调用者不得把错误/部分表传成空表。

normalize_hook 的有限映射：SessionStart/End、UserPromptSubmit、Stop/StopFailure/Interrupt、PermissionRequest、Pre/PostToolUse/Failure、SubagentStart/Stop。未读工具输入或响应，因此旧后台输出识别和 resume 输入识别不再提供。native turn 缺失时暂用 main，generation 必须由未来 adapter 提供；此函数还不是可安装的真实客户端 handler。

有 native event ID 才能识别上游重复；否则生成投递 UUID，任务键/墓碑仍提供语义幂等，但不承诺 exactly-once。审计/墓碑/代际保留策略、本地多 CLI 并发日志导出、完整实例移除流程留到下一阶段，不宣称已产品化。

## Config

任意实例数组，id 唯一，provider 为 codex/claude/process_wrapper/other，enabled 为布尔值，可选 config_root 为登记路径。没有固定的两个 CODEX_HOME，也没有 API/模型/凭据字段或自动扫描。禁用实例拒绝新事件，不自动删除其既有任务；真正的启停/移除迁移流程未实现。

## Status

任务数、每实例计数和 paused 来自开发库；lease_intent 为 task_count>0 且未暂停。service_alive、lease_alive、amphetamine_active 为 null，表示本里程碑没有外部观测，不把意图当保护事实。status 是 CLI即时派生结果，不是现有服务的 runtime/status.json。
