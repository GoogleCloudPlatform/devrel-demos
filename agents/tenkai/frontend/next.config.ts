import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true,
  },
  // Rewrites don't work in export mode, API calls must be to same domain
  // or handled via CORS/Proxy.
  // Since we are merging containers, API will be at /api/ on same host.
};

export default nextConfig;

