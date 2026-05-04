const FAVICON_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="pinkyGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f472b6" />
      <stop offset="100%" stop-color="#a78bfa" />
    </linearGradient>
  </defs>
  <rect width="64" height="64" rx="18" fill="#0b0a12" />
  <rect x="3" y="3" width="58" height="58" rx="15" fill="none" stroke="url(#pinkyGlow)" stroke-width="3" />
  <path d="M21 18h14c8 0 13 4.7 13 11.6 0 7.2-5.4 11.9-13.9 11.9H28V50h-7V18Zm12 18.1c5.1 0 8-2.1 8-6.1 0-3.8-2.8-5.8-7.8-5.8H28v11.9h5Z" fill="#f4f0ff" />
</svg>
`.trim();

export async function GET(): Promise<Response> {
  return new Response(FAVICON_SVG, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  });
}
