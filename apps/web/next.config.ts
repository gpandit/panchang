import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@pandit/api-client-ts", "@pandit/design-tokens"],
  // Required for the Docker standalone build (copies only runtime files)
  output: "standalone",
};

export default nextConfig;
