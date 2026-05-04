import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@pinky/contracts", "@pinky/design-system"],
};

export default nextConfig;
