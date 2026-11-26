import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: [
    "@agentvoice/shared-types",
    "@agentvoice/config",
    "@agentvoice/ui",
  ],
};

export default nextConfig;
