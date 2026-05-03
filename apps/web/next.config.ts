import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@pinky/contracts", "@pinky/design-system"],
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
