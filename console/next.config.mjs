/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Odoo è raggiunto server-side (route handlers / server components): nessun segreto al client.
};

export default nextConfig;
