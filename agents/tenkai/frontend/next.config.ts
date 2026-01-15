import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  // rewrites are ignored in export mode, but valid for dev
  // rewrites are ignored in export mode, but valid for dev
  // async rewrites() {
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: 'http://127.0.0.1:8080/api/:path*',
  //     },
  //   ];
  // },
};

export default nextConfig;

