# Source review and provenance

逐文件提取，不复制实验版整个目录或 Git 历史。

| 新文件 | 来源与处理 |
|---|---|
| src/agent_wake_manager/core.py | 审查相邻实验版 manager_core.py 的 Store.connection、任务键、reap、墓碑及暂停代码；保留标准库短事务模式，按新协议改写实例/代际/暂停，删除 transcript、工具响应和旧 provider 特例路径。新 closed_sessions/generations、异库拒绝规则由合成回归驱动 |
| src/agent_wake_manager/contracts.py | 新建；参考实验版 hook.py 白名单提取思路，不复制其工具输入/响应、后台字符串识别、Scanner 或用户路径；普通 JSON 解析符合本轮已确认方向 |
| src/agent_wake_manager/__main__.py | 新建开发 CLI，只写显式隔离数据目录，无 install/uninstall/run/lid-test 或现场系统调用 |
| src/agent_wake_manager/__init__.py | 新建包标识 |
| tests/test_core.py | 审查实验版 test_manager.py；改编开始/结束、多实例、墓碑、权限等待、子任务、PID 复用、静默、观察失败等合成场景；新增暂停保留、暂停期间结束、新代际和异库保护。没有沿用 transcript 清理或真实账户结论 |
| tests/test_privacy.py | 新建合成敏感标记、忽略字段 trap、配置投影与错误过滤测试 |
| tests/test_cli.py | 新建临时目录/合成 stdin 的真实 CLI 子进程测试；不运行真实 Agent |
| schemas/*.json | 新建 canonical event/config/status 的最小机器可读契约 |
| examples/instances.json | 新建假实例/假 config_root，不取用户实际配置 |
| README、docs/*、HANDOFF、pyproject、.gitignore | 新建开发文档、构建声明和忽略规则；未安装打包依赖 |

明确排除：runtime、backups、research、真实配置、SQLite、二进制.app、原实验版 Git 历史、Swift GUI 源码（本轮不实现 GUI）以及模型/API/凭据。当前只审查了所引入文件，不宣称完成项目全部第三方许可来源核验；MIT 尚未正式采用，未创建 LICENSE。研究参考目录未引入，因此也不假定其许可覆盖本仓库。
