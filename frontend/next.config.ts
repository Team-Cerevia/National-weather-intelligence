import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // maplibre-gl worker threads require webpack (Turbopack incompatible with import.meta.url)
};

export default nextConfig;

