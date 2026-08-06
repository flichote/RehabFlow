# ============================================================
# RehabFlow 前端镜像 — Next.js 16 standalone + Nginx（对外 80）
# 构建：docker build -f docker/frontend.Dockerfile -t rehabflow-frontend .
# 说明：Next.js standalone 输出自包含 Node 服务，nginx 做静态托管 + /api 反代
# ============================================================

# ---------- 构建阶段 ----------
FROM node:22-alpine AS builder

WORKDIR /app

# 依赖层（缓存友好）
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

# 源码
COPY frontend/ .

# 生产构建（standalone 输出）
# 注意：构建期不需要 NEXT_PUBLIC_API_URL——前端统一走同源 /api（nginx 反代），
# 天然适配任意对外域名/IP，无需构建期注入环境变量。
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- 运行阶段（nginx 托管 + 反代） ----------
FROM nginx:1.27-alpine

# 从 builder 提取 standalone 产物
COPY --from=builder /app/.next/standalone /app
COPY --from=builder /app/.next/static /app/.next/static
COPY --from=builder /app/public /app/public

# nginx 配置：静态 + 健康检查 + /api 反代后端
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
