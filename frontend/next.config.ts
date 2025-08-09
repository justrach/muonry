import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Allow optimized images from our CDN domain
    domains: ["images.muonry.com"],
    // Alternatively, remotePatterns offer finer control:
    // remotePatterns: [{ protocol: "https", hostname: "images.muonry.com" }],
  },
};

export default nextConfig;
