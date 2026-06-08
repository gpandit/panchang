import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@pandit/api-client-ts", "@pandit/design-tokens"],
};

export default nextConfig;
