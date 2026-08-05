# RehabFlow 页面结构与信息架构

- 版本：v0.1（初始规划）
- 配套文档：`design-system.md`（设计 token）、`components.md`（页面级组件）
- 技术基座：Next.js App Router，路由按角色分组 `(auth)` / `(patient)` / `(therapist)` / `(admin)` / `(doctor)`

> 路由守卫规则：`proxy.ts`（Next.js 16 中 middleware 的正式名称）校验 access token 与角色；未登录访问受保护路由 → 跳 `/login`；角色不匹配 → 跳 `/403` 或对应角色首页。

---

## 1. 站点地图（Sitemap）

```
/
├── (auth)
│   ├── /login                        登录
│   ├── /register                     注册（含角色选择）
│   └── /onboarding                   档案完善（按角色分流，规划）
│
├── (patient)  患者端  [需要 patient 角色]
│   ├── /patient                      首页（我的课程概览 + 今日提醒）
│   ├── /patient/schedule             我的课程安排（周历）
│   └── /patient/profile              个人档案（含主管医生/责任康复师）
│
├── (therapist)  康复师端  [需要 therapist 角色]
│   ├── /therapist/schedule           我的课表（核心，日程清单式）★
│   ├── /therapist/patients           我的患者列表
│   ├── /therapist/patients/[id]      患者 360° 视图（共享）
│   ├── /therapist/assessments        评估记录（填写/查看）
│   ├── /therapist/messages           消息
│   └── /therapist/profile            个人档案
│
├── (admin)  管理端  [需要 admin 角色]
│   ├── /admin/scheduler              排课日历（核心排课引擎）★
│   ├── /admin/dashboard              主任数据看板 ★
│   ├── /admin/rooms                  治疗室资源管理
│   ├── /admin/therapists             康复师管理（组别/排班）
│   ├── /admin/alerts                 异常预警处理（看板预警的落地页）
│   └── /admin/audit                  审计日志
│
├── (doctor)  医生端  [需要 doctor 角色，新增]
│   ├── /doctor/patients              我的患者列表
│   ├── /doctor/patients/[id]         患者 360° 视图（核心）★
│   └── /doctor/messages              消息
│
└── 全局
    ├── /404                          页面不存在
    ├── /403                          无权限
    └── /500                          服务器错误
```

> ★ = V2 核心页面。`(doctor)` 为新增角色组；若首期不做独立医生端，医生可复用患者 360 页面 + 权限位控制（见 PRD §7）。

---

## 2. 全局布局（Layout）

### 2.1 认证布局（(auth)）

- 居中卡片布局：左半品牌区（桌面端）/ 顶部品牌（移动端），右半表单区。
- 卡片：宽 440px，`rounded-lg shadow-lg bg-white p-8`。
- 元素顺序：Logo → 页面标题 → 副标题 → 表单 → 底部跳转链接。

### 2.2 应用布局（患者/康复师/医生）

- 桌面端（≥1024px）：左侧 Sidebar 240px（导航）+ 右侧主内容区；顶部 Topbar 64px（品牌 / 页面标题 / 通知铃铛 + 头像菜单）。
- 移动端（<1024px）：Topbar 56px（汉堡菜单）+ 底部 TabBar（首页/课表/消息/我的）；主内容底部预留 72px。

### 2.3 管理端布局（排课/看板）

- 桌面优先：左侧 Sidebar 240px + Topbar + 内容区；内容区 `max-w-[1400px] mx-auto`。
- **排课日历页例外**：内容区全宽（无 max-width 限制），时间轴网格自适应撑满，最大化可视排课区域。

---

## 3. 页面路由与角色对照

| 路由 | 角色 | 页面 |
| :--- | :--- | :--- |
| `/admin/scheduler` | admin | 排课日历 |
| `/admin/dashboard` | admin | 主任看板 |
| `/therapist/schedule` | therapist | 我的课表 |
| `/doctor/patients/[id]` | doctor / therapist | 患者 360° |
| `/patient/schedule` | patient | 我的课程安排 |
| `/therapist/patients` | therapist | 我的患者 |
| `/admin/rooms` | admin | 治疗室管理 |
| `/admin/alerts` | admin | 异常预警处理 |

---

## 4. 导航信息架构

### 4.1 康复师侧边栏

```
我的课表        ← 默认落地页
我的患者
评估记录
消息
个人档案
```

### 4.2 管理端侧边栏

```
排课日历        ← 默认落地页（排课管理员）
主任看板
治疗室管理
康复师管理
异常预警        ← 有未处理预警时显示红点角标
审计日志
```

### 4.3 医生侧边栏

```
我的患者        ← 默认落地页
消息
```

---

## 5. 页面优先级（MVP 范围）

| 优先级 | 页面 | 说明 |
| :--- | :--- | :--- |
| P0 | `/admin/scheduler` 排课日历 | 核心引擎，M2 |
| P0 | `/therapist/schedule` 我的课表 | 核心执行，M2 |
| P0 | `/doctor/patients/[id]` 患者 360° | 位置可视化，M3 |
| P1 | `/admin/dashboard` 主任看板 | 决策层，M3 |
| P1 | `/patient/schedule` 患者课程安排 | 患者可见性，M2 尾 |
| P2 | `/admin/rooms`、`/admin/alerts` | 支撑管理，M3 |
