import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: [
    "192.168.1.132",
    "http://192.168.1.132:3000",
  ],
};

export default nextConfig;