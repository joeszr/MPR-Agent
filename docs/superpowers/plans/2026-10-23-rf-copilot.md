# RF Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已有无线射频仿真改造成可复现、有引用、可执行工具且可评测的 AI 应用／后端求职项目，在 2027-01-31 前完成可面试版本。

**Architecture:** 保留既有功放与信号处理实现，提取显式配置的仿真核心，由 FastAPI、PostgreSQL、Redis 与独立 worker 进程提供异步实验服务。PostgreSQL 是任务状态的事实来源，Redis 承担任务队列、结果缓存与检索缓存。Qdrant 与 BM25 检索带版本的通信资料，LangGraph 编排四个受约束工具，输出带来源和实验依据的报告。先做一个用户的本地演示系统。

**Tech Stack（核心）:** Python、NumPy、SciPy、Pydantic、pytest、FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis、Qdrant、BM25、BGE embedding/reranker、LangGraph、HTTP LLM API、Streamlit、Docker Compose。
**Tech Stack（可选）:** MCP Python SDK（可选阶段 A）、Celery（可选阶段 B）。

**Spec:** [已认可设计](../specs/2026-10-23-rf-copilot-design.md)，用户已在本聊天认可；本文是其实施细化，不表示代码已经完成。

## 本版修订（2026-10-29）

- 计划按 **6 个核心阶段 + 2 个可选阶段** 组织，见下方「阶段总览」。
- **Celery 改为可选**（可选阶段 B）。核心任务队列用 Redis 列表（`rf:queue:jobs`／`rf:queue:processing`）和独立 worker 进程实现；硬超时由 worker 终止子进程完成。分发器保持 `enqueue(job_id)` 接口，日后换成 Celery 不改服务层。
- **保留 Redis**：负责任务队列、结果缓存（TTL 24h）和检索缓存（TTL 1h）。PostgreSQL 仍是任务状态的唯一事实来源。
- **MCP 改为可选**（可选阶段 A）：把 4 个 Agent 工具发布成 MCP Server，复用同一套白名单、参数校验和预算。
- 设计文档 §1、§6、§8 把 Celery 列为主线技术栈，**以本计划为准**；设计文档稍后同步。
- 核心工时由 154h 增至 158h（新增任务 0，4h，从机动时间支出）。两个可选阶段共 14h，只在启动条件满足时从剩余机动时间中支出。
- **现有代码也按功能重组（新增任务 0）**：根目录脚本、`PAmodel/`、`plotfigure/` 全部搬进 `src/rf_copilot/` 下对应的功能文件夹（功放模型、指标检测、原主程序、诊断、绘图），只改 import 路径和模块文件名，不改任何数值逻辑，用搬迁前后逐位一致的对照测试证明。
- **当前仓库状态（10/29 核对）：** Git 已初始化，共 3 个提交（最新为 `98de8b7`「添加 PAmodel 和 plotfigure 文件夹」），没有 `.gitignore`。功放模型已移入 `PAmodel/`，但根目录的 `apply_pa_model.py` 仍是 `from HZW_HB_am import ...`，导入时报 `ModuleNotFoundError`，所以**两个主程序目前无法运行**。任务 0 首先修复这一点。
- **执行方式：Native**（用户 10/29 选定）。本轮只写计划，收到开始指令前不动代码。
- **目录按功能分文件夹**（见「文件结构与共用约定」）：取消顶层 `scripts/`，命令入口放回各自功能包；分发器单独放在 `jobs/dispatch/`；新增 `config/`、`db/`、`evaluation/`；用量表移到 `llm/`，会话表移到 `agent/`；测试目录与源码目录一一对应；数据统一放 `data/`，文档分为 `docs/project/` 和 `docs/career/`。

## Global Constraints

- 每周总投入 20 小时，包含学习、刷题和项目，不是纯开发 20 小时。
- 初版只支持一个开发者／演示用户，不宣称多租户生产系统。服务只监听本机或受控开发网络，不把无鉴权演示实例公开发布。
- 先支持一个固定、经过验证的 FR1 参数档：100 MHz、30 kHz SCS、NRB=273；CP-OFDM 为主，DFT-s-OFDM 在兼容层回归，不同时开放所有标准组合。
- 没有参考功率时 `mpr_db=null`，报告说明原因。
- `pass`、`fail`、`not_evaluated`、`skipped`、`error` 分开；NaN／Inf 不直接输出为非标准 JSON。
- 上限：每次会话 6 次工具调用、最多提交 2 个实验；每实验最多 2 个 RB 配置、每配置最多 3 次试验；工作进程任务硬时限 120 秒，LLM 单次请求 30 秒，瞬态 API 错误最多重试 1 次。
- Redis 结果缓存 TTL 24 小时，只缓存 succeeded；读缓存失败回源 PostgreSQL。变更代码或阈值必须换 key。检索缓存 TTL 1 小时，key 包含语料、embedding 和 reranker 版本。
- Redis key 前缀固定：队列 `rf:queue:jobs`、`rf:queue:processing`，结果缓存 `rf:result:`，检索缓存 `rf:retrieval:`。Redis 使用 `maxmemory-policy noeviction`，防止队列消息被当作缓存驱逐。Redis 数据丢失只影响排队和缓存，不影响任务状态：由补偿扫描根据 PostgreSQL 重新入队。
- Celery 与 MCP 是可选项：核心阶段的代码、测试和验收不得依赖它们。
- 所有评测数字都是目标或实测结果，不能预填成功；旧代码一致性不等于符合 3GPP。

## Review Focus

1. 上一轮蒙特卡洛成功、下一轮无有效点时不能沿用功率；搜索终止指标不能冒充最后有效点指标。任务 2 固定此行为。
2. worker 超时后迟到写回、同一 job_id 在 Redis 队列中出现两次、两个 worker 重复领取，都不能覆盖终态；Redis 被清空后，仍处于 queued 的任务必须被补投；任务哈希必须包含 seed／代码／阈值版本。任务 3—4 固定此行为。
3. dense 已过滤而 BM25／reranker／缓存串入其他版本，必须阻止；更换模型 revision 或维度不能读旧索引。任务 5—6 固定此行为。
4. 会话续问、进程重启、并发请求不能重置或绕过工具预算；检索文本指令不能获得执行权。任务 8 固定此行为。
5. 相同问题的改写混入开发／测试集、无答案混入 Recall 分母、warm cache 冒充仿真性能，必须识别。任务 9 固定此行为。

---

## 执行边界、工时与环境

本轮只产出计划。仓库已有 Git（见「本版修订」）；开始实施时先 `git status` 确认工作区干净，再从任务 0 开始。

按一个端到端项目执行，仿真、任务、检索是相互依赖的模块，不另建三个独立产品。任务依赖顺序：0 → 1 → 2 → 3 → 4；5 → 6 → 7；4 + 7 → 8 → 9 → 10；可选 A 依赖 8，可选 B 依赖 4。阶段按下表串行推进，避免同时学习多套框架。

## 阶段总览

| 阶段 | 周次（日期） | 项目工时 | 包含任务 | 这一阶段做什么 | 阶段结束时你手上有什么 |
|---|---|---:|---|---|---|
| **一、仿真核心可信化** | 1—2（10/26—11/08） | 26h | 0、1、2 | 先把现有代码按功能搬进 `src/rf_copilot/` 并修好导入；再固定参数档和输入／输出契约，捕获旧代码基线；最后把仿真改成无全局状态、可复现、有搜索上限的函数，指标带测量值和裕量 | 结构清晰、能运行的代码库；`simulate(config)` 一次调用就能得到可解释的结果；12 例基线；`--smoke` 命令 |
| **二、后端服务化** | 3—5（11/09—11/29） | 33h | 3、4 | FastAPI 提交／查询实验；PostgreSQL 保存任务并保证幂等；Redis 队列 + 独立 worker 执行仿真；结果缓存、硬超时、Redis 丢数据后补投 | `docker compose up` 后能提交实验、拿 job_id、轮询结果；故障测试通过 |
| **三、通信知识库 RAG** | 6—9（11/30—12/27） | 43h | 5、6、7 | 整理 30—60 个可追溯语料块；Qdrant 向量 + BM25 混合检索、版本过滤、重排、拒答；接入 LLM API，生成带引用的回答，记录 token 费用 | 问一个规范问题，得到带条款／版本引用的回答，证据不足时拒答 |
| **四、Agent 闭环** | 10（12/28—01/03） | 12h | 8 | 用 LangGraph 编排 4 个工具：查规范、提交仿真、查结果、对比实验；会话预算持久化，防提示注入 | 一句话完成「查证据 → 提交仿真 → 等待 → 查询 → 对比」，有完整调用轨迹 |
| **五、评测与性能** | 11—12（01/04—01/17） | 22h | 9 | 冻结 60 道题和 20 个 Agent 场景；做 dense／BM25／混合／重排四组消融；压测与故障演练 | `docs/project/evaluation.md`：带分子／分母的真实指标和 badcase |
| **六、交付与面试** | 13—14（01/18—01/31） | 22h | 10 | 完成 Compose 部署、Streamlit 演示、README；写架构说明、面试问答、两版简历；录 5 分钟演示 | 能从干净环境一键启动的项目、演示视频、简历 |
| 核心合计 | 14 周 | **158h** | 0—10 | | |
| *可选 A：MCP Server* | 阶段四之后 | 8h | A | 把 4 个工具发布为 MCP Server，可被 Claude Desktop／MCP Inspector 调用 | 简历可写「提供 MCP 接口」，并能现场演示 |
| *可选 B：Celery 调度后端* | 阶段四之后（代码只依赖任务 4） | 6h | B | 新增 `CeleryDispatcher`，与 Redis 队列跑同一套分发器契约测试 | 能讲「为什么先不用 Celery、换上它改了什么」 |

**可选阶段的启动条件：** 阶段四验收通过，且累计进度落后不超过 1 周。先做 A，再做 B。工时从每周 2h 的机动时间里出（14 周共 28h，任务 0 先用掉 4h，剩 24h；A+B 共 14h）。机动时间不够时直接跳过，简历上不写。设计 §13 的扩展（GPU／C++／代理模型）排在 A、B 之后。

**进度提醒：** 第 1 周从 10/26 开始，修订本计划时（10/29）阶段一尚未动工。第 1 周落下的工时先用机动时间补；补不完时，可选阶段相应减少。

**各阶段同步学习**（来自设计第 9 节）：
- 阶段一：Python 工程、pytest、单位与 EVM／ACLR
- 阶段二：HTTP、事务、SQL 索引、进程／线程、Redis 数据结构／TTL、至少一次投递
- 阶段三：embedding、余弦相似度、召回指标、RRF、reranker、开发／测试集隔离
- 阶段四：Tool Calling、状态机、Transformer 基础
- 阶段五：p50／p95、缓存命中、系统设计取舍
- 阶段六：Linux 排障、项目讲解

每周其余 9h：C++ 刷题 3h、计算机基础 2h、AI 原理／官方文档 2h、复盘与机动 2h。超出任务预算时记录原因，先用机动时间；仍不足就按设计降级，评测不能压缩为零。

工程细化选择：Python 3.11，Pydantic 2，SQLAlchemy 2；具体兼容补丁版本在首次安装后锁定，之后更新依赖必须重跑相关测试。开发／测试依赖分组，GPU 模型依赖单独分组，不要求所有测试下载模型。

核心 worker 是普通 Python 进程（`python -m rf_copilot.jobs.worker`，concurrency=1）。每个仿真在 `multiprocessing` 的 spawn 子进程里执行，超时由父进程 terminate 子进程，Windows 和 Linux 都能运行。真实集成测试和演示统一用 Compose 的 Linux 容器。硬超时必须用真实子进程被终止来验证，不能在事件循环里 sleep 模拟。可选阶段 B 的 Celery worker 只在 Linux 容器运行，依据：[Celery Windows 支持说明](https://docs.celeryq.dev/en/stable/faq.html#windows)。

第三方 SDK 的具体调用以锁定版本的官方文档为准；下文签名是本项目内部契约。默认测试不用真实 LLM，live 测试显式选择且记录费用。API 月预算初始 100 元，可通过环境变量调整；尚未配置供应商单价时禁止声称已做准确费用统计。

## 文件结构与共用约定

所有路径相对 `E:/PyProject/MPR_python`。每个包创建 `__init__.py`。采用 setuptools 的 `src` 包布局，**根目录不再放任何 `.py`**；所有导入使用绝对路径（`from rf_copilot.sim.matlab_compat import ...`），不靠 `sys.path` 拼接或 IDE 的 Sources Root。在空目录用安装包做导入测试，不能依赖偶然的 cwd。

**组织原则：一个大类功能 = 一个文件夹。**
- 每个功能包内部放齐自己的数据模型、业务逻辑和命令行入口；命令统一写成 `python -m rf_copilot.<包>.<模块>`，**不设顶层 `scripts/`**。
- 数据库表的 ORM 模型跟着所属功能走（任务表在 `jobs/`，用量表在 `llm/`，会话表在 `agent/`）；共用的数据库连接放在 `db/`。
- `tests/` 的子目录与 `src/rf_copilot/` 一一对应，测试数据放在对应测试目录的 `fixtures/` 下。
- 运行时数据统一放在 `data/`，文档按用途分为 `docs/project/`（项目说明）和 `docs/career/`（求职材料）。

```text
MPR_python/
├── src/rf_copilot/
│   ├── config/        settings.py                         环境配置，不含真实密钥（3 起逐步增加）
│   ├── db/            base.py, session.py                 SQLAlchemy Base 与 session_factory（3）
│   ├── sim/           schemas, profiles, engine, cp, dft, metrics, baseline   新仿真核心与旧代码基线（1—2）
│   │   ├── matlab_compat.py                               MATLAB 内置函数的 Python 版（0）
│   │   ├── pa/        dispatch + 各功放模型                功放模型（0）
│   │   ├── checks/    aclr, evm_cp, evm_dft, ibe, sem_*, region_avg_*   指标检测（0；2 增加 measure 接口）
│   │   ├── legacy/    cp_ofdm_v6, dft_ofdm_v2             原两个主程序，任务 2 后变为兼容 CLI（0、2）
│   │   └── diagnostics/ mirror_check                      镜像对称性自检（0）
│   ├── plots/         mpr_map, pa_huawei, pa_memory, pa_memoryless, pa_mp_k7   绘图（0）
│   ├── jobs/          models, repository, service, worker, cache, reconcile   实验任务：持久化、执行、缓存、补偿（3—4）
│   │   └── dispatch/  base, redis_queue, celery_dispatcher                    任务分发：协议、Redis 队列、可选 Celery（4、B）
│   ├── api/           app.py                              FastAPI 工厂与错误映射（3、8）
│   │   └── routes/    experiments, questions, health      按资源拆分路由（3、8）
│   ├── rag/           schemas, ingest, retrieve, answer   知识库：入库、检索、带引用回答（5—7）
│   ├── llm/           client, usage                       LLM 供应商适配、token／费用账本（7）
│   ├── agent/         schemas, models, tools, workflow    Agent：会话表、工具白名单、LangGraph 图（8）
│   ├── evaluation/    dataset, metrics, cli, benchmark    评测与压测（9）
│   └── mcp_server/    __init__, __main__, server          可选 A：MCP Server（包名不叫 mcp，避免遮蔽官方 SDK）
├── tests/             conftest.py + sim/ jobs/(dispatch/) api/ rag/ llm/ agent/ evaluation/ mcp_server/ delivery/
├── data/
│   ├── knowledge/     manifest.jsonl, chunks.jsonl, retrieval_config.json   语料与检索配置（5—6）
│   └── eval/          questions.jsonl, scenarios.jsonl, annotations.jsonl  冻结评测集（9）
├── migrations/ + alembic.ini                              数据库迁移（3、7、8）
├── demo/              app.py                              Streamlit 演示，只调用 HTTP API（10）
├── docs/
│   ├── project/       numerical-audit, data-card, evaluation, architecture
│   ├── career/        interview, job-tracker.csv, resume-ai, resume-backend, demo-script
│   └── superpowers/   specs/, plans/
├── outputs/           旧主程序和绘图脚本的运行结果（.npz／.mat／.csv／.png），已 gitignore
└── Dockerfile, compose.yaml, pyproject.toml, uv.lock, .gitignore, .env.example, README.md
```

模块依赖只能单向：`sim.matlab_compat` ← `sim.pa`、`sim.checks` ← `sim.legacy`、`sim.diagnostics`、`plots`；`config`、`db` ← `sim` ← `jobs` ← `api`；`llm` ← `rag` ← `agent` ← `api`、`mcp_server`；`evaluation` 可以依赖任何包，但其他包不能依赖它。

测试标记：`unit` 不联网；`integration` 使用独立测试数据库／Qdrant collection；`live` 才调用付费 API／真实模型；`slow` 包括硬超时测试。不得清空开发数据库。pytest 默认 `-m 'not live and not slow'`，长时限验证单列。

各任务按“测试失败 → 最小实现 → 测试通过 → 提交”执行，命令中的预期 PASS 是未来验收条件，本计划没有运行这些尚不存在的测试。提交仅暂存本任务明确文件，不能 `git add .` 把密钥、模型、原始受限资料纳入历史。

---

# 阶段一：仿真核心可信化（第 1—2 周，26h）

**目标：** 先让代码结构清楚、能运行，再让「算出来的数」可信、可复现。后面所有服务、RAG 和 Agent 都建立在这里的结果之上。
**做什么：** 任务 0 把现有代码按功能搬进 `src/rf_copilot/`，修好导入，用对照测试证明数值不变；任务 1 固定输入／输出契约，记录旧代码基线；任务 2 把仿真提取成纯函数，修掉功率沿用、搜索无上限、IBE 冒充通过等口径问题。
**阶段验收：** 根目录没有 `.py` 文件；`python -m pytest tests/sim -v` 全部 PASS（包括搬迁对照测试）；`python -m rf_copilot.sim.legacy.cp_ofdm_v6 --smoke --seed 42` 输出带功率口径、指标测量值、裕量和 `not_evaluated` 标记的结果；`docs/project/numerical-audit.md` 记录每个已知问题的处理方式。

## Task 0：按功能重组现有代码（4h）

**目标：** 只搬家、不装修。把根目录脚本、`PAmodel/`、`plotfigure/` 搬进对应的功能文件夹，修复当前断掉的导入。**不改任何数值逻辑、函数名或函数签名**；用搬迁前后逐位一致的指纹对照来证明。

**搬迁对照表**（用 `git mv`，保留文件历史；模块文件名改为小写，函数名保持原样，如 `check_ACLR`、`pa_model_mp_K7` 不变）：

| 现在的位置 | 搬到 `src/rf_copilot/` 下 |
|---|---|
| `matlab_builtins.py` | `sim/matlab_compat.py` |
| `apply_pa_model.py` | `sim/pa/dispatch.py`（`sim/pa/__init__.py` 导出 `apply_pa_model`） |
| `PAmodel/HZW_HB_am.py`、`PAmodel/HZW_HB_pm.py` | `sim/pa/hzw_hb_am.py`、`sim/pa/hzw_hb_pm.py` |
| `PAmodel/pa_GaAs_2GHz.py` | `sim/pa/gaas_2ghz.py` |
| `PAmodel/pa_model_memory_38803.py`、`PAmodel/pa_model_memoryless_38803.py` | `sim/pa/memory_38803.py`、`sim/pa/memoryless_38803.py` |
| `PAmodel/pa_model_memoryless.py`、`PAmodel/pa_model_mp.py`、`PAmodel/pa_model_mp_K7.py` | `sim/pa/memoryless.py`、`sim/pa/mp.py`、`sim/pa/mp_k7.py` |
| `check_ACLR.py`、`check_IBE.py` | `sim/checks/aclr.py`、`sim/checks/ibe.py` |
| `check_EVM_CP.py`、`check_EVM_DFT.py` | `sim/checks/evm_cp.py`、`sim/checks/evm_dft.py` |
| `check_SEM_FR1.py`、`check_SEM_FR2.py`、`check_SEM_FR2_EESS.py` | `sim/checks/sem_fr1.py`、`sim/checks/sem_fr2.py`、`sim/checks/sem_fr2_eess.py` |
| `check_region_avg_left.py`、`check_region_avg_right.py` | `sim/checks/region_avg_left.py`、`sim/checks/region_avg_right.py` |
| `CP_ofdm_mainV6.py`、`DFT_ofdm_mainV2.py` | `sim/legacy/cp_ofdm_v6.py`、`sim/legacy/dft_ofdm_v2.py` |
| `mirror_check.py` | `sim/diagnostics/mirror_check.py` |
| `plotfigure/figure_plot.py` | `plots/mpr_map.py` |
| `plotfigure/plotPA_HUAWEI.py`、`plotfigure/plotPA_memory.py` | `plots/pa_huawei.py`、`plots/pa_memory.py` |
| `plotfigure/plotPA_memoryless.py`、`plotfigure/plotPA_mp_K7.py` | `plots/pa_memoryless.py`、`plots/pa_mp_k7.py` |

**Files:** 新增 `.gitignore`、最小 `pyproject.toml`、上表各目录的 `__init__.py`、`tests/sim/fixtures/reorg_fingerprint.py`、`tests/sim/fixtures/reorg_before.json`、`tests/sim/test_reorg_equivalence.py`；按上表移动并修改所有内部 import；删除 `PAmodel/`、`plotfigure/`（`git mv` 后其中只剩未跟踪的 `__pycache__`，`rmdir` 会失败，需整个删除）。

**Interfaces:**

- Produces（任务 1、2 依赖）：`rf_copilot.sim.pa.apply_pa_model(signal_in, k, PA_MODEL_TYPE)`；`rf_copilot.sim.checks.<模块>.<原函数名>`；`rf_copilot.sim.legacy.cp_ofdm_v6.simulate_config(lcrb, rbstart, rbend, rng)` 与 `rf_copilot.sim.legacy.dft_ofdm_v2.simulate_config(lcrb, rbstart, rbend, rng)`，模块全局参数（`MONTE_CARLO`、`PA_MODEL_TYPE` 等）名称不变；`rf_copilot.sim.matlab_compat`。
- 运行方式统一为 `python -m rf_copilot.<包>.<模块>`；旧主程序和绘图脚本的输出文件改写到 `outputs/`（不存在时自动创建），文件名不变。
- `reorg_fingerprint.digest(a: np.ndarray) -> str`：dtype + shape + 原始字节的 SHA-256，摘要相同即逐位相同；fixture 只存摘要（约 4KB），不存数组（`plot_pa_memory` 有 34 万点，存数组约 22MB）。
- `reorg_fingerprint.compute(layout: Literal['old','new'], root: Path | None = None) -> dict[str, np.ndarray]`：`old` 把 `root`、`root/PAmodel`、`root/plotfigure` 依次插入 `sys.path` 后按旧的平铺模块名导入（对当前 `98de8b7` 的布局有效，不需要回退旧提交），`new` 从 `rf_copilot` 导入，两种布局计算同一组量：
  - `cp_a`、`cp_b`：CP 主模块设 `MONTE_CARLO=1` 后，`simulate_config(1, 0, 0, RandomState(42))` 与 `simulate_config(12, 120, 131, RandomState(42))` 的返回元组；
  - `dft_a`：DFT 主模块设 `MONTE_CARLO=1` 后，`simulate_config(12, 0, 11, RandomState(42))` 的返回元组；
  - `pa_<类型>`：对 `RandomState(0)` 生成、按最大幅度归一化的 1024×1 复信号，以 `k=-10` 调用 `apply_pa_model`，类型取 `HZW_HB`、`MP1`、`MP`、`MEMORYLESS`、`MEMORY` 中实际有实现的（抛 `NotImplementedError` 的跳过并记录）；
  - `plot_<名称>`：4 个功放绘图模块 `compute()` 的返回值（元组逐项展开为 `plot_<名称>_<序号>`）；`mpr_map`：`build_map(np.arange(55.0), 10)` 的返回值。

- [ ] **0.1 仓库卫生。** 新增 `.gitignore`：`__pycache__/`、`*.pyc`、`.idea/`、`.venv/`、`.env`、`outputs/`、`*.npz`、`*.mat`。若 `__pycache__/`、`.idea/` 已被跟踪，执行 `git rm -r --cached __pycache__ .idea`（文件仍留在本地）。提交 `chore: ignore caches, IDE files and run outputs`。
- [ ] **0.2 写指纹脚本。** 在任何 `git mv` 之前，写好 `tests/sim/fixtures/reorg_fingerprint.py`，入口带 `--layout`、`--root`、`--out` 参数。
- [ ] **0.3 生成搬迁前指纹。** 仍在搬迁前，运行 `python tests/sim/fixtures/reorg_fingerprint.py --layout old --root . --out tests/sim/fixtures/reorg_before.json`。预期打印「共 40 项」（演练值，以实际输出为准），并打印跳过的功放类型。把当前提交号和跳过列表记入 `docs/project/numerical-audit.md`。提交指纹脚本和 JSON：`test: capture pre-reorganization fingerprint`。
- [ ] **0.4 写对照测试。**

```python
def test_reorg_is_bit_identical():
    before = json.loads((FIXTURES / 'reorg_before.json').read_text(encoding='utf-8'))
    after = {k: fp.digest(v) for k, v in fp.compute('new').items()}
    assert set(after) == set(before)
    assert sorted(k for k in before if after[k] != before[k]) == []
```

另加 `test_no_python_files_at_repo_root`：仓库根目录 `glob('*.py')` 为空。
- [ ] **0.5 执行红灯。** `python -m pytest tests/sim/test_reorg_equivalence.py -v`；预期 FAIL，原因是 `rf_copilot` 无法导入、根目录仍有 `.py`。
- [ ] **0.6 搬迁并修导入。** 新建最小 `pyproject.toml`（setuptools、`src` 布局、包 `rf_copilot`、依赖 numpy 与 scipy、可选组 `plots = [matplotlib]`），`pip install -e .`。按对照表 `git mv`；把所有平铺导入改成绝对导入，例如 `from matlab_builtins import polyval` → `from rf_copilot.sim.matlab_compat import polyval`。`sim/pa/__init__.py` 只写 `from .dispatch import apply_pa_model`。各脚本的 `if __name__ == '__main__':` 保持原样，只把输出路径改到 `outputs/`。
- [ ] **0.7 验证并提交。** `python -m pytest tests/sim/test_reorg_equivalence.py -v` PASS；`python -c "import rf_copilot.sim.legacy.cp_ofdm_v6, rf_copilot.sim.legacy.dft_ofdm_v2, rf_copilot.sim.diagnostics.mirror_check, rf_copilot.plots.mpr_map"` 无报错，且不会触发全量扫描。不要直接运行旧主程序的 main（默认全量扫描约 21 小时）。在 PyCharm 中把 `src` 标为 Sources Root（只是方便跳转，运行不依赖它）。提交 `refactor: organize legacy simulation code into rf_copilot packages`。

## Task 1：建立固定配置、依赖与小样本基线（10h）

**Files:** 新增 `uv.lock`、`src/rf_copilot/sim/schemas.py`、`src/rf_copilot/sim/profiles.py`、`src/rf_copilot/sim/baseline.py`、`tests/conftest.py`、`tests/sim/test_contract.py`、`tests/sim/fixtures/sim_cases.json`；修改任务 0 建立的 `pyproject.toml`、`.gitignore`（补充模型目录与原始受限资料）、`docs/project/numerical-audit.md`。

**Interfaces:**

- `profiles.get_profile(profile_id: str) -> RadioProfile`：`fr1_100m_30k_legacy_v1` 固定 CBW=100 MHz、SCS=30 kHz、NRB=273、Fs=614400 kHz、IFFT=20480、CP=15360；名称明确继承实现，不能声称标准 CP。
- `schemas.SimConfig`：`waveform: Literal['cp','dft']`、`profile_id`、`rb_start: int`、`rb_count: int`、`mod_order: Literal[4,16,64,256]`、`pa_model: Literal['HZW_HB']`、`seed: int`、`trials: int`、`threshold_profile_id`、`engine_version`；整数严格验证，RB 越界拒绝，seed 范围 0..2**32-1，trials 1..3。
- `schemas.ExperimentRequest(configs: list[SimConfig])`：1..2 个配置；HTTP 层仅接受 cp，dft 供兼容测试。
- 阈值档 `legacy_cp_v1`／`legacy_dft_v1`：ACLR=31 dB；EVM 按旧表；DFT QPSK=3.5%，其他 QAM=12.5/8/3.5%。标注实验条件，不附虚构标准条款。
- `schemas.Metric(value: float|None, unit: str, limit: float|None, margin: float|None, status: str)`；检查状态用设计中的五值枚举。`TrialResult` 保存 trial_index、seed、status、power、drive、metrics、reason；`SimResult` 保存 config、status、trials、output_power_db_ref、mpr_db、reason、elapsed_s。非有限数映射 null 并记录原因，不默默变成成功。
- `tests/conftest.py` 的 `make_config(**overrides) -> SimConfig` 默认 cp、RB=(0,1)、256QAM、seed=42、trials=1、上述固定档、engine_version=`engine-v1`；只用于测试。

- [ ] **1.1 记录版本基线。** 确认任务 0 的提交之后工作区干净（`git status`）；把该提交号作为「旧实现基线」记入 numerical-audit。`.gitignore` 补充模型目录和原始受限资料。不改原始数值实现。
- [ ] **1.2 写契约测试。** 在 `test_contract.py` 中包含下列断言，并参数化越界 rb_start=273、rb_count=0、trials=4、未知模型和多余字段：

```python
def test_profile_and_budget(make_config):
    cfg = make_config(rb_start=272, rb_count=1)
    assert get_profile(cfg.profile_id).nrb == 273
    assert cfg.trials == 1
    with pytest.raises(ValidationError):
        ExperimentRequest(configs=[cfg, cfg, cfg])
```

- [ ] **1.3 执行红灯。** `python -m pytest tests/sim/test_contract.py -v`；预期缺模块或契约断言失败，记录实际原因。
- [ ] **1.4 实现类型与打包。** schemas/profiles 按上述契约实现；在任务 0 的 pyproject 上补充 Pydantic 等依赖、开发依赖组与 pytest 标记，生成锁文件。先检查 Python／uv 是否可用，缺少时再安装。添加编辑器外导入检查。
- [ ] **1.5 捕获旧基线。** `sim/baseline.py` 在独立子进程按案例设置旧模块参数后调用 `rf_copilot.sim.legacy.cp_ofdm_v6.simulate_config` 或 `rf_copilot.sim.legacy.dft_ofdm_v2.simulate_config`，每例 120 秒外部 watchdog，不执行默认 main。12 例固定为：CP 的 (0,1)、(272,1)、(120,12)、(0,24)、(249,24)、(100,50)；非法越界；DFT (0,7) 跳过；一次成功后无有效点的替身；全部检查通过导致搜索不收敛的替身；固定点 EVM 恰好阈值；CP IBE 未评估。真实案例 seed=42、trials=1。基线输出存 `tests/sim/fixtures/legacy_baseline.json`，超时／异常原样记录。
- [ ] **1.6 验证并提交。** 重跑契约测试应 PASS；`python -m rf_copilot.sim.baseline --cases tests/sim/fixtures/sim_cases.json --timeout 120` 应生成 12 条带状态记录，不要求旧代码全部正确。`git add` 仅本任务文件；`git commit -m "test: establish RF simulation contracts and baseline"`。

## Task 2：提取可解释、有界的仿真核心（12h）

**Files:** 新增 `sim/engine.py`、`sim/cp.py`、`sim/dft.py`、`sim/metrics.py`（均在 `src/rf_copilot/` 下）、`tests/sim/test_engine.py`、`tests/sim/test_metrics.py`；修改 `sim/legacy/cp_ofdm_v6.py`、`sim/legacy/dft_ofdm_v2.py` 的 `simulate_config` 入口与 CLI，以及 `sim/checks/evm_cp.py`、`sim/checks/evm_dft.py`、`sim/checks/aclr.py`；更新 numerical-audit。

**Interfaces:**

- `engine.simulate(config: SimConfig) -> SimResult`；`cp.run(config: SimConfig) -> SimResult`；`dft.run(config: SimConfig) -> SimResult`。不修改模块全局配置，不共享 RNG。
- `metrics.aclr_from_powers(main: float, left: float, right: float, limit: float) -> dict[str, Metric]`，返回 aclr_left/aclr_right；非正功率返回 error，不能除零。
- `metrics.evm_from_symbols(reference: np.ndarray, received: np.ndarray, limit: float) -> Metric`，复用现有 comm_evm；单位 %，margin=limit-value，等于阈值沿用旧 `<` 判失败。ACLR margin=value-limit，等于阈值通过。
- `metrics.mpr(power_db_ref: float, reference_db_ref: float|None) -> float|None`。初版 profile 不提供参考，默认 null。
- `engine.search(evaluate: Callable[[float], TrialResult], start_db: float, max_db: float=10.0, max_evaluations: int=200) -> TrialResult`：保留 (5,1,0.2) 搜索步长；返回同一有效点的功率与指标，无有效点返回 error，任何搜索超限不得称找到最大功率。

- [ ] **2.1 写数值与状态测试。** 替身 evaluate 固定在 -10 dB 返回成功、在 -9 dB 返回失败；检查最终 power/metrics 来自同一成功点。两次试验分别成功／无有效点，第二次必须 error、power=null，总结果 error 且不对成功子集冒充全试验平均。补充以下独立解析断言：

```python
def test_metrics_have_physical_meaning():
    metric = aclr_from_powers(1.0, 0.001, 0.001, 31.0)['aclr_left']
    assert metric.value == pytest.approx(30.0)
    assert metric.margin == pytest.approx(-1.0)
    assert metric.status == 'fail'
    assert mpr(-8.0, None) is None
    assert mpr(-8.0, -5.0) == pytest.approx(3.0)
```

- [ ] **2.2 执行红灯。** `python -m pytest tests/sim/test_engine.py tests/sim/test_metrics.py -v`；预期尚无入口或断言失败。
- [ ] **2.3 提取测量。** 在旧 check 文件中新增同参数的 measure 接口返回数值，保留 check 的 0/1 包装；不增加噪声、不改变均衡算法。新 metrics 负责状态、margin 与非有限值。保留 SEM 布尔值，CP IBE 固定 not_evaluated。
- [ ] **2.4 提取计算。** 把两种波形放入 cp/dft，engine 分发；每次试验重新初始化状态，seed+i 构造独立 RNG，记录派生 seed。保留已有 FFT/Welch 路径及 DFT 跳过规则。计算 trial 全成功时才汇总线性功率平均后转 dB。
- [ ] **2.5 接入有界搜索与兼容 CLI。** CP 起点 -15、DFT -25，最大驱动 10、最多 200 次 evaluate；DFT 随机重采样上限 100 次。旧 CLI 保留全量扫描能力但增加 `--smoke`，打印真实功率名称和未评估指标；兼容输出旧字段时附 deprecated 说明。
- [ ] **2.6 验证并提交。** `python -m pytest tests/sim -v`；`python -m rf_copilot.sim.legacy.cp_ofdm_v6 --smoke --seed 42`；`python -m rf_copilot.sim.legacy.dft_ofdm_v2 --smoke --seed 42`。任务 0 的对照测试在本任务后会失败是预期的（数值口径被有意修正）：把它标记为 `legacy_reorg` 并在本任务中改为只比较 `pa_*`、`plot_*`、`mpr_map` 这些未被修改的键，`cp_*`、`dft_*` 的对照交给任务 1 的基线。正常基线容差 atol=1e-6/rtol=1e-5；seed+i 导致多试验旧随机流不同，逐试验重放对照而非强求总数相同。修复场景以独立断言为准。暂存本任务文件，提交 `refactor: expose bounded reproducible RF simulations`。

---

# 阶段二：后端服务化（第 3—5 周，33h）

**目标：** 把仿真包装成可靠的异步服务。这一阶段是简历上「后端」部分的主要证据。
**做什么：** 任务 3 实现 FastAPI 接口和 PostgreSQL 持久化（幂等、事务、终态不可覆写）；任务 4 实现 Redis 队列、独立 worker、硬超时、结果缓存和补偿扫描。
**阶段验收：** `docker compose up -d postgres redis worker scheduler` 后，`python -m pytest tests/jobs tests/api -v` 全部 PASS；手动 `curl` 提交一个小样本实验，返回 202 和 job_id，轮询后得到 succeeded 结果；执行 `redis-cli FLUSHALL` 后，未完成的任务仍能被补投并完成。

## Task 3：实验持久化与 HTTP 接口（22h）

**Files:** 新增 `config/settings.py`、`db/{base,session}.py`、`jobs/{models,repository,service}.py`、`jobs/dispatch/base.py`、`api/app.py`、`api/routes/{experiments,health}.py`、`migrations/env.py`（导入各功能包的 models 以注册表结构）、`migrations/versions/001_jobs.py`、`alembic.ini`、`.env.example`、初版 `compose.yaml`、`tests/jobs/test_repository.py`、`tests/api/test_experiments.py`（模块目录沿文件地图）；更新依赖锁。

**Interfaces:**

- `models.JobView`：id UUID、status、request、result `list[SimResult]|None`、dispatch_pending bool、error_code、created_at、started_at、finished_at、request_hash、attempt_token UUID|None。
- `repository.JobRepository(session_factory)`：`get_or_create(request: ExperimentRequest) -> tuple[JobView,bool]`、`get(job_id: UUID) -> JobView|None`、`claim(job_id: UUID, token: UUID, now: datetime) -> bool`、`finish(job_id: UUID, token: UUID, status: str, result: list[SimResult]|None, error: str|None) -> bool`。
- `service.request_key(request: ExperimentRequest) -> str`：规范化 JSON + SHA256；包含配置顺序、seed、所有 profile/engine 版本，不包含时间戳。`ExperimentService(repo, dispatcher: Dispatcher)` 的 `submit(request) -> JobView`、`get(job_id) -> JobView|None`。
- `jobs/dispatch/base.Dispatcher`：Protocol，只有 `enqueue(job_id: UUID) -> None`。本任务用测试替身实现，任务 4 和可选 B 提供真实实现。
- `db.session.make_session_factory(url: str) -> sessionmaker`；`db.base.Base` 是所有功能包 ORM 模型的共同基类。
- `app.create_app(service: ExperimentService) -> FastAPI`；POST `/v1/experiments` → 202；GET `/v1/experiments/{id}` → 200 或 404；非法配置／不支持的 dft → 422。`/health` 只检查进程，`/ready` 检查必要依赖。

- [ ] **3.1 写 API／事务测试。** 真 PostgreSQL 集成 fixture 用独立测试数据库，测试完成回滚／清理自己的表数据；以下并发测试不能用 SQLite 代替：

```python
def test_idempotency_and_version(repo, make_request):
    request = make_request(seed=42)
    first, _ = repo.get_or_create(request)
    same, _ = repo.get_or_create(request)
    seeded, _ = repo.get_or_create(make_request(seed=43))
    versioned, _ = repo.get_or_create(make_request(engine_version='engine-v2'))
    assert first.id == same.id
    assert seeded.id != first.id
    assert versioned.id != first.id
```

`make_request(**overrides)` 在 conftest 中包装任务 1 的单配置。并发 8 次同请求要求数据库只有 1 行；阈值版本变化也生成新 key。HTTP 提交非法 RB 断言 422、enqueue 调用数为 0；未知 ID 404。

- [ ] **3.2 执行红灯。** `python -m pytest tests/jobs/test_repository.py tests/api/test_experiments.py -v`；先确认测试 PostgreSQL 可连，缺依赖是环境问题，不作为正确红灯。
- [ ] **3.3 建表与事务。** request_hash 唯一、status/created_at 索引；request/results 用 JSONB，时间 UTC；get_or_create 处理唯一约束竞争并回查。claim 用 queued 条件 UPDATE；finish 必须匹配 running 和 token，终态不可覆写。
- [ ] **3.4 实现服务与 HTTP。** 数据库 commit 后才 enqueue；失败保存 dispatch_pending=true，仍返回 queued；过期代码版本必须在真实服务入口拒绝，版本哈希测试可用 repository 层注入第二版支持表。加入 request_id 和结构化错误。
- [ ] **3.5 验证并提交。** `docker compose up -d postgres`；`alembic upgrade head`；重跑上述测试 PASS。依赖配置排除秘密，提交 `feat: persist and expose idempotent simulation jobs`。

## Task 4：Redis 队列、独立 worker、缓存与终态恢复（11h）

**Files:** 新增 `jobs/dispatch/redis_queue.py`、`jobs/{worker,cache,reconcile}.py`、初版 `Dockerfile`、`tests/jobs/dispatch/test_redis_queue.py`、`tests/jobs/test_worker.py`、`tests/jobs/test_cache.py`、`tests/jobs/test_reconcile.py`、`tests/jobs/dispatch/contract.py`；修改 service、repository、settings、compose 与依赖锁。

**Interfaces:**

- Consumes：任务 3 的 `JobRepository.get/claim/finish`、`ExperimentService(repo, dispatcher)` 与 `jobs/dispatch/base.Dispatcher` 协议；任务 2 的 `engine.simulate(config) -> SimResult`。
- `dispatch.redis_queue.RedisJobQueue(redis_client, prefix: str = 'rf:queue')`：
  - `enqueue(job_id: UUID) -> None`：`LPUSH {prefix}:jobs`，满足 dispatcher 协议；
  - `reserve(timeout_s: int) -> UUID | None`：`BLMOVE {prefix}:jobs {prefix}:processing RIGHT LEFT`；
  - `ack(job_id: UUID) -> None`：从 `{prefix}:processing` 中 `LREM`；
  - `contains(job_id: UUID) -> bool`：用 `LPOS` 检查两个列表；
  - `recover_processing() -> int`：worker 启动时把 processing 中的遗留项移回 jobs，返回移动数量。
- `worker.run_with_timeout(fn: Callable[[Any], Any], arg: Any, timeout_s: float) -> tuple[Literal['ok','timeout','error'], Any]`：在 spawn 子进程执行，超时 terminate 后 join，返回值通过 Queue 传回。
- `worker.run_job(job_id: UUID, repo: JobRepository, cache: ResultCache, *, time_limit_s: float = 120.0) -> Literal['succeeded','failed','timed_out','not_claimed']`：claim 失败（重复出队、已终态）返回 `not_claimed` 且不写任何东西；成功后 finish + 写缓存。
- `worker.main() -> None`：`python -m rf_copilot.jobs.worker`；启动时 `recover_processing`，循环 `reserve(5) → run_job → ack`，concurrency=1。
- `cache.ResultCache(redis_client, prefix: str = 'rf:result')`：`get(key: str) -> list[SimResult]|None`、`put(key: str, result: list[SimResult]) -> None`；TTL=86400。
- `repository.queued(limit: int) -> list[JobView]`、`mark_dispatched(job_id: UUID) -> None`（置 dispatch_pending=false）、`expire_running(before: datetime) -> int`；只操作满足状态的记录。
- `reconcile.reconcile(queue: RedisJobQueue, repo: JobRepository, now: datetime) -> dict[str,int]`，返回键 `requeued`、`timed_out`：对 queued 且 `dispatch_pending=true` 或 `not queue.contains(id)` 的任务重新入队并 mark_dispatched；running 且 `started_at < now - 150s` 的任务标 timed_out（worker 自身 120s 硬超时，150s 只兜底 worker 崩溃）。`python -m rf_copilot.jobs.reconcile --interval 15`。初版终态不自动重跑。
- `config.settings.dispatcher: Literal['redis','celery'] = 'redis'`；核心只实现 `redis`。

- [ ] **4.1 写分发器契约测试。** `tests/jobs/dispatch/contract.py` 定义可参数化的契约，任务 4 用 `redis` 运行，可选 B 用 `celery` 复用。测试 Redis 使用独立前缀 `rf-test:{uuid}:queue`，结束时删除自己的 key。fixture `run_worker_once(times: int) -> list[str]` 在 `conftest.py` 中按 dispatcher 类型实现：redis 模式下执行 `times` 次 `reserve → run_job → ack` 并返回每次的状态；celery 模式下等待 `times` 次任务执行完成，再从 worker 日志的结构化记录读取状态。

```python
def test_duplicate_delivery_runs_once(dispatcher, repo, run_worker_once, make_request):
    job, _ = repo.get_or_create(make_request(seed=42))
    dispatcher.enqueue(job.id)
    dispatcher.enqueue(job.id)
    statuses = run_worker_once(times=2)
    assert sorted(statuses) == ['not_claimed', 'succeeded']
    assert repo.get(job.id).status == 'succeeded'
```

- [ ] **4.2 写队列、worker、缓存与补偿测试。**
  - `dispatch/test_redis_queue.py`：enqueue → reserve 得到同一 id，且在 processing 中；ack 后两个列表都没有；`recover_processing` 把遗留项移回 jobs 并返回 1。
  - `test_worker.py`：`run_with_timeout(time.sleep, 5, timeout_s=1)` 返回 `'timeout'`，且子进程 `is_alive()` 为 False；替身仿真抛异常时任务 failed 且保存原因；超时扫描之后迟到的 finish 返回 False。
  - `test_reconcile.py`：enqueue 抛 `ConnectionError` 时 dispatch_pending=true，接口仍返回 queued；Redis 恢复后 reconcile 返回 `requeued == 1`，worker 跑完 succeeded。enqueue 之后删除队列 key（模拟 Redis 丢数据），reconcile 返回 `requeued == 1`。running 的 `started_at` 设为 151 秒前，reconcile 返回 `timed_out == 1`。
  - `test_cache.py`：`ttl in 1..86400`；failed 不缓存；删除缓存后服务从数据库得到同样结果；Redis 不可用时 GET 回源 PostgreSQL 仍返回 200。
- [ ] **4.3 执行红灯。** `python -m pytest tests/jobs/dispatch/test_redis_queue.py tests/jobs/test_worker.py tests/jobs/test_cache.py tests/jobs/test_reconcile.py -v`；预期新模块缺失。
- [ ] **4.4 实现队列与 worker。** 按上面的接口实现。claim 后顺序处理最多 2 个配置，整项任务共用 120 秒预算；任何 SimResult error 都使任务 failed，并保留已取得的结果和原因。新建 Linux Python 3.11 镜像，安装锁定依赖和本项目，Compose 的 worker 与 scheduler 共用。
- [ ] **4.5 实现缓存和补偿。** 写缓存失败不撤回数据库成功。Compose 中 Redis 设置 `maxmemory` 与 `noeviction`；容量满导致的写入错误按入队失败处理（dispatch_pending=true）。scheduler 容器运行 reconcile。补投可能造成重复，由 claim 拒绝重复执行。
- [ ] **4.6 验证并提交。** `docker compose up -d postgres redis worker scheduler`；`python -m pytest tests/jobs -v` PASS。再单列 `python -m pytest tests/jobs/test_worker.py -m slow -v`：使用真实参数档、`time_limit_s=120` 的阻塞替身被终止，任务为 timed_out。提交 `feat: run recoverable jobs on a Redis queue with caching`。

---

# 阶段三：通信知识库 RAG（第 6—9 周，43h）

**目标：** 做一个「答得有出处、不知道就说不知道」的通信规范知识库。这一阶段是简历上「RAG／向量数据库」部分的证据。
**做什么：** 任务 5 整理并入库 30—60 个可追溯语料块；任务 6 做 Qdrant + BM25 混合检索、版本过滤、重排和拒答；任务 7 接入 LLM API，生成带引用的回答并记录费用。
**阶段验收：** `python -m pytest tests/rag tests/llm -v` PASS；真实 Qdrant 中按版本 A 过滤不会返回版本 B；3 道开发题的 live 调用保存了引用和费用；无证据问题不调用 LLM，直接拒答。

## Task 5：建立可追溯语料与向量索引（12h）

**Files:** 新增 `rag/schemas.py`、`rag/ingest.py`（含 `python -m rf_copilot.rag.ingest` 入口）、`data/knowledge/manifest.jsonl`、`data/knowledge/chunks.jsonl`、`docs/project/data-card.md`、`tests/rag/test_ingest.py`；增加 Qdrant 服务与模型可选依赖。

**Interfaces:**

- `schemas.Chunk`：id/text/document_id/version/release/clause/page/section/band/duplex/power_class/source_url/content_hash；字段未知可 null，version 必须明确或 `project-note-v1`；追加 `kind: Literal['standard','project_note','experiment']`，不能混淆标准与自定义阈值。
- `schemas.IndexVersion`：corpus_hash、embedding_model、embedding_revision、dimension、reranker_revision、tokenizer_version；生成索引命名后缀，不能用浮动 latest。
- `ingest.load_chunks(path: Path) -> list[Chunk]`；`ingest.build_index(chunks: list[Chunk], version: IndexVersion, embedder: Embedder, store: VectorStore) -> int`。
- 同时在 schemas 定义 `RetrievalFilter(document_id: str|None, version: str|None, band: str|None, power_class: str|None)` 与 `Hit(chunk: Chunk, score: float)`；任务 6 复用，避免类型依赖倒置。两个 Protocol 也定义在 schemas：`Embedder.encode(texts: list[str]) -> np.ndarray`；`VectorStore.upsert(chunks: list[Chunk], vectors: np.ndarray, version: IndexVersion) -> None`、`search(query_vector: np.ndarray, filters: RetrievalFilter, limit: int) -> list[Hit]`。

- [ ] **5.1 写入库测试。** 文档 fixture 是 4 条人工合成文本，版本 A/B 各两条，不伪装真实条款；断言重入无重复、修改内容 hash 改变、向量 dimension 不匹配抛 ValueError、缺 source 的 standard 块拒绝入库。记录字段完整性而非测试真实标准内容。
- [ ] **5.2 执行红灯。** `python -m pytest tests/rag/test_ingest.py -v`；预期 ingest 缺失。
- [ ] **5.3 准备语料。** 人工校对 30—60 块，表格保留标题、单位和脚注；标准原文可用时才标 standard。若官方资源仍不可取，先以项目说明／实验阈值完成链路，回答明确“无规范证据”，不能编造标准块或题目答案。data-card 记录来源、许可、获取日期、文件 hash 与核对人。
- [ ] **5.4 实现索引。** BGE-M3 初选，revision 和维度由实际模型卡／输出核对并写 manifest；Qdrant 元数据使用完整字段；本地 BM25 原始文本索引与 Qdrant 使用同一 corpus_hash。中文术语使用可固定版本的分词器，保护 ACLR、EVM、38.101-1 等 token；分词器版本进入索引身份。
- [ ] **5.5 验证并提交。** `python -m rf_copilot.rag.ingest --manifest data/knowledge/manifest.jsonl --chunks data/knowledge/chunks.jsonl` 输出有效块数；重复执行数量不变，单元测试 PASS。提交代码与允许公开的 metadata／示例，受限原文留本机，提交 `feat: index provenance-aware RF knowledge`。

## Task 6：版本过滤、混合检索、重排与拒答信号（21h）

**Files:** 新增 `rag/retrieve.py`、`data/knowledge/retrieval_config.json`、`tests/rag/test_retrieve.py`；修改 schemas、ingest、依赖锁。

**Interfaces:**

- 消费任务 5 的 RetrievalFilter、Hit；新增 `RetrievalResult(status: Literal['ok','clarify','no_evidence'], hits: list[Hit], reason: str|None)`。
- `Reranker.rank(query: str, hits: list[Hit]) -> list[Hit]` Protocol；`Retriever.search(query: str, filters: RetrievalFilter) -> RetrievalResult`；构造注入 embedder/vector store/BM25/reranker/cache/index version。
- `retrieve.rrf(rankings: list[list[Hit]], k: int=60) -> list[Hit]`，按 chunk id 融合，score=Σ1/(60+rank)，rank 从 1 开始，同分按 id。

- [ ] **6.1 写过滤与融合测试。** 使用任务 5 的四块语料，dense/BM25 替身故意分别返回 A/B；过滤 version=A 后最终全部是 A。缓存 key 改 corpus_hash／embedding_revision／reranker_revision 时命中数必须 0。缺少 version 且候选多个版本涉及阈值时 status=clarify，不自动选择较新版本。

```python
def test_rrf_uses_both_rankings(hit_a, hit_b):
    fused = rrf([[hit_a, hit_b], [hit_b]])
    assert fused[0].chunk.id == hit_b.chunk.id
    assert fused[0].score == pytest.approx(1/62 + 1/61)
```

- [ ] **6.2 执行红灯。** `python -m pytest tests/rag/test_retrieve.py -v`；预期缺接口／过滤失败。
- [ ] **6.3 实现统一检索。** 两路各 20，BM25 同样先过滤文档集合，再 RRF，前 20 重排，前 5 交付；候选不足按实际数量。模型调用前后均校验候选 id 和 metadata，不能由 reranker 引入其他块。过滤要求明确字段而块该字段未知时排除，不视为自动匹配。
- [ ] **6.4 实现可校准拒答。** 新增 `data/knowledge/retrieval_config.json`，保存开发集选出的 score_threshold 与模型 revision；未校准时仅在无候选时 no_evidence，UI 标“阈值未校准”。使用独立开发题校准后才进入 live 评测，不设跨模型通用分数。缓存 TTL=3600，key 包含 query、filters 和完整 IndexVersion。
- [ ] **6.5 验证并提交。** 单元测试 PASS；真实 Qdrant integration 查询版本 A 不返回 B；人工挑 5 题查看前 5 条来源，保留 badcase。提交 `feat: retrieve version-consistent evidence with hybrid ranking`。

## Task 7：LLM 适配、证据回答与费用记录（10h）

**Files:** 新增 `llm/{client,usage}.py`、`rag/answer.py`、`migrations/versions/002_usage.py`、`tests/rag/test_answer.py`、`tests/llm/test_client.py`、`tests/llm/test_usage.py`；修改 `config/settings.py`、依赖锁。

**Interfaces:**

- `client.Message(role: str, content: str)`、`ToolCall(id: str, name: str, arguments: dict)`、`LLMReply(text: str, tool_calls: list[ToolCall], input_tokens: int, output_tokens: int)`；`LLMClient.complete(messages: list[Message], tools: list[dict]) -> LLMReply`。具体 provider 由环境配置实现，单次 30 秒，429/5xx/网络瞬态最多重试 1 次，认证错误不重试。
- `answer.Citation(chunk_id: str, document_id: str, version: str, clause: str|None, page: int|None, source_url: str|None)`；`Answer(status: str, text: str, citations: list[Citation])`。
- `answer.answer_question(query: str, evidence: RetrievalResult, llm: LLMClient) -> Answer`：只准引用提供的 chunk_id，标准结论必须来自 kind=standard；clarify/no_evidence 用确定性提示，不请求 LLM 补知识。

- [ ] **7.1 写边界测试。** ScriptedLLM 替身按给定序列返回 LLMReply 或错误。无证据调用数=0；伪造 chunk_id 返回 no_evidence；只有 project_note 时不能出现“已符合标准”的成功模板。模拟 429 后成功调用数=2，连续 429 调用数仍=2，401 调用数=1。
- [ ] **7.2 执行红灯。** `python -m pytest tests/rag/test_answer.py tests/llm/test_client.py -v`。
- [ ] **7.3 实现客户端与预算账本。** 记录模型名／revision（供应商未提供时记 unknown）、token、供应商价格配置和请求状态。用量表的 ORM 模型和预留／结算逻辑放在 `llm/usage.py`，迁移为 `migrations/versions/002_usage.py`；每次调用前按 max_tokens 预留预算，返回后结算；超预算拒绝外部请求。未知单价要求先配置，不以 0 计价。
- [ ] **7.4 实现回答。** 引用存在性可程序验证，事实是否受支持还需任务 9 的人工标注。检索文本只作为数据段，不混入 system 指令。实现固定回答结构：结论、适用条件、证据、局限。
- [ ] **7.5 验证并提交。** 上述测试 PASS；另选 3 个开发题做付费 live 调用，保存脱敏响应与费用，不使用冻结测试题调 prompt。提交 `feat: generate attributable answers with bounded LLM calls`。

---

# 阶段四：Agent 闭环（第 10 周，12h）

**目标：** 把仿真服务和知识库连成一个能干活的 Agent。这一阶段是简历上「Agent／Tool Calling／LangGraph」部分的证据。
**做什么：** 任务 8 实现 4 个白名单工具、LangGraph 工作流、PostgreSQL 持久化的会话预算，以及注入防护。
**阶段验收：** `python -m pytest tests/agent -v` PASS；能演示一次「查证据 → 提交小样本 → waiting → 查询 → 对比」，并导出完整 trace。验收通过后检查可选阶段的启动条件。

## Task 8：四工具 Agent 与跨请求预算（12h）

**Files:** 新增 `agent/{schemas,models,tools,workflow}.py`（Session、ToolInvocation 两张表的 ORM 模型在 `agent/models.py`）、`api/routes/questions.py`、`migrations/versions/003_sessions.py`、`tests/agent/test_workflow.py`；修改 `api/app.py`、`config/settings.py`。

**Interfaces:**

- `schemas.QuestionRequest(session_id: UUID|None, question: str, filters: RetrievalFilter|None)`；`AgentResponse(session_id: UUID, status: str, answer: Answer|None, job_ids: list[UUID], trace_ids: list[UUID])`。
- `tools.search_knowledge(query: str, filters: RetrievalFilter) -> RetrievalResult`；`submit_simulation(config: ExperimentRequest) -> JobView`；`get_experiment(job_id: UUID) -> JobView`；`compare_experiments(job_ids: list[UUID]) -> Comparison`。Comparison 包含每个 job 的状态、参数差异、指标差值与 incompatible_reasons；只在成功且口径一致时算差值。
- `tools.ToolRunner(session_id: UUID, session_factory)` 的 `call(name: str, arguments: dict) -> dict`：查白名单 → 用 Pydantic 校验参数 → 在事务中预留预算 → 执行 → 写 ToolInvocation；违规时返回 `{'error': code, 'message': ...}`，不抛到调用方。LangGraph 执行节点和可选 A 的 MCP Server **只能**通过它调用工具。
- `workflow.AgentService.handle(request: QuestionRequest) -> AgentResponse`；API 工厂扩为 `create_app(service: ExperimentService, agent: AgentService|None=None) -> FastAPI`，保留旧测试；POST `/v1/questions` 调用 agent，返回 200，未配置 agent 返回 503；运行中响应 status=waiting 与 job_id，不阻塞等待。
- Session 表保存 tools_used、experiments_submitted、active_request UUID、lease_until、messages/trace；ToolInvocation 表保存 session_id、调用 id、参数 hash、结果引用。计数和占用通过事务原子更新；每会话同时只处理一个请求，冲突返回 409。请求租约 600 秒，异常在 finally 释放；进程崩溃后租约过期可接管，但预算保留，旧请求不得用失效 token 写回。

- [ ] **8.1 写有界工作流测试。** 用 ScriptedLLM、真实 repo 和假的模拟执行器。连续请求同 session，第 7 次工具调用被拒绝；第三次提交被拒绝。服务对象重建后仍保留计数。两个并发相同 session 返回一个成功一个 409；注入时钟推进 601 秒后允许恢复但不能清空计数，旧 token 写回失败。恶意文档要求运行 shell 时 trace 中无白名单外工具；模型不允许靠伪造工具名绕过参数验证。
- [ ] **8.2 执行红灯。** `python -m pytest tests/agent/test_workflow.py -v`。
- [ ] **8.3 实现工具与比较。** 四工具绑定任务 3/6；get 只读取存在的 job，compare 仅接受 2 个不同 job_id。参数档／阈值／单位不同允许展示差异但数值 delta=null；不允许把跨单位结果相减。
- [ ] **8.4 实现 LangGraph 图与持久状态。** 节点为解析、工具验证、执行、返回；每次调用前事务预留工具次数，失败尝试也计数。提交前为调用 id 记录预留并关联 request_key，进程中断后用幂等 key 恢复原 job，不能再创建新实验。图恢复依赖 PostgreSQL 会话和调用日志，不仅用内存 checkpointer；参考 [LangGraph 持久化说明](https://docs.langchain.com/oss/python/langgraph/persistence)。
- [ ] **8.5 实现可重入查询。** queued/running 立即 waiting；用户后续请求沿用 session_id，预算不重置。无剩余工具额度时 UI 直接 GET job 查看结果，不无限新增 Agent 轮次。给模型最多 7 次决策轮次，防止只思考不调用工具的空转；模型 API 重试仍遵循任务 7。
- [ ] **8.6 验证并提交。** 测试 PASS，演示查证据 → 提交小样本 → waiting → 查询 → 对比，输出完整 trace；提交 `feat: orchestrate bounded RF tools with durable sessions`。

---

# 阶段五：评测与性能（第 11—12 周，22h）

**目标：** 用数据证明项目做过、做到了什么程度。简历上的每个数字都来自这一阶段。
**做什么：** 任务 9 冻结题集和场景，跑四组检索消融、Agent 端到端场景、并发压测，以及 Redis／worker 故障演练。
**阶段验收：** `docs/project/evaluation.md` 列出可重放命令、数据 hash、分子／分母和 badcase；没达标的指标如实报告。

## Task 9：冻结评测、消融与性能报告（22h）

**Files:** 新增 `data/eval/questions.jsonl`、`data/eval/scenarios.jsonl`、`data/eval/annotations.jsonl`、`src/rf_copilot/evaluation/{dataset,metrics,cli,benchmark}.py`、`tests/evaluation/test_evaluation.py`、`docs/project/evaluation.md`；更新 data-card。

**Interfaces:**

- `evaluation.dataset.validate_dataset(path: Path) -> None`：每题 id/split/template_group/category/question/gold_chunk_ids/expected_behavior；检查分组隔离与规定计数。
- `evaluation.metrics.recall_at_k(gold: list[set[str]], predicted: list[list[str]], k: int=5) -> float`：对有答案题计算每题证据召回比例再宏平均；无答案题单独处理。
- CLI `python -m rf_copilot.evaluation.cli --mode dense|bm25|hybrid|rerank --split dev|test --output PATH`；输出原始预测、引用、错误、版本和分子分母。annotation 保存 claim、是否被来源支持及标注说明，人工支持率=支持的事实数/所有可验证事实数。

- [ ] **9.1 写评测器测试。** 固定小样本验证指标定义，template_group 出现在两个 split 应抛 ValueError；没有有效事实的回答不能自动得到 100% 支持率：

```python
def test_recall_definition():
    assert recall_at_k([{'a','b'}, {'c'}], [['a'], ['c']]) == pytest.approx(0.75)
```

- [ ] **9.2 执行红灯。** `python -m pytest tests/evaluation/test_evaluation.py -v`。
- [ ] **9.3 冻结数据。** 60 题=30 dev+30 test；test=18 可答、6 条件缺失／版本冲突、6 无答案。20 个 Agent 场景含正常问答／实验／对比及非法参数、超时、API 故障、注入。先给 ground truth 再跑模型，冻结 hash；没有合法规范语料时可答题只涉及项目内容，并明确未覆盖规范问答。
- [ ] **9.4 实现并运行消融。** 四配置使用同一 corpus/model revision/题集，参数只在 dev 调整；对 test 分别运行四次 CLI，人工复核事实与引用。目标 Recall@5≥0.85、支持率≥0.90、无答案正确拒答≥5/6、Agent 成功≥16/20。未达标列 badcase 和真实值，不修改 test 来抬分。
- [ ] **9.5 实现并运行性能实验。** `python -m rf_copilot.evaluation.benchmark` 参数 `--requests 50 --concurrency 1|4|8 --cache cold|warm`；每个组合固定 50 次，预先区分重复 key 与唯一 key 比例，冷缓存用独立测试命名空间。记录提交／查询 p50/p95、排队、计算、LLM、总耗时、命中率、失败数和机器配置。进行一次 Redis 停机／恢复、worker 中断／恢复，验证数据库终态。
- [ ] **9.6 验证并提交。** 单元测试 PASS；evaluation.md 引用可重放命令、数据 hash、结果文件及分母；结论不超过数据支持范围。提交 `test: add frozen RF Copilot evaluations and benchmarks`。

---

# 阶段六：交付与面试（第 13—14 周，22h）

**目标：** 让别人能跑起来、你能讲清楚。
**做什么：** 任务 10 完成 Compose 部署、Streamlit 演示、README、架构说明、面试问答、两版简历，以及 5 分钟演示视频。
**阶段验收：** 在独立 Compose 项目名下从干净环境启动，smoke 测试 PASS；不看代码能讲 10 分钟，并回答设计第 12 节的问题。

## Task 10：可部署演示与面试交付（22h）

**Files:** 完成 Dockerfile、compose.yaml、`.env.example`、README.md；新增 `demo/app.py`、`tests/delivery/test_smoke.py`、`docs/project/architecture.md`、`docs/career/interview.md`、`docs/career/job-tracker.csv`、`docs/career/resume-ai.md`、`docs/career/resume-backend.md`、`docs/career/demo-script.md`。

**Interfaces:** Streamlit 只调用既有三个 API，提供问题输入、job 状态查询、两实验对比和报告展示；通过 `session_id` 连续会话。NPZ／图表需要时写 `artifacts/<job_id>/`，数据库只存相对路径+hash，路径由服务端生成。

- [ ] **10.1 写交付 smoke 测试。** 用完整 Compose、mock LLM profile 提交一项真实 cp 小样本，轮询直到终态，查询结果含 config/seed/version；重启 API 后仍可查询同 job；答案引用可追溯。无证据时展示局限。缺必要 API 配置时给明确错误，不启动付费调用。
- [ ] **10.2 执行红灯。** `python -m pytest tests/delivery/test_smoke.py -v -m integration`；预期交付接口／部署未完成。
- [ ] **10.3 完成部署与 UI。** API 映射 `127.0.0.1:8000`、UI `127.0.0.1:8501`，数据库／Redis／Qdrant 默认不暴露公网。Compose 配置 healthcheck、持久卷、worker/scheduler 和 migration 启动步骤；日志脱敏。README 明确 Windows 宿主+Linux 容器、锁文件安装、清洁环境启动、模型下载、无网络 mock 模式。
- [ ] **10.4 验证干净部署。** `docker compose config` 无错误；`docker compose up -d --build`；运行 smoke PASS；`python -m pytest -m "not live and not slow"` PASS。单独附 slow 硬超时和 live 结果。不要为“干净环境”删除用户现有卷，使用独立 Compose 项目名。
- [ ] **10.5 完成面试材料。** architecture 写真实边界，包括「Redis 队列 vs Celery」的取舍；interview 每个技术点写“问题—选择—代价—证据”；两版简历只用实测数字，只写已完成的可选阶段。demo-script 包含 5 分钟：问答引用、仿真、对比、失败处理；录制实际视频并由用户检查可讲解性。job-tracker 延续设计字段，每两周更新职位，不复用过期批次当在招证明。
- [ ] **10.6 自测讲解并提交。** 不看代码讲 10 分钟，回答设计第 12 节问题；遇到讲不清的模块补学习记录。暂存本任务文件，提交 `docs: deliver RF Copilot demo and interview materials`。可选 GPU/C++/代理模型不纳入本任务验收。

---

# 可选阶段（启动条件见「阶段总览」）

可选阶段不纳入核心验收，不能挤占阶段五的评测工时。没完成的可选项不写进简历。

## Task A（可选）：MCP Server（8h）

**目标：** 让 Claude Desktop、MCP Inspector 等 MCP 客户端直接使用 RF Copilot 的 4 个工具，补上 JD 中出现频率较高的 MCP 关键词，并且能现场演示。

**Files:** 新增 `src/rf_copilot/mcp_server/{__init__,__main__,server}.py`、`tests/mcp_server/test_server.py`；修改 `pyproject.toml`（`mcp` 可选依赖组）、README（客户端配置示例）。

**Interfaces:**

- Consumes：任务 8 的 `tools.ToolRunner(session_id, session_factory).call(name, arguments) -> dict`，以及 Session 表。
- `server.build_server(session_factory) -> FastMCP`：用官方 MCP Python SDK 注册 `search_knowledge`、`submit_simulation`、`get_experiment`、`compare_experiments` 4 个工具。参数 schema 直接来自任务 8 的 Pydantic 模型，每个工具体只调用 `ToolRunner.call`。SDK 具体 API 以安装锁定版本的官方文档为准。
- `python -m rf_copilot.mcp_server`：stdio 传输；启动时新建一个 Agent Session 并在 stderr 打印 session_id。预算与任务 8 相同（6 次工具调用、最多 2 个实验）。重启 server 就是新会话，这是单用户本地演示的已知限制，写进 README。
- 不新增任何工具，不提供 shell／任意代码执行；`submit_simulation` 立即返回 job_id，不阻塞等待。

- [ ] **A.1 写测试。** 按锁定 SDK 版本文档用进程内客户端连接 `build_server`：

```python
async def test_mcp_exposes_exactly_four_tools(mcp_client):
    names = {t.name for t in (await mcp_client.list_tools()).tools}
    assert names == {'search_knowledge', 'submit_simulation',
                     'get_experiment', 'compare_experiments'}
```

另外断言：对同一 fixture 语料，MCP 的 `search_knowledge` 与直接调用 `ToolRunner.call` 结果相同；第 7 次调用返回预算错误；非法 RB（rb_start=273）返回错误，并且数据库没有新 job；调用不存在的工具名返回错误。
- [ ] **A.2 执行红灯。** `python -m pytest tests/mcp_server -v`；预期模块缺失。
- [ ] **A.3 实现 server。** 按上面的接口实现，安装并锁定 `mcp` 版本。
- [ ] **A.4 验证并提交。** 测试 PASS；用 MCP Inspector 或 Claude Desktop 配置 `python -m rf_copilot.mcp_server`，完成一次「search → submit → get」，截图放进 `docs/career/demo-script.md`。提交 `feat: expose RF Copilot tools over MCP`。

## Task B（可选）：Celery 调度后端（6h）

**目标：** 证明分发器边界设计得对：换成 Celery 只新增一个实现，服务层、仓储和测试契约都不改。面试时能讲清「为什么核心先不用 Celery」。

**Files:** 新增 `src/rf_copilot/jobs/dispatch/celery_dispatcher.py`、`tests/jobs/dispatch/test_celery.py`；修改 `config/settings.py`、`compose.yaml`（`celery` profile）、`pyproject.toml`（`celery` 可选依赖组）。

**Interfaces:**

- Consumes：任务 4 的 `worker.run_job(job_id, repo, cache, time_limit_s=120.0)` 与 `tests/jobs/dispatch/contract.py`。
- `dispatch.celery_dispatcher.CeleryDispatcher.enqueue(job_id: UUID) -> None`：调用 `execute_job.delay(str(job_id))`。
- `dispatch.celery_dispatcher.execute_job(job_id: str) -> None`：Celery task，只调用 `run_job`。配置 JSON 序列化、`acks_late=True`、`worker_prefetch_multiplier=1`、不配 result backend；broker 使用同一 Redis 的 DB 1，与核心队列和缓存的 key 分开。
- `config.settings.dispatcher == 'celery'` 时由服务工厂注入 `CeleryDispatcher`；默认仍为 `redis`。reconcile 在 celery 模式下只按 dispatch_pending 补投（Celery 队列不支持 `contains`）。

- [ ] **B.1 写测试。** `tests/jobs/dispatch/test_celery.py` 以 `dispatcher='celery'` 参数化运行 `tests/jobs/dispatch/contract.py` 的全部用例，必须使用 Compose 中真实运行的 Celery worker，不使用 eager 模式。
- [ ] **B.2 执行红灯。** `docker compose --profile celery up -d`；`python -m pytest tests/jobs/dispatch/test_celery.py -v -m integration`；预期 `jobs/dispatch/celery_dispatcher.py` 缺失。
- [ ] **B.3 实现分发器与 task。** 按上面的接口实现，安装并锁定 Celery 版本。
- [ ] **B.4 验证并提交。** 契约测试在 `redis` 和 `celery` 两种模式下都 PASS；在 `docs/project/architecture.md` 补充两种分发器的取舍（依赖、运维成本、Windows 支持、可观测性）。提交 `feat: add optional Celery dispatcher behind the queue contract`。

## 自审与完成判断

- 设计覆盖：数值口径→1/2；任务可靠性→3/4；语料来源与版本→5/6；引用／费用→7；四工具／预算→8；冻结评测→9；部署／简历／演示→10。MCP→可选 A；Celery→可选 B（设计中 Celery 是主线，本版明确降为可选，见「本版修订」）。
- 阶段一致：阶段工时 26+33+43+12+22+22=158h（任务 0 的 4h 来自机动时间）；可选 A+B=14h，不超过剩余的 24h 机动时间。
- 现有代码：根目录 14 个 `.py`、`PAmodel/` 8 个、`plotfigure/` 5 个，共 27 个文件，全部出现在任务 0 的对照表中；任务 1、2 引用的旧文件路径都已改为新位置。
- 接口一致：SimConfig → ExperimentRequest → JobView → AgentResponse；未知参考功率始终 null；job 终态与单项 Metric 状态分别建模。
- Review Focus 五项均已指向具体测试；真实数据库、真实 worker 和真实模型评测不以 mock 结果代替。
- 第三方库 API、模型 revision、实际硬件速度在实施时验证锁定；当前没有实测成绩，没有依赖安装，没有代码变更。
- 本文比设计更细，但不展开算法函数体；实现者可以据契约选择内部写法。预算不足按设计删可选项，不能悄悄取消核心证据和失败测试。

## 执行交接

**执行方式：Native**（用户 2026-10-29 选定）：由同一会话按任务 0 → 10 顺序实现，全部完成后由一位独立审阅者检查整个分支。使用 superpowers:executing-plans。

**当前状态：只有计划，尚未开始实施。** 收到用户明确的开始指令后，从任务 0 的 0.1 开始；每完成一个阶段先停下来，让用户确认阶段验收结果，再进入下一阶段。

无论由谁实现，都要保留用户亲自理解代码、复现实验和练习面试讲解的环节：每个阶段结束时，用户应能不看代码讲清这一阶段做了什么、为什么这样做。
