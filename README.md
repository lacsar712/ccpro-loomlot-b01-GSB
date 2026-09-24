# LoomLot-01 · 染坊缸染与色牢度抽检

靛蓝染坊台：按 **染坊 → 染缸 → 染程 → 色牢度** 工序推进，聚焦缸染调度与抽检，不是库存出入库系统。

## 技术栈

| 层 | 技术 |
| --- | --- |
| Backend | FastAPI + SQLAlchemy 2 + Pydantic v2 + Postgres + JWT |
| Frontend | Svelte 4 + Vite + svelte-spa-router |
| 部署 | docker-compose（db + backend + frontend/nginx） |

## 端口

| 服务 | 端口 |
| --- | --- |
| 前端 | **3600** |
| 后端 API | **8600** |
| PostgreSQL | **5439** |

数据库账号：`loomlot` / `loomlot` / 库名 `loomlot`。

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | 染坊主管 |
| `dyer` | `123456` | 染程操作员 |

容器启动时 entrypoint 自动建表并 seed。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\LoomLot\LoomLot-01
docker compose up -d --build
```

浏览器：http://localhost:3600  
API：http://localhost:8600/api/health

停止：

```bash
docker compose down
```

## 业务实体

1. **DyeHouse** — `name`, `waterNote`, `notes`
2. **Vat** — `dyeHouseId`, `vatCode`, `fiberType`, `capacityL`, `status` ∈ `ready|dyeing|drain`
3. **DyeLot** — `vatId`, `recipeName`, `fabricKg`, `startedAt`, `operatorName`, `closedAt`（关闭时刻，可空）
4. **FastnessCheck** — `dyeLotId`, `checkedAt`, `washFastness`(1–5), `rubFastness`(>0), `tempC`, `notes`, `retestCount`（复测次数，非负整数）, `lastRetestAt`（末次复测时刻，可空）

### 规则

- 仅当染缸状态为 `ready` 或 `dyeing` 时可新建染程，否则 409
- 新建染程后，染缸状态自动设为 `dyeing`
- 可选接口：`POST /api/vats/{id}/drain` 将染缸置为 `drain`

#### 色牢度复测与染程关闭

- **规定复测次数常量 `REQUIRED_RETEST_COUNT` = 2**（配置项 `required_retest_count`，可经环境变量 `REQUIRED_RETEST_COUNT` 覆盖；代码保证至少为 2）。看板接口同时返回 `requiredRetestCount` 供前端展示。
- 每条色牢度抽检记录复测次数 `retestCount`（非负整数）与末次复测时刻 `lastRetestAt`（可空）：
  - `retestCount > 0` 时 `lastRetestAt` 必填，且不得早于 `checkedAt`，否则 **400 中文错误**；
  - `retestCount = 0` 时不得填写 `lastRetestAt`，否则 **400**。
- 染程增加关闭动作 `POST /api/dye-lots/{id}/close`：
  - 仅当该染程下**至少一条**色牢度抽检的复测次数达到规定次数，染程才可关闭（写入 `closedAt`）；否则 **409**；
  - 重复关闭返回 **409**；
  - 染程关闭后其色牢度记录只读：禁止追加（POST 409）、禁止改挂到已关闭染程或修改其已有记录（PUT 409）、禁止删除（DELETE 409）。
- 色牢度页可对已有抽检行「登记复测」：复测次数 +1 并记录末次复测时刻。
- 筛选：
  - `GET /api/fastness-checks?retestUnmet=true` 只返回复测次数未达规定次数的行；
  - `GET /api/dye-lots?retestUnmet=true` 只返回**未关闭且复测未达标**的染程。
- 看板新增 `lotsRetestPending`（未关闭且复测未达标的染程数）。该数字与染程列表 `retestUnmet=true` 手数结果**同一口径**（后端共用 `app/retest_rules.py` 的 `retest_pending_lot_ids` 查询，不得各算各的）。
- 种子数据含一条复测未达标（`retestCount=0`）的色牢度记录，挂在一条未关闭染程上（看板初始即应显示至少 1）；另有一条复测已达标（`retestCount=2`）的染程可直接演示关闭。

## 主要 API

- `POST /api/auth/login`（OAuth2 表单）
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/dye-houses`
- `GET/POST/PUT/DELETE /api/vats` · `POST /api/vats/{id}/drain`
- `GET/POST/PUT/DELETE /api/dye-lots` · `POST /api/dye-lots/{id}/close`（关闭染程）· 列表支持 `?retestUnmet=true`
- `GET/POST/PUT/DELETE /api/fastness-checks`（支持 `?retestUnmet=true`）
- `GET /api/dashboard/stats`（含 `lotsRetestPending`、`requiredRetestCount`）

除登录外需 `Authorization: Bearer <token>`。字段对外为 camelCase。

## 目录

```
LoomLot-01/
├── docker-compose.yml
├── backend/          # FastAPI
├── frontend/         # Svelte 4 + Vite + nginx
└── README.md
```

## 本地开发

### 数据库

```bash
docker compose up -d db
```

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://loomlot:loomlot@127.0.0.1:5439/loomlot"
python -c "from app.database import Base, engine; from app import models; Base.metadata.create_all(bind=engine)"
python -c "from app.seed import seed; seed()"
uvicorn app.main:app --reload --port 8600
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

开发态 Vite 将 `/api` 代理到 `http://127.0.0.1:8600`。
