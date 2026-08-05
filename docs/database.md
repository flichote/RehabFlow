# RehabFlow 数据模型设计

- 版本：v0.1（设计蓝图，未建表）
- 状态：待评审
- 配套文档：`architecture.md`（架构）、`api.md`（接口）、`PRD.md`（需求）
- 对应交付物：`Database_ER图.vsdx`（规划产出）

> 设计原则：
> 1. **状态日志即事实**——患者位置/状态用日志表存储（天然审计），当前态=最近一条日志。
> 2. **课程是核心实体**——一切排课/执行/统计围绕 `courses`。
> 3. **枚举用字符串常量**，不加额外表（组别 PT/OT/ST、状态枚举等）。
> 4. 时间一律 `TIMESTAMPTZ`（UTC 存储，前端本地化展示）；时间粒度 15 分钟。

---

## 1. 表清单总览（15 张核心表）

| # | 表名 | 中文名 | 分类 |
| :--- | :--- | :--- | :--- |
| 1 | `users` | 用户 | 基础 |
| 2 | `patients` | 患者档案 | 基础 |
| 3 | `therapists` | 康复师档案 | 基础 |
| 4 | `doctors` | 主管医生档案 | 基础 |
| 5 | `rooms` | 治疗室 | 资源 |
| 6 | `courses` | 课程实例 ★ | 业务核心 |
| 7 | `course_status_log` | 课程状态流转 | 业务 |
| 8 | `patient_status_log` | 患者状态/位置流转 ★ | 业务 |
| 9 | `therapist_shifts` | 康复师排班/出勤 | 业务 |
| 10 | `assessments` | 评估记录 | 业务 |
| 11 | `assessment_templates` | 评估量表定义 | 配置 |
| 12 | `notifications` | 消息提醒 | 业务 |
| 13 | `alerts` | 异常预警 | 业务 |
| 14 | `audit_log` | 审计日志 | 支撑 |
| 15 | `refresh_tokens` | 刷新令牌 | 支撑 |

---

## 2. 表结构明细

### 2.1 `users` 用户

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| username | VARCHAR(64) | UNIQUE, NOT NULL | 登录名 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt |
| role | VARCHAR(20) | NOT NULL | `patient` / `therapist` / `doctor` / `admin` |
| display_name | VARCHAR(64) | NOT NULL | 显示名 |
| phone | VARCHAR(20) | NULL | 可选短信通道 |
| is_active | BOOLEAN | DEFAULT true | 禁用标记 |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

> 索引：`uk_users_username`、`idx_users_role`。

### 2.2 `patients` 患者档案

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users, UNIQUE | 登录账号 |
| name | VARCHAR(64) | NOT NULL | |
| gender | VARCHAR(8) | NULL | 男/女 |
| age | INT | NULL | |
| diagnosis | VARCHAR(255) | NULL | 诊断 |
| admission_date | DATE | NULL | 入院日期 |
| ward_location | VARCHAR(128) | NULL | 病房位置（如"住院部3楼5床"） |
| doctor_id | BIGINT | FK→doctors, NULL | 主管医生 |
| therapist_id | BIGINT | FK→therapists, NULL | 责任康复师 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'ward' | 患者状态枚举（见下） |
| external_patient_no | VARCHAR(64) | NULL | **HIS 患者号（备用冗余，不参与业务逻辑）**：仅作将来 CSV 导入对账参考；RehabFlow 一切业务以本表 id 为准（见 architecture §9.4） |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**患者状态枚举**：`ward`(病房) / `en_route`(前往途中) / `treating`(治疗中) / `paused`(临时暂停) / `absent`(旷课缺席) / `discharged`(出院)。

> 索引：`idx_patients_doctor_id`、`idx_patients_therapist_id`、`idx_patients_status`。

### 2.3 `therapists` 康复师档案

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users, UNIQUE | |
| name | VARCHAR(64) | NOT NULL | |
| group_name | VARCHAR(10) | NOT NULL | `PT` / `OT` / `ST` |
| title | VARCHAR(64) | NULL | 职称 |
| certified | BOOLEAN | DEFAULT false | 资质审核 |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### 2.4 `doctors` 主管医生档案

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users, UNIQUE | |
| name | VARCHAR(64) | NOT NULL | |
| department | VARCHAR(64) | NULL | 科室 |
| title | VARCHAR(64) | NULL | 职称 |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### 2.5 `rooms` 治疗室

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| name | VARCHAR(64) | NOT NULL, UNIQUE | 如"PT大厅"、"PT-1室" |
| room_type | VARCHAR(10) | NOT NULL | `PT` / `OT` / `ST` |
| capacity | INT | DEFAULT 1 | 容量（是否做容量管理 TBD，PRD §9） |
| is_active | BOOLEAN | DEFAULT true | |

### 2.6 `courses` 课程实例 ★

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK→patients, NOT NULL | |
| therapist_id | BIGINT | FK→therapists, NOT NULL | |
| room_id | BIGINT | FK→rooms, NOT NULL | |
| course_type | VARCHAR(10) | NOT NULL | `PT` / `OT` / `ST`（与 room 类型一致） |
| start_at | TIMESTAMPTZ | NOT NULL | 计划开始（15min 粒度） |
| end_at | TIMESTAMPTZ | NOT NULL | 计划结束 |
| status | VARCHAR(20) | NOT NULL DEFAULT 'scheduled' | 课程状态枚举（见下） |
| actual_start_at | TIMESTAMPTZ | NULL | 实际开始（点"开始上课"） |
| actual_end_at | TIMESTAMPTZ | NULL | 实际结束（点"结束上课"） |
| minutes_consumed | INT | NULL | 课时消耗（实际时长，向上取整 15min，TBD） |
| session_note | TEXT | NULL | 治疗记录（内容/反应/下次注意事项） |
| created_by | BIGINT | FK→users | 排课人 |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

**课程状态枚举**：`scheduled`(待执行) / `reminded`(提醒已发) / `ongoing`(进行中) / `completed`(已完成) / `leave`(未完成-请假) / `absent`(未完成-缺席) / `abnormal`(异常)。

> **冲突检测索引**：`idx_courses_patient_time (patient_id, start_at, end_at)`、`idx_courses_therapist_time (therapist_id, start_at, end_at)`——事务内 FOR UPDATE 依赖。

### 2.7 `course_status_log` 课程状态流转

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| course_id | BIGINT | FK→courses, NOT NULL | |
| from_status | VARCHAR(20) | NULL | |
| to_status | VARCHAR(20) | NOT NULL | |
| actor_id | BIGINT | FK→users, NULL | 操作人（系统动作=null） |
| note | VARCHAR(255) | NULL | 备注 |
| occurred_at | TIMESTAMPTZ | DEFAULT now() | |

### 2.8 `patient_status_log` 患者状态/位置流转 ★

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK→patients, NOT NULL | |
| from_status | VARCHAR(20) | NULL | |
| to_status | VARCHAR(20) | NOT NULL | |
| location | VARCHAR(128) | NULL | 位置快照（如"PT大厅2号床"） |
| actor_id | BIGINT | FK→users, NULL | 触发人（康复师/医生/系统） |
| source | VARCHAR(20) | NOT NULL | `course_action` / `manual_fix` / `system` |
| occurred_at | TIMESTAMPTZ | DEFAULT now() | |

> **当前状态查询**：`SELECT ... ORDER BY occurred_at DESC LIMIT 1`（或物化到 patients.status 冗余字段，双写）。
> 索引：`idx_patient_status_log_patient (patient_id, occurred_at DESC)`。

### 2.9 `therapist_shifts` 康复师排班/出勤

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| therapist_id | BIGINT | FK→therapists, NOT NULL | |
| work_date | DATE | NOT NULL | |
| start_time | TIME | NOT NULL | |
| end_time | TIME | NOT NULL | |
| status | VARCHAR(20) | DEFAULT 'scheduled' | `scheduled` / `on_duty` / `absent` / `leave` |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

> UNIQUE：`uk_shifts (therapist_id, work_date)`。出勤率 = on_duty / scheduled。

### 2.10 `assessments` 评估记录

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| patient_id | BIGINT | FK→patients, NOT NULL | |
| template_id | BIGINT | FK→assessment_templates | |
| assess_type | VARCHAR(64) | NOT NULL | 冗余类型名（Fugl-Meyer / Barthel…） |
| score | NUMERIC(6,2) | NULL | 评分 |
| detail | JSONB | NULL | 分项明细 |
| assessor_id | BIGINT | FK→users | 评估人（康复师） |
| assessed_at | TIMESTAMPTZ | NOT NULL | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### 2.11 `assessment_templates` 评估量表定义

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| name | VARCHAR(64) | NOT NULL, UNIQUE | 量表名 |
| category | VARCHAR(32) | NULL | 分类 |
| max_score | NUMERIC(6,2) | NULL | 满分 |
| fields | JSONB | NULL | 分项字段定义 |
| is_active | BOOLEAN | DEFAULT true | |

### 2.12 `notifications` 消息提醒

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users, NOT NULL | 接收人 |
| type | VARCHAR(32) | NOT NULL | `course_new` / `course_change` / `course_reminder` / `course_overdue` / `assessment_todo` / `alert` |
| title | VARCHAR(128) | NOT NULL | |
| content | TEXT | NOT NULL | 模板渲染后文本 |
| link | VARCHAR(255) | NULL | 跳转路由 |
| is_read | BOOLEAN | DEFAULT false | |
| channel | VARCHAR(20) | DEFAULT 'inbox' | `inbox` / `browser` / `sms` |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

> 索引：`idx_notifications_user (user_id, is_read, created_at DESC)`。

### 2.13 `alerts` 异常预警

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| alert_type | VARCHAR(32) | NOT NULL | `course_overdue` / `patient_absent` / `conflict_unresolved` |
| ref_course_id | BIGINT | FK→courses, NULL | 关联课程 |
| ref_patient_id | BIGINT | FK→patients, NULL | 关联患者 |
| summary | VARCHAR(255) | NOT NULL | 摘要 |
| status | VARCHAR(20) | DEFAULT 'open' | `open` / `resolved` / `ignored` |
| resolved_by | BIGINT | FK→users, NULL | |
| resolved_at | TIMESTAMPTZ | NULL | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

> 索引：`idx_alerts_status (status, created_at DESC)`。

### 2.14 `audit_log` 审计日志

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| actor_id | BIGINT | FK→users, NULL | 操作人 |
| action | VARCHAR(64) | NOT NULL | 如 `course.force_replace` / `patient.location_fix` |
| entity_type | VARCHAR(32) | NOT NULL | `course` / `patient` / `alert`… |
| entity_id | BIGINT | NULL | |
| detail | JSONB | NULL | 变更前后快照 |
| ip | VARCHAR(45) | NULL | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

### 2.15 `refresh_tokens` 刷新令牌

| 字段 | 类型 | 约束 | 说明 |
| :--- | :--- | :--- | :--- |
| id | BIGSERIAL | PK | |
| user_id | BIGINT | FK→users, NOT NULL | |
| token_hash | VARCHAR(128) | NOT NULL, UNIQUE | SHA-256 |
| expires_at | TIMESTAMPTZ | NOT NULL | |
| revoked | BOOLEAN | DEFAULT false | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |

---

## 3. ER 关系速览

```text
users 1─1 patients            users 1─1 therapists          users 1─1 doctors
patients N─1 doctors           patients N─1 therapists
patients 1─N courses           therapists 1─N courses       rooms 1─N courses
courses 1─N course_status_log  patients 1─N patient_status_log
patients 1─N assessments       assessment_templates 1─N assessments
therapists 1─N therapist_shifts
users 1─N notifications        courses/patients N─1 alerts
```

## 4. 冲突检测 SQL 模板（实现参照）

```sql
-- 患者冲突（事务内）
SELECT id FROM courses
WHERE patient_id = :pid
  AND status NOT IN ('completed','leave','absent')
  AND start_at < :new_end AND end_at > :new_start
FOR UPDATE;

-- 康复师冲突（事务内）
SELECT id FROM courses
WHERE therapist_id = :tid
  AND status NOT IN ('completed','leave','absent')
  AND start_at < :new_end AND end_at > :new_start
FOR UPDATE;
```

## 5. TBD（影响表结构的开放问题）

1. 课时消耗向上取整规则（15min？）→ 影响 `minutes_consumed` 计算。
2. 治疗室容量管理是否一期做 → 影响 courses 是否加 `capacity` 校验。
3. 患者 status 冗余字段（patients.status）与日志表是否双写 → 影响一致性设计。
4. 康复师排班模块是否独立（还是看板直接统计出勤）。
