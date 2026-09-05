import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to web/ so Next stops hunting for stray lockfiles
  // (the repo root carries an unrelated package-lock.json).
  turbopack: { root: __dirname },
};

export default nextConfig;
