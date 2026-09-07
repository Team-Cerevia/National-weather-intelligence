import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // maplibre-gl worker threads require webpack (Turbopack incompatible with import.meta.url)
};

export default nextConfig;

