import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /**
   * 允许的开发来源（dev 模式跨源 JS 加载白名单）：
   * 防止 Next.js dev server 拦截 127.0.0.1 / 局域网 IP 访问时
   * 的 JS chunk 加载（否则 React 不 hydration，登录无反应）。
   */
  allowedDevOrigins: ["127.0.0.1", "localhost", "10.2.27.189"],

  /**
   * API 同源代理（根治跨域）：
   * 前端统一请求 /api/*（同源），Next.js 服务端转发到后端 8000。
   * 无论用户用 localhost / 127.0.0.1 / 局域网 IP 访问，都不再触发浏览器跨域拦截。
   */
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.BACKEND_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
