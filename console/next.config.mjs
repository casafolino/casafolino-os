/** @type {import('next').NextConfig} */
// basePath e standalone guidati da env: dev locale resta a "/", il deploy
// stage gira sotto /console dietro nginx. Odoo è raggiunto SOLO server-side.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  ...(basePath ? { basePath } : {}),
};

export default nextConfig;
