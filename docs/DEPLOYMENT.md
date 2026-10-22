# 部署与演示流程

下列流程区分“脚本已准备”与“环境已运行”。真实 Azure 连接、校园模型网络和 Docker/kind 是否可用必须在对应电脑实测。

## 1. 本机开发

需要 Python 3.12、Node.js 22+、PostgreSQL 17（本地或 Azure）。在仓库根目录运行：

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm ci --prefix frontend
Copy-Item .env.example .env
```

编辑 `.env`：填写 DATABASE_URL、MODEL_API_KEY、指定 Base URL。MODEL_NAME 保持 campus-qwen。DEMO_MODE=true，默认 MODEL_MODE=live。不要把真实配置提交到 Git。

```powershell
# 前台启动方式，使用两个终端
.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8001
npm run dev --prefix frontend
```

或者执行 `./scripts/start-dev.ps1`，它会隐藏后台窗口启动 API 与前端。本次 MSI 的本地 PostgreSQL 二进制和数据位于 `.runtime/`，脚本可复用它；此目录不提交到仓库。

打开 http://127.0.0.1:5622/ ，API 文档 http://127.0.0.1:8001/docs 。确认 http://127.0.0.1:5622/api/health 返回 ok。此检查只证明数据库连接，不代表模型可达。

## 2. Azure PostgreSQL Flexible Server

1. 在 Azure 创建/选用 PostgreSQL Flexible Server，创建 secondspace 数据库和专用连接账号。创建资源可能产生费用，应由账号所有者选择规格。
2. 配置开发电脑/演示电脑的出口 IP 防火墙规则，或连接已有私网。不要为演示开放所有来源。
3. 把连接字符串写到私有 `.env`，URL 中的密码需 URL 编码：

```dotenv
DATABASE_URL=postgresql://USER:ENCODED_PASSWORD@SERVER.postgres.database.azure.com:5432/secondspace?sslmode=require
```

可使用 `sslmode=verify-full` 并配置受信任根证书。Azure 端保持 TLS 要求。不要在日志中打印连接字符串。

4. API 启动时执行幂等 schema 创建与首次 seed，再初始化 LangGraph checkpoint 表。运行账号目前需要建表权限；若采用严格生产权限应独立执行迁移。
5. 请求 health、创建订单、验收、重启 API，再查询订单，验证 Azure 持久化。读取 `payments` / `settlements` 核对订单与金额。

## 3. 模型连通性

Base URL 为 `.env` 中的校园内网地址，必须由运行 API 的电脑/容器能够访问。仅允许 campus-qwen。执行：

```powershell
.venv/Scripts/python.exe scripts/check-model.py
```

脚本仅报告连通性/结构化文本响应，不输出 key。文本成功不代表视觉能力；用真实照片上架另行验证。图片审核失败时保留拒绝上架并允许修改重试。需要离线自动测试时，显式使用 MODEL_MODE=fixture，不将其结果描述为真实模型调用。

## 4. Docker Compose

先安装并启动 Docker Desktop（Linux containers）。

```powershell
# Azure 模式：DATABASE_URL 指向 Azure
docker compose up --build -d
# 本地 PostgreSQL 模式：在 .env 设置 URL-safe POSTGRES_PASSWORD
docker compose -f compose.yaml -f compose.local.yaml up --build -d
docker compose ps
```

打开 http://127.0.0.1:5623/ 。该端口仅绑定 loopback。Nginx 反向代理 /api 到 backend；图片保存在 uploads volume。本地模式的数据库另有 postgres volume。停机使用 `docker compose down`，不加 `-v`，保留演示数据。

## 5. kind + kubectl

先安装 Docker Desktop、kind、kubectl。运行：

```powershell
# 文档约定的云数据库部署
./scripts/deploy-kind.ps1 -DatabaseMode Azure
# 没有 Azure 配置时的本地验证分支
./scripts/deploy-kind.ps1 -DatabaseMode Local
```

脚本创建名为 second-space 的 kind 集群、显式指定 kind-second-space context；从 .env 直接构造 Secret 并通过标准输入传给 kubectl，不写出含密钥的清单；构建并载入两个镜像，部署 PVC、API、Nginx 与 Service，等待 rollout 并检查 health。

本地数据库模式额外部署 PostgreSQL StatefulSet/PVC。Azure 模式不部署本地数据库，后端连接 .env 指定的 Azure 服务。kind 的端口与 Compose 都是 5623，演示时二选一。

```powershell
kubectl --context kind-second-space -n second-space get pods,pvc,services
kubectl --context kind-second-space -n second-space logs deployment/backend --tail=80
```

修改代码后重新运行部署脚本，镜像重建、载入、重启；PVC 保留。删除 kind 集群会移除其中的本地卷，需要提前另做数据库和图片备份。

## 6. 验证与协作

测试仅使用名称含 secondspace_test 的隔离数据库。创建该数据库后：

```powershell
.venv/Scripts/python.exe -m pytest backend/tests -q
npm test --prefix frontend
npm run build --prefix frontend
# 对全新的演示数据库运行真实浏览器完整流程；会生成 E2E 测试订单和政策。
node frontend/tests/api-flow.mjs
```

仓库附 GitHub Actions CI：PostgreSQL service、Python API 测试、前端规则测试与构建。PR 提交前检查 `.env`、`.runtime`、附件中的原始凭据均未进入 Git。当前分支名为 feat/python-langgraph-backend。建议由另一位组员按 PR 模板复核并合并。

参考：[Azure TLS](https://learn.microsoft.com/en-us/azure/postgresql/security/security-tls-how-to-connect)、[LangGraph interrupt/resume](https://docs.langchain.com/oss/python/langgraph/interrupts)、[LangChain ChatOpenAI 兼容服务配置](https://docs.langchain.com/oss/python/integrations/chat/openai)。
