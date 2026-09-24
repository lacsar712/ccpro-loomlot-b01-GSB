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
3. **DyeLot** — `vatId`, `recipeName`, `fabricKg`, `startedAt`, `operatorName`, `closedAt`（可空，空=未关闭）
4. **FastnessCheck** — `dyeLotId`, `checkedAt`, `washFastness`(1–5), `rubFastness`(>0), `tempC`, `notes`, `retestCount`（复测次数，非负整数）, `lastRetestAt`（末次复测时刻，可空）

### 规则

- 仅当染缸状态为 `ready` 或 `dyeing` 时可新建染程，否则 409
- 新建染程后，染缸状态自动设为 `dyeing`
- 可选接口：`POST /api/vats/{id}/drain` 将染缸置为 `drain`
- **复测规定次数**：后端常量 `app/constants.py::REQUIRED_RETEST_COUNT = 2`（至少 2）。看板接口同时下发 `requiredRetestCount`，前端不硬编码
- 色牢度复测字段校验（违例返回 400，中文消息）：
  - `retestCount` 必须为非负整数
  - `retestCount > 0` 时 `lastRetestAt` 必填，且不得早于 `checkedAt`
  - `retestCount = 0` 时 `lastRetestAt` 必须为空
- 色牢度页可通过 `POST /api/fastness-checks/{id}/retest` 登记复测（次数 +1，末次时刻默认取当前时间）
- **染程关闭规则**：`POST /api/dye-lots/{id}/close` 仅当该染程下**至少一条**色牢度的 `retestCount >= REQUIRED_RETEST_COUNT` 时才可关闭，否则 409
- 染程**关闭后禁止再追加**色牢度抽检与复测，否则 409；重复关闭同样 409
- 列表筛选：
  - `GET /api/dye-lots?closed=false&retestUnmet=true` — 未关闭且复测未达标的染程
  - `GET /api/fastness-checks?retestUnmet=true` — 复测未达标（次数不足规定次数）的色牢度行
- **看板口径**：`GET /api/dashboard/stats` 的 `openRetestUnmetCount`（未关闭且复测未达标的染程数）与染程列表上述筛选条件**共用同一 SQL 表达式**（`DyeLot.open_retest_unmet_criterion`），看板数字必须等于用列表条件手数出的行数

## 主要 API

- `POST /api/auth/login`（OAuth2 表单）
- `GET /api/auth/me`
- `GET/POST/PUT/DELETE /api/dye-houses`
- `GET/POST/PUT/DELETE /api/vats` · `POST /api/vats/{id}/drain`
- `GET/POST/PUT/DELETE /api/dye-lots`（支持 `closed`、`retestUnmet`、`vatId` 查询参数）· `POST /api/dye-lots/{id}/close`
- `GET/POST/PUT/DELETE /api/fastness-checks`（支持 `dyeLotId`、`retestUnmet` 查询参数）· `POST /api/fastness-checks/{id}/retest`
- `GET /api/dashboard/stats`

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
