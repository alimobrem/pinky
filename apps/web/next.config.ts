import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@pinky/contracts", "@pinky/design-system"],
};

export default nextConfig;
