# 本次验证记录 · 2026-10-22

## 已实测

- Python 3.12.15；本机独立 PostgreSQL 17，loopback 55432。
- 后端 17 项测试通过，使用隔离的 secondspace_test 数据库和显式模型 fixture。
- 前端原规则 23 项测试通过；Vite production build 通过。
- Edge headless 完整网页流程通过：卖家上架、推荐、Visa、物业回复、取货、送达、验收自动结算、卖家明细、管理员政策、BPAY。
- 两个独立浏览器 context：物业提交后买家轮询收到更新；英文字段名正确；买家时间线无 Agent 名称，管理员可见；管理员无待结算。
- 真实 HEIC 样本解码；正好 15 MiB 接收；15 MiB + 1 字节拒绝；无效文件拒绝。
- 两个并发购买请求仅一个成功；重复验收只生成一笔结算；非法操作不提交业务状态。
- PostgreSQL LangGraph checkpoint 可用新 graph 实例读取并恢复人工处理；已完成的政策不改变固定买家总价。
- 实际重启 API 后，11 条现有演示订单的 ID、状态、结算标识保持一致。
- 部署 YAML 可解析；PowerShell 部署脚本语法解析通过。
- Git 跟踪文件扫描：未包含文档中的模型密钥、私有 .env 或 .runtime 数据。

## 真实模型证据与限制

- campus-qwen 文本调用曾成功提取 `绿色、布艺、双人、扶手`。
- 也观察到空偏好结果；当前版本对已有关键词但模型返回空值的情况使用明确记录的 keyword_fallback_empty。
- 图片请求遇到 OpenAIRateLimitError，真实视觉审核尚未通过验收；不能把演示照片或 fixture 的通过视为真实图片审核证据。
- 模型可达性会随校园网络/服务配额变化，health 只检查数据库，不宣称模型健康。

## 尚未实测的外部步骤

- Azure PostgreSQL：未收到 Azure 资源/连接配置，本次运行的是本地 PostgreSQL。
- Docker/kind：本机缺少容器引擎、kind、kubectl，已准备 Dockerfile、Compose、Kubernetes/PVC/Secret 和部署脚本，尚未运行 rollout。
- GitHub：仓库可克隆，但非交互推送检查无可用登录凭据。改动保存在本地开发分支，未推送、未创建 PR、未独立审核。

原 5621 前端和旧浏览器数据保留；新版预览为 5622。
