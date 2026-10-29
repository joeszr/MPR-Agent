# RF Copilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将已有无线射频仿真改造成可复现、有引用、可执行工具且可评测的 AI 应用／后端求职项目，在 2027-01-31 前完成可面试版本。

**Architecture:** 保留既有功放与信号处理实现，提取显式配置的仿真核心，由 FastAPI、PostgreSQL、Celery 和 Redis 提供异步实验服务。Qdrant 与 BM25 检索带版本的通信资料，LangGraph 编排四个受约束工具，输出带来源和实验依据的报告。先做一个用户的本地演示系统。

**Tech Stack:** Python、NumPy、SciPy、Pydantic、pytest、FastAPI、SQLAlchemy、Alembic、PostgreSQL、Redis、Celery、Qdrant、BM25、BGE embedding/reranker、LangGraph、HTTP LLM API、Streamlit、Docker Compose。

**Spec:** [已认可设计](../specs/2026-10-23-rf-copilot-design.md)，用户已在本聊天认可；本文是其实施细化，不表示代码已经完成。

## Global Constraints

- 每周总投入 20 小时，包含学习、刷题和项目，不是纯开发 20 小时。
- 初版只支持一个开发者／演示用户，不宣称多租户生产系统。服务只监听本机或受控开发网络，不把无鉴权演示实例公开发布。
- 先支持一个固定、经过验证的 FR1 参数档：100 MHz、30 kHz SCS、NRB=273；CP-OFDM 为主，DFT-s-OFDM 在兼容层回归，不同时开放所有标准组合。
- 没有参考功率时 `mpr_db=null`，报告说明原因。
- `pass`、`fail`、`not_evaluated`、`skipped`、`error` 分开；NaN／Inf 不直接输出为非标准 JSON。
- 上限：每次会话 6 次工具调用、最多提交 2 个实验；每实验最多 2 个 RB 配置、每配置最多 3 次试验；工作进程任务硬时限 120 秒，LLM 单次请求 30 秒，瞬态 API 错误最多重试 1 次。
- Redis 结果缓存 TTL 24 小时，只缓存 succeeded；读缓存失败回源 PostgreSQL。变更代码或阈值必须换 key。检索缓存 TTL 1 小时，key 包含语料、embedding 和 reranker 版本。
- 所有评测数字都是目标或实测结果，不能预填成功；旧代码一致性不等于符合 3GPP。

## Review Focus

1. 上一轮蒙特卡洛成功、下一轮无有效点时不能沿用功率；搜索终止指标不能冒充最后有效点指标。任务 2 固定此行为。
2. worker 超时后迟到写回、两个 worker 重复领取不能覆盖终态；任务哈希必须包含 seed／代码／阈值版本。任务 3—4 固定此行为。
3. dense 已过滤而 BM25／reranker／缓存串入其他版本，必须阻止；更换模型 revision 或维度不能读旧索引。任务 5—6 固定此行为。
4. 会话续问、进程重启、并发请求不能重置或绕过工具预算；检索文本指令不能获得执行权。任务 8 固定此行为。
5. 相同问题的改写混入开发／测试集、无答案混入 Recall 分母、warm cache 冒充仿真性能，必须识别。任务 9 固定此行为。

---

## 执行边界、工时与环境

本轮只产出计划。项目还没有 Git 仓库；开始实施时先检查工作目录、备份／提交原始代码，不能现在假定存在基线提交。

按一个端到端项目执行，仿真、任务、检索是相互依赖的模块，不另建三个独立产品。依赖顺序：1 → 2 → 3 → 4；5 → 6 → 7；4 + 7 → 8 → 9 → 10。实际学习按下表串行推进，避免同时学习多套框架。

| 任务 | 项目工时上限 | 对应周 | 阶段验收 |
|---|---:|---|---|
| 1 配置与基线 | 10h | 1 | 小样本可重放，输入契约固定 |
| 2 数值核心 | 12h | 1—2 | 指标／状态／功率口径可信 |
| 3 API 与持久化 | 22h | 3—4 | 提交／查询与重复请求正确 |
| 4 队列与缓存 | 11h | 5 | 真实异步计算与故障恢复 |
| 5 语料与入库 | 12h | 6 | 30—60 个可追溯块 |
| 6 检索与重排 | 21h | 7—8 | 版本一致、拒答条件明确 |
| 7 生成适配 | 10h | 9 | 引用与 API 错误可控 |
| 8 Agent 闭环 | 12h | 9—10 | 四工具与持久预算 |
| 9 评测 | 22h | 11—12 | 冻结数据、消融和故障报告 |
| 10 交付与面试 | 22h | 13—14 | 可部署、可演示、能讲清 |
| 合计 | **154h** | 14 周 | 不包含扩展项目 |

每周其余 9h：C++ 刷题 3h、计算机基础 2h、AI 原理／官方文档 2h、复盘与机动 2h。学习内容沿用设计第 9 节。超出任务预算时记录原因，先用机动时间；仍不足按设计降级，不压缩评测为零。

工程细化选择：Python 3.11，Pydantic 2，SQLAlchemy 2；具体兼容补丁版本在首次安装后锁定，之后更新依赖必须重跑相关测试。开发／测试依赖分组，GPU 模型依赖单独分组，不要求所有测试下载模型。

Windows 可运行纯计算单元测试；Celery worker 与真实集成测试统一在 Linux 容器中，默认 prefork、concurrency=1。依据：[Celery Windows 支持说明](https://docs.celeryq.dev/en/stable/faq.html#windows)、[worker 时间限制](https://docs.celeryq.dev/en/stable/userguide/workers.html#time-limits)。不能用 eager 模式或 Windows solo worker 的结果宣称真实进程硬超时已经验证。

第三方 SDK 的具体调用以锁定版本的官方文档为准；下文签名是本项目内部契约。默认测试不用真实 LLM，live 测试显式选择且记录费用。API 月预算初始 100 元，可通过环境变量调整；尚未配置供应商单价时禁止声称已做准确费用统计。

## 文件结构与共用约定

所有路径相对 `E:/PyProject/MPR_python`；不整体迁移原有脚本。每个新包创建 `__init__.py`。采用 setuptools 的 `src` 包布局，原有 `apply_pa_model`、功放模块、`matlab_builtins`、`check_*` 暂作为显式枚举的 `py-modules` 一并打包；在空目录用安装包导入测试，不能依赖偶然的 cwd。

| 文件 | 职责／负责任务 |
|---|---|
| `src/rf_copilot/sim/{schemas,profiles,engine,cp,dft,metrics}.py` | 类型、参数档、入口、两种波形、测量；1—2 |
| `src/rf_copilot/jobs/{models,repository,service,worker,cache,reconcile}.py` | SQL 数据、事务、提交、执行、缓存、补偿；3—4 |
| `src/rf_copilot/api/{app,routes}.py` | API 工厂、路由；3、8 |
| `src/rf_copilot/rag/{schemas,ingest,retrieve,answer}.py` | 文档、入库、检索、回答；5—7 |
| `src/rf_copilot/llm/client.py` | 供应商适配与预算；7 |
| `src/rf_copilot/agent/{schemas,tools,workflow}.py` | 会话／工具类型、白名单、图；8 |
| `src/rf_copilot/settings.py` | 环境设置，不含真实密钥；3 起逐步增加 |
| `migrations/`、`alembic.ini` | schema 变更；3、8 |
| `tests/conftest.py`、`tests/{sim,jobs,rag,agent,api,eval,delivery}/` | 各任务新增的测试与注入替身 |
| `scripts/{capture_baseline,ingest,evaluate,benchmark}.py` | 可重跑命令；1、5、9 |
| `eval/{questions,scenarios}.jsonl`、`data/knowledge/{manifest,chunks}.jsonl` | 评测与语料；5、9 |
| `Dockerfile`、`compose.yaml`、`demo/app.py`、`README.md` | 部署与演示；3 起增量，10 完成 |

测试标记：`unit` 不联网；`integration` 使用独立测试数据库／Qdrant collection；`live` 才调用付费 API／真实模型；`slow` 包括硬超时测试。不得清空开发数据库。pytest 默认 `-m 'not live and not slow'`，长时限验证单列。

各任务按“测试失败 → 最小实现 → 测试通过 → 提交”执行，命令中的预期 PASS 是未来验收条件，本计划没有运行这些尚不存在的测试。提交仅暂存本任务明确文件，不能 `git add .` 把密钥、模型、原始受限资料纳入历史。

## Task 1：建立固定配置、依赖与小样本基线（10h）

**Files:** 新增 `pyproject.toml`、`uv.lock`、`.gitignore`、`src/rf_copilot/sim/schemas.py`、`src/rf_copilot/sim/profiles.py`、`scripts/capture_baseline.py`、`tests/conftest.py`、`tests/sim/test_contract.py`、`tests/fixtures/sim_cases.json`、`docs/numerical-audit.md`。

**Interfaces:**

- `profiles.get_profile(profile_id: str) -> RadioProfile`：`fr1_100m_30k_legacy_v1` 固定 CBW=100 MHz、SCS=30 kHz、NRB=273、Fs=614400 kHz、IFFT=20480、CP=15360；名称明确继承实现，不能声称标准 CP。
- `schemas.SimConfig`：`waveform: Literal['cp','dft']`、`profile_id`、`rb_start: int`、`rb_count: int`、`mod_order: Literal[4,16,64,256]`、`pa_model: Literal['HZW_HB']`、`seed: int`、`trials: int`、`threshold_profile_id`、`engine_version`；整数严格验证，RB 越界拒绝，seed 范围 0..2**32-1，trials 1..3。
- `schemas.ExperimentRequest(configs: list[SimConfig])`：1..2 个配置；HTTP 层仅接受 cp，dft 供兼容测试。
- 阈值档 `legacy_cp_v1`／`legacy_dft_v1`：ACLR=31 dB；EVM 按旧表；DFT QPSK=3.5%，其他 QAM=12.5/8/3.5%。标注实验条件，不附虚构标准条款。
- `schemas.Metric(value: float|None, unit: str, limit: float|None, margin: float|None, status: str)`；检查状态用设计中的五值枚举。`TrialResult` 保存 trial_index、seed、status、power、drive、metrics、reason；`SimResult` 保存 config、status、trials、output_power_db_ref、mpr_db、reason、elapsed_s。非有限数映射 null 并记录原因，不默默变成成功。
- `tests/conftest.py` 的 `make_config(**overrides) -> SimConfig` 默认 cp、RB=(0,1)、256QAM、seed=42、trials=1、上述固定档、engine_version=`engine-v1`；只用于测试。

- [ ] **1.1 建立版本基线。** 确认无 Git 后执行 `git init`；`.gitignore` 排除 `.env`、虚拟环境、缓存、模型、运行输出和原始受限资料。明确选择原有 `.py` 与设计文档提交，记录 commit ID 到 numerical-audit；不改原始数值实现。
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
- [ ] **1.4 实现类型与打包。** schemas/profiles 按上述契约实现；pyproject 定义依赖与 pytest 标记，生成锁文件。先检查 Python／uv 是否可用，缺少时再安装。添加编辑器外导入检查。
- [ ] **1.5 捕获旧基线。** `capture_baseline.py` 在独立子进程按案例设置旧模块参数后调用 `simulate_config`，每例 120 秒外部 watchdog，不执行默认 main。12 例固定为：CP 的 (0,1)、(272,1)、(120,12)、(0,24)、(249,24)、(100,50)；非法越界；DFT (0,7) 跳过；一次成功后无有效点的替身；全部检查通过导致搜索不收敛的替身；固定点 EVM 恰好阈值；CP IBE 未评估。真实案例 seed=42、trials=1。基线输出存 `tests/fixtures/legacy_baseline.json`，超时／异常原样记录。
- [ ] **1.6 验证并提交。** 重跑契约测试应 PASS；`python scripts/capture_baseline.py --cases tests/fixtures/sim_cases.json --timeout 120` 应生成 12 条带状态记录，不要求旧代码全部正确。`git add` 仅本任务文件；`git commit -m "test: establish RF simulation contracts and baseline"`。

## Task 2：提取可解释、有界的仿真核心（12h）

**Files:** 新增 `sim/engine.py`、`sim/cp.py`、`sim/dft.py`、`sim/metrics.py`（均在 `src/rf_copilot/` 下）、`tests/sim/test_engine.py`、`tests/sim/test_metrics.py`；修改 `CP_ofdm_mainV6.py:91`、`DFT_ofdm_mainV2.py:99` 的计算入口与 CLI、`check_EVM_CP.py`、`check_EVM_DFT.py`、`check_ACLR.py`；更新 numerical-audit。

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
- [ ] **2.6 验证并提交。** `python -m pytest tests/sim -v`；`python CP_ofdm_mainV6.py --smoke --seed 42`；`python DFT_ofdm_mainV2.py --smoke --seed 42`。正常基线容差 atol=1e-6/rtol=1e-5；seed+i 导致多试验旧随机流不同，逐试验重放对照而非强求总数相同。修复场景以独立断言为准。暂存本任务文件，提交 `refactor: expose bounded reproducible RF simulations`。

## Task 3：实验持久化与 HTTP 接口（22h）

**Files:** 新增 `jobs/{models,repository,service}.py`、`api/{app,routes}.py`、`settings.py`、`migrations/env.py`、`migrations/versions/001_jobs.py`、`alembic.ini`、`.env.example`、初版 `compose.yaml`、`tests/jobs/test_repository.py`、`tests/api/test_experiments.py`（模块目录沿文件地图）；更新依赖锁。

**Interfaces:**

- `models.JobView`：id UUID、status、request、result `list[SimResult]|None`、dispatch_pending bool、error_code、created_at、started_at、finished_at、request_hash、attempt_token UUID|None。
- `repository.JobRepository(session_factory)`：`get_or_create(request: ExperimentRequest) -> tuple[JobView,bool]`、`get(job_id: UUID) -> JobView|None`、`claim(job_id: UUID, token: UUID, now: datetime) -> bool`、`finish(job_id: UUID, token: UUID, status: str, result: list[SimResult]|None, error: str|None) -> bool`。
- `service.request_key(request: ExperimentRequest) -> str`：规范化 JSON + SHA256；包含配置顺序、seed、所有 profile/engine 版本，不包含时间戳。`ExperimentService(repo, dispatcher)` 的 `submit(request) -> JobView`、`get(job_id) -> JobView|None`；dispatcher 接口 `enqueue(job_id: UUID) -> None`，本任务用测试替身。
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

## Task 4：真正的队列、缓存和终态恢复（11h）

**Files:** 新增 `jobs/{worker,cache,reconcile}.py`、初版 `Dockerfile`、`tests/jobs/test_worker.py`、`tests/jobs/test_cache.py`、`tests/jobs/test_reconcile.py`；修改 service、repository、compose 与依赖锁。

**Interfaces:**

- `worker.execute_job(job_id: str) -> None`：Celery task；消费任务 3 的 repo 与任务 2 simulate。
- `cache.ResultCache(redis_client)`：`get(key: str) -> list[SimResult]|None`、`put(key: str, result: list[SimResult]) -> None`；TTL=86400。
- `repository.pending(limit: int) -> list[JobView]`、`mark_dispatched(job_id: UUID) -> None`、`expire_running(before: datetime) -> int`；只操作满足状态的记录。
- `reconcile.reconcile(now: datetime) -> dict[str,int]`：重发 queued + dispatch_pending，以及 running 超过 120 秒的任务标 timed_out；每 15 秒执行，崩溃可见性最迟约 135 秒。初版终态不自动重跑。

- [ ] **4.1 写故障测试。** fixture `repo` 为真实 PostgreSQL，`redis_client` 为测试 Redis，模拟 worker 使用可控 token 和 now：领取两次只有一次 true；超时扫描后迟到 finish=false；enqueue 失败 pending=true，恢复后补投可完成。缓存验证 `ttl in 1..86400`，删除缓存后服务从数据库得到同样结果，failed 不缓存。
- [ ] **4.2 执行红灯。** `python -m pytest tests/jobs/test_worker.py tests/jobs/test_cache.py tests/jobs/test_reconcile.py -v`；预期新逻辑缺失。
- [ ] **4.3 实现 worker。** 新建安装锁定依赖和本项目的 Linux Python 3.11 镜像，让 Compose worker/scheduler 共用。claim 后顺序处理最多 2 配置，整项任务 time_limit=120；使用 JSON 序列化、late ack、prefetch=1；任何 SimResult error 则任务 failed，保留已取得的结果和原因。不使用 Celery result backend 充当任务事实来源。
- [ ] **4.4 实现缓存和补偿。** Redis key 前缀 `rf:result:`；写缓存失败不撤回数据库成功。增加 scheduler 容器调用 reconcile；补投可能重复，依靠 claim 拒绝重复执行。Redis 不可用时查询回源、提交仍 queued。Redis 设置容量与 noeviction，避免把 broker 消息当缓存驱逐；满容量错误按入队失败处理。
- [ ] **4.5 验证并提交。** 启动 postgres/redis/worker/scheduler，重跑 jobs 测试 PASS；单列 `python -m pytest tests/jobs/test_worker.py -m slow -v`，Linux 实际阻塞任务超过 120 秒被终止，并在扫描后标 timed_out。不要在事件循环 sleep 模拟硬超时。提交 `feat: run recoverable jobs with Redis caching`。

## Task 5：建立可追溯语料与向量索引（12h）

**Files:** 新增 `rag/schemas.py`、`rag/ingest.py`、`scripts/ingest.py`、`data/knowledge/manifest.jsonl`、`data/knowledge/chunks.jsonl`、`docs/data-card.md`、`tests/rag/test_ingest.py`；增加 Qdrant 服务与模型可选依赖。

**Interfaces:**

- `schemas.Chunk`：id/text/document_id/version/release/clause/page/section/band/duplex/power_class/source_url/content_hash；字段未知可 null，version 必须明确或 `project-note-v1`；追加 `kind: Literal['standard','project_note','experiment']`，不能混淆标准与自定义阈值。
- `schemas.IndexVersion`：corpus_hash、embedding_model、embedding_revision、dimension、reranker_revision、tokenizer_version；生成索引命名后缀，不能用浮动 latest。
- `ingest.load_chunks(path: Path) -> list[Chunk]`；`ingest.build_index(chunks: list[Chunk], version: IndexVersion, embedder: Embedder, store: VectorStore) -> int`。
- 同时在 schemas 定义 `RetrievalFilter(document_id: str|None, version: str|None, band: str|None, power_class: str|None)` 与 `Hit(chunk: Chunk, score: float)`；任务 6 复用，避免类型依赖倒置。两个 Protocol 也定义在 schemas：`Embedder.encode(texts: list[str]) -> np.ndarray`；`VectorStore.upsert(chunks: list[Chunk], vectors: np.ndarray, version: IndexVersion) -> None`、`search(query_vector: np.ndarray, filters: RetrievalFilter, limit: int) -> list[Hit]`。

- [ ] **5.1 写入库测试。** 文档 fixture 是 4 条人工合成文本，版本 A/B 各两条，不伪装真实条款；断言重入无重复、修改内容 hash 改变、向量 dimension 不匹配抛 ValueError、缺 source 的 standard 块拒绝入库。记录字段完整性而非测试真实标准内容。
- [ ] **5.2 执行红灯。** `python -m pytest tests/rag/test_ingest.py -v`；预期 ingest 缺失。
- [ ] **5.3 准备语料。** 人工校对 30—60 块，表格保留标题、单位和脚注；标准原文可用时才标 standard。若官方资源仍不可取，先以项目说明／实验阈值完成链路，回答明确“无规范证据”，不能编造标准块或题目答案。data-card 记录来源、许可、获取日期、文件 hash 与核对人。
- [ ] **5.4 实现索引。** BGE-M3 初选，revision 和维度由实际模型卡／输出核对并写 manifest；Qdrant 元数据使用完整字段；本地 BM25 原始文本索引与 Qdrant 使用同一 corpus_hash。中文术语使用可固定版本的分词器，保护 ACLR、EVM、38.101-1 等 token；分词器版本进入索引身份。
- [ ] **5.5 验证并提交。** `python scripts/ingest.py --manifest data/knowledge/manifest.jsonl --chunks data/knowledge/chunks.jsonl` 输出有效块数；重复执行数量不变，单元测试 PASS。提交代码与允许公开的 metadata／示例，受限原文留本机，提交 `feat: index provenance-aware RF knowledge`。

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

**Files:** 新增 `llm/client.py`、`rag/answer.py`、`tests/rag/test_answer.py`、`tests/llm/test_client.py`；修改 settings、依赖锁。

**Interfaces:**

- `client.Message(role: str, content: str)`、`ToolCall(id: str, name: str, arguments: dict)`、`LLMReply(text: str, tool_calls: list[ToolCall], input_tokens: int, output_tokens: int)`；`LLMClient.complete(messages: list[Message], tools: list[dict]) -> LLMReply`。具体 provider 由环境配置实现，单次 30 秒，429/5xx/网络瞬态最多重试 1 次，认证错误不重试。
- `answer.Citation(chunk_id: str, document_id: str, version: str, clause: str|None, page: int|None, source_url: str|None)`；`Answer(status: str, text: str, citations: list[Citation])`。
- `answer.answer_question(query: str, evidence: RetrievalResult, llm: LLMClient) -> Answer`：只准引用提供的 chunk_id，标准结论必须来自 kind=standard；clarify/no_evidence 用确定性提示，不请求 LLM 补知识。

- [ ] **7.1 写边界测试。** ScriptedLLM 替身按给定序列返回 LLMReply 或错误。无证据调用数=0；伪造 chunk_id 返回 no_evidence；只有 project_note 时不能出现“已符合标准”的成功模板。模拟 429 后成功调用数=2，连续 429 调用数仍=2，401 调用数=1。
- [ ] **7.2 执行红灯。** `python -m pytest tests/rag/test_answer.py tests/llm/test_client.py -v`。
- [ ] **7.3 实现客户端与预算账本。** 记录模型名／revision（供应商未提供时记 unknown）、token、供应商价格配置和请求状态。新增 jobs models 的 usage 表及 `migrations/versions/002_usage.py`；每次调用前按 max_tokens 预留预算，返回后结算；超预算拒绝外部请求。未知单价要求先配置，不以 0 计价。
- [ ] **7.4 实现回答。** 引用存在性可程序验证，事实是否受支持还需任务 9 的人工标注。检索文本只作为数据段，不混入 system 指令。实现固定回答结构：结论、适用条件、证据、局限。
- [ ] **7.5 验证并提交。** 上述测试 PASS；另选 3 个开发题做付费 live 调用，保存脱敏响应与费用，不使用冻结测试题调 prompt。提交 `feat: generate attributable answers with bounded LLM calls`。

## Task 8：四工具 Agent 与跨请求预算（12h）

**Files:** 新增 `agent/{schemas,tools,workflow}.py`、`migrations/versions/003_sessions.py`、`tests/agent/test_workflow.py`；修改 jobs/models、API app/routes、settings。

**Interfaces:**

- `schemas.QuestionRequest(session_id: UUID|None, question: str, filters: RetrievalFilter|None)`；`AgentResponse(session_id: UUID, status: str, answer: Answer|None, job_ids: list[UUID], trace_ids: list[UUID])`。
- `tools.search_knowledge(query: str, filters: RetrievalFilter) -> RetrievalResult`；`submit_simulation(config: ExperimentRequest) -> JobView`；`get_experiment(job_id: UUID) -> JobView`；`compare_experiments(job_ids: list[UUID]) -> Comparison`。Comparison 包含每个 job 的状态、参数差异、指标差值与 incompatible_reasons；只在成功且口径一致时算差值。
- `workflow.AgentService.handle(request: QuestionRequest) -> AgentResponse`；API 工厂扩为 `create_app(service: ExperimentService, agent: AgentService|None=None) -> FastAPI`，保留旧测试；POST `/v1/questions` 调用 agent，返回 200，未配置 agent 返回 503；运行中响应 status=waiting 与 job_id，不阻塞等待。
- Session 表保存 tools_used、experiments_submitted、active_request UUID、lease_until、messages/trace；ToolInvocation 表保存 session_id、调用 id、参数 hash、结果引用。计数和占用通过事务原子更新；每会话同时只处理一个请求，冲突返回 409。请求租约 600 秒，异常在 finally 释放；进程崩溃后租约过期可接管，但预算保留，旧请求不得用失效 token 写回。

- [ ] **8.1 写有界工作流测试。** 用 ScriptedLLM、真实 repo 和假的模拟执行器。连续请求同 session，第 7 次工具调用被拒绝；第三次提交被拒绝。服务对象重建后仍保留计数。两个并发相同 session 返回一个成功一个 409；注入时钟推进 601 秒后允许恢复但不能清空计数，旧 token 写回失败。恶意文档要求运行 shell 时 trace 中无白名单外工具；模型不允许靠伪造工具名绕过参数验证。
- [ ] **8.2 执行红灯。** `python -m pytest tests/agent/test_workflow.py -v`。
- [ ] **8.3 实现工具与比较。** 四工具绑定任务 3/6；get 只读取存在的 job，compare 仅接受 2 个不同 job_id。参数档／阈值／单位不同允许展示差异但数值 delta=null；不允许把跨单位结果相减。
- [ ] **8.4 实现 LangGraph 图与持久状态。** 节点为解析、工具验证、执行、返回；每次调用前事务预留工具次数，失败尝试也计数。提交前为调用 id 记录预留并关联 request_key，进程中断后用幂等 key 恢复原 job，不能再创建新实验。图恢复依赖 PostgreSQL 会话和调用日志，不仅用内存 checkpointer；参考 [LangGraph 持久化说明](https://docs.langchain.com/oss/python/langgraph/persistence)。
- [ ] **8.5 实现可重入查询。** queued/running 立即 waiting；用户后续请求沿用 session_id，预算不重置。无剩余工具额度时 UI 直接 GET job 查看结果，不无限新增 Agent 轮次。给模型最多 7 次决策轮次，防止只思考不调用工具的空转；模型 API 重试仍遵循任务 7。
- [ ] **8.6 验证并提交。** 测试 PASS，演示查证据 → 提交小样本 → waiting → 查询 → 对比，输出完整 trace；提交 `feat: orchestrate bounded RF tools with durable sessions`。

## Task 9：冻结评测、消融与性能报告（22h）

**Files:** 新增 `eval/questions.jsonl`、`eval/scenarios.jsonl`、`eval/annotations.jsonl`、`scripts/evaluate.py`、`scripts/benchmark.py`、`tests/eval/test_evaluation.py`、`docs/evaluation.md`；更新 data-card。

**Interfaces:**

- `evaluate.validate_dataset(path: Path) -> None`：每题 id/split/template_group/category/question/gold_chunk_ids/expected_behavior；检查分组隔离与规定计数。
- `evaluate.recall_at_k(gold: list[set[str]], predicted: list[list[str]], k: int=5) -> float`：对有答案题计算每题证据召回比例再宏平均；无答案题单独处理。
- CLI `evaluate.py --mode dense|bm25|hybrid|rerank --split dev|test --output PATH`；输出原始预测、引用、错误、版本和分子分母。annotation 保存 claim、是否被来源支持及标注说明，人工支持率=支持的事实数/所有可验证事实数。

- [ ] **9.1 写评测器测试。** 固定小样本验证指标定义，template_group 出现在两个 split 应抛 ValueError；没有有效事实的回答不能自动得到 100% 支持率：

```python
def test_recall_definition():
    assert recall_at_k([{'a','b'}, {'c'}], [['a'], ['c']]) == pytest.approx(0.75)
```

- [ ] **9.2 执行红灯。** `python -m pytest tests/eval/test_evaluation.py -v`。
- [ ] **9.3 冻结数据。** 60 题=30 dev+30 test；test=18 可答、6 条件缺失／版本冲突、6 无答案。20 个 Agent 场景含正常问答／实验／对比及非法参数、超时、API 故障、注入。先给 ground truth 再跑模型，冻结 hash；没有合法规范语料时可答题只涉及项目内容，并明确未覆盖规范问答。
- [ ] **9.4 实现并运行消融。** 四配置使用同一 corpus/model revision/题集，参数只在 dev 调整；对 test 分别运行四次 CLI，人工复核事实与引用。目标 Recall@5≥0.85、支持率≥0.90、无答案正确拒答≥5/6、Agent 成功≥16/20。未达标列 badcase 和真实值，不修改 test 来抬分。
- [ ] **9.5 实现并运行性能实验。** benchmark 参数 `--requests 50 --concurrency 1|4|8 --cache cold|warm`；每个组合固定 50 次，预先区分重复 key 与唯一 key 比例，冷缓存用独立测试命名空间。记录提交／查询 p50/p95、排队、计算、LLM、总耗时、命中率、失败数和机器配置。进行一次 Redis 停机／恢复、worker 中断／恢复，验证数据库终态。
- [ ] **9.6 验证并提交。** 单元测试 PASS；evaluation.md 引用可重放命令、数据 hash、结果文件及分母；结论不超过数据支持范围。提交 `test: add frozen RF Copilot evaluations and benchmarks`。

## Task 10：可部署演示与面试交付（22h）

**Files:** 完成 Dockerfile、compose.yaml、`.env.example`、README.md；新增 `demo/app.py`、`tests/delivery/test_smoke.py`、`docs/architecture.md`、`docs/interview.md`、`docs/job-tracker.csv`、`docs/resume-ai.md`、`docs/resume-backend.md`、`docs/demo-script.md`。

**Interfaces:** Streamlit 只调用既有三个 API，提供问题输入、job 状态查询、两实验对比和报告展示；通过 `session_id` 连续会话。NPZ／图表需要时写 `artifacts/<job_id>/`，数据库只存相对路径+hash，路径由服务端生成。

- [ ] **10.1 写交付 smoke 测试。** 用完整 Compose、mock LLM profile 提交一项真实 cp 小样本，轮询直到终态，查询结果含 config/seed/version；重启 API 后仍可查询同 job；答案引用可追溯。无证据时展示局限。缺必要 API 配置时给明确错误，不启动付费调用。
- [ ] **10.2 执行红灯。** `python -m pytest tests/delivery/test_smoke.py -v -m integration`；预期交付接口／部署未完成。
- [ ] **10.3 完成部署与 UI。** API 映射 `127.0.0.1:8000`、UI `127.0.0.1:8501`，数据库／Redis／Qdrant 默认不暴露公网。Compose 配置 healthcheck、持久卷、worker/scheduler 和 migration 启动步骤；日志脱敏。README 明确 Windows 宿主+Linux 容器、锁文件安装、清洁环境启动、模型下载、无网络 mock 模式。
- [ ] **10.4 验证干净部署。** `docker compose config` 无错误；`docker compose up -d --build`；运行 smoke PASS；`python -m pytest -m "not live and not slow"` PASS。单独附 slow 硬超时和 live 结果。不要为“干净环境”删除用户现有卷，使用独立 Compose 项目名。
- [ ] **10.5 完成面试材料。** architecture 写真实边界；interview 每个技术点写“问题—选择—代价—证据”；两版简历只用实测数字。demo-script 包含 5 分钟：问答引用、仿真、对比、失败处理；录制实际视频并由用户检查可讲解性。job-tracker 延续设计字段，每两周更新职位，不复用过期批次当在招证明。
- [ ] **10.6 自测讲解并提交。** 不看代码讲 10 分钟，回答设计第 12 节问题；遇到讲不清的模块补学习记录。暂存本任务文件，提交 `docs: deliver RF Copilot demo and interview materials`。可选 GPU/C++/代理模型不纳入本任务验收。

## 自审与完成判断

- 设计覆盖：数值口径→1/2；任务可靠性→3/4；语料来源与版本→5/6；引用／费用→7；四工具／预算→8；冻结评测→9；部署／简历／演示→10。
- 接口一致：SimConfig → ExperimentRequest → JobView → AgentResponse；未知参考功率始终 null；job 终态与单项 Metric 状态分别建模。
- Review Focus 五项均已指向具体测试；真实数据库、真实 worker 和真实模型评测不以 mock 结果代替。
- 第三方库 API、模型 revision、实际硬件速度在实施时验证锁定；当前没有实测成绩，没有依赖安装，没有代码变更。
- 本文比设计更细，但不展开算法函数体；实现者可以据契约选择内部写法。预算不足按设计删可选项，不能悄悄取消核心证据和失败测试。

## 执行交接

用户当前授权的是设计与计划文档，未要求立即实现全部功能。建议把这份文档作为个人学习清单，任务完成后逐项勾选。

如由编码代理实施，建议 Native：模块接口顺序依赖明显、项目规模受限，由同一代理逐项实现便于保持上下文并控制开销。也可选 Subagent-driven，为每个任务安排独立实现与审阅；两者均须保留用户亲自理解代码、复现实验与面试讲解的环节。

按照 writing-plans 的交接要求，开始实现前先审阅本计划并选择执行方式；这不影响本次文档交付完成。
