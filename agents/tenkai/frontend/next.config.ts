import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/experiments/:path*',
        destination: 'http://127.0.0.1:8080/api/experiments/:path*',
      },
      {
        source: '/api/runs/:path*',
        destination: 'http://127.0.0.1:8080/api/runs/:path*',
      },
      {
        source: '/api/scenarios/:path*',
        destination: 'http://127.0.0.1:8080/api/scenarios/:path*',
      },
      {
        source: '/api/templates/:path*',
        destination: 'http://127.0.0.1:8080/api/templates/:path*',
      },
      {
        source: '/api/health',
        destination: 'http://127.0.0.1:8080/api/health',
      },
    ];
  },
};

export default nextConfig;

