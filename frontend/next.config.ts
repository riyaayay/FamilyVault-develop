import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  // Required for the production Docker image (copies a minimal server.js + deps).
  // Without this, the Dockerfile's standalone runner stage has nothing to run.
  output: "standalone",
}

export default nextConfig
