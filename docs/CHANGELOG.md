# RehabFlow 版本记录

## v0.1.0（2026-08-06）— 首个可用版本

RehabFlow（康复流程流）首个对外版本：院内康复治疗排课与执行管理系统。
**里程碑 M1–M3 全量交付，已公网部署（AutoDL/seetacloud）稳定运行。**

### 核心能力

| 模块 | 能力 |
| :--- | :--- |
| **排课引擎** | 资源树（房间/康复师/患者）→ 待排池 → 排课日历（拖拽）→ 冲突检测（患者/康复师/房间三重冲突 + 时区统一） |
| **课程执行** | 软打卡状态机（待开始 → 已提醒 → 进行中 → 已完成/已逾期）、定位校验、站内信通知 |
| **主任看板** | KPI 聚合、患者 360° 视图、康复师工作量、课程趋势、异常预警 |
| **消息通知** | 课前 15 分钟提醒、超时 5 分钟提醒、30 分钟巡检、站内信 |
| **认证体系** | 注册/登录/退出登录/忘记密码（手机号+验证码）/修改密码；JWT access+refresh（jti 唯一）；RBAC 四角色（患者/康复师/医生/管理员） |

### 技术栈

- **前端**：Next.js 16.3（App Router + RSC + proxy.ts 路由守卫 + rewrites 同源代理）、Tailwind v4（CSS-first）、shadcn/ui 风格、TanStack Query v5
- **后端**：FastAPI（Pydantic v2）+ SQLAlchemy 2.x async + Alembic + APScheduler + uvicorn
- **数据**：SQLite（开发/轻量部署）→ PostgreSQL 16（生产可迁移，asyncpg）
- **部署**：双方案 —— 方案 A 常规（systemd + nginx + conda 一键脚本）/ 方案 B Docker Compose（含独立 scheduler 服务）；AutoDL 容器适配脚本（端口映射 + 数据盘构建绕 overlayfs SIGBUS）

### 质量数据

- 后端 pytest：**119/119 全绿**（M1 验收 28 + M2 验收 31 + M3 验收 37 + 认证增强 5 + 修复回归）
- 前端构建：**26/26 路由**通过（Next.js 16 Turbopack）
- 演示账号：`admin / admin123`

### 公网部署（AutoDL/seetacloud）

```
前端页面:  https://uu372683-8934-fb822b68.westc.seetacloud.com:8443
后端 API:  https://u372683-8934-fb822b68.westc.seetacloud.com:8443  （/docs 接口文档）
```

### 关键修复（本版本内）

- Next.js 16 dev 跨源 JS 拦截（127.0.0.1/局域网 IP 登录无反应）→ `allowedDevOrigins` + 同源代理
- 注册字段契约不一致（full_name vs display_name）→ 统一 `display_name`
- 手机号必填（前后端一致校验：`^1\d{10}$`）
- 多 worker 下调度器重复执行 → `RUN_SCHEDULER` 独立开关 + 独立 scheduler 服务
- overlayfs Bus error（AutoDL 容器前端构建崩溃）→ 数据盘（/root/autodl-tmp）构建
- PYTHONPATH 污染（子进程加载旧代码）→ start_dev.py `clean_env()`

### 版本说明

- 短信验证码：院内系统暂无短信通道，验证码写入后端日志 + `dev_code` 字段返回；生产接入短信服务商后移除 `dev_code` 并改为短信下发
- LICENSE：暂缓添加（README 保持「待定」）
- 已知限制：软打卡定位基于 IP/坐标简化实现，未接硬件定位
