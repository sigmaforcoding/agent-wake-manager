# Agent Wake Manager — isolated development core

<img src="assets/AppIcon.png" alt="Agent Wake Manager icon" width="128">

这是与已安装实验版隔离的小里程碑，不是 macOS 发行包。保留 Python Core + Swift GUI 方向；当前仅实现 Python 元数据核心，没有 GUI、服务、安装器、登录注册、解释器打包或电源后端。首批产品目标 macOS 14+ / Apple Silicon；Intel 未验证。此核心本次使用现有 Python 3.9.6 测试，不要求安装依赖。

## 测试

```sh
PYTHONPATH=src python3 -B -m unittest discover -s tests -v
```

全部测试使用临时目录、合成事件和合成进程表。不会启动当前 LaunchAgent、Agent 客户端、lease 或 Amphetamine，也不访问用户配置。成功原文见 `docs/TEST-RESULTS.txt`。

## 开发 CLI

无需 pip install，显式指定独立数据目录：

```sh
PYTHONPATH=src python3 -B -m agent_wake_manager --data-dir .local/demo --config examples/instances.json status
PYTHONPATH=src python3 -B -m agent_wake_manager --data-dir .local/demo --config examples/instances.json pause
PYTHONPATH=src python3 -B -m agent_wake_manager --data-dir .local/demo --config examples/instances.json resume
PYTHONPATH=src python3 -B -m agent_wake_manager --data-dir .local/demo --config examples/instances.json reset --confirm
```

`event` 从 stdin 接收 `awm.event/1` JSON，提交到指定目录的 SQLite。不得把已安装实验版的 runtime 当数据目录：核心在写入前拒绝其他数据库结构，不迁移现场数据库。没有默认 HOME 数据路径，没有安装入口。

- `pause` 保留任务，继续处理生命周期，只将 `lease_intent` 设为 false。
- `resume` 对仍活跃任务恢复意图。
- `reset` 明确警告、需要 `--confirm`，清理全部实例任务；保留当前暂停状态。已清理的旧代际不能被迟到事件复活。
- `lease_intent` 只是意图。`service_alive`、`lease_alive`、`amphetamine_active` 都为 null：本里程碑没有实现这些外部观测。

## 隐私

使用标准 JSON 解析，不开发特殊解析器。官方 Hook 可能附带内容字段；`normalize_hook` 只取白名单元数据，不使用 prompt、回复、文件内容、tool_input、tool_response、transcript_path 或凭据。Core 再投影一次，防止绕过适配器后直接持久化正文。错误仅固定代码，不回显原输入；审计日志只含 canonical event。

没有 Scanner，不扫描 JSONL、聊天数据库、业务目录，不调用模型/API，不读写容器 plist，不调用 AppleScript/pmset，不联网。配置中的 config_root 只是登记信息，本里程碑不访问该路径。协议允许 opaque ID 与进程出生标记；这些元数据仍是本地私有信息。不能把敏感内容故意放入合法元数据字段后宣称任意信息流都已防泄露。

## 能力与限制

合成测试证明核心的多实例隔离、重复/迟到处理、代际与终态、暂停/恢复/reset、等待权限、已登记子任务独立持有、传入进程表的 PID 复用/观察失败语义，以及正文不落数据库、审计日志、错误和状态输出。

真实 Hook 版本、owner 采集、Claude 无 native turn 的代际分配、取消/失败回调、后台注册/PID 绑定、无 Hooks 进程包装和 GUI 均未在此开发版验证。未收到结束事件且宿主还活着时可能保守残留；不按静默时长清理，也不扫描正文补洞。关闭的 session ID 在本里程碑视为终态；真实会话恢复的逻辑 ID 路由待适配器实现。

Amphetamine 是未来实际运行时的外部依赖；本核心不实现自己的电源管理，不启动它，也不承诺未经条件化实测的合盖效果。实验版的用户截图证据只覆盖该实验版主 Codex 场景，不能转移成此核心或其他客户端的验证结论。详见 `docs/SUPPORT.md`。

公开开发仓库：[sigmaforcoding/agent-wake-manager](https://github.com/sigmaforcoding/agent-wake-manager)。更新直接提交到 `main`。许可证倾向 MIT，但来源审查未完成，本仓库没有正式 LICENSE。提取记录见 `SOURCES.md`。下一轮建议只完成一个 Codex 元数据 adapter 的合成原生事件 fixture 与代际映射，不安装真实 Hooks。
