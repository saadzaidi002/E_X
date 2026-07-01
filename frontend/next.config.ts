import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // @ts-ignore - Some next versions type this differently
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
};

export default nextConfig;
