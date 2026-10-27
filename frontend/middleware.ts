import { type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/middleware";

// Deployed service origins (Render/Railway/R2) must be allowed explicitly,
// otherwise the browser blocks every API call once the app leaves localhost.
const serviceOrigins = [
  process.env.NEXT_PUBLIC_API_URL,
  process.env.NEXT_PUBLIC_GRAPH_API_URL,
  process.env.NEXT_PUBLIC_BIOMETRICS_API_URL,
  process.env.NEXT_PUBLIC_MEDIA_ORIGIN,
]
  .map((url) => {
    try {
      return url ? new URL(url).origin : null;
    } catch {
      return null;
    }
  })
  .filter((origin): origin is string => Boolean(origin))
  .join(" ");

const devOrigins = process.env.NODE_ENV === "production" ? "" : "http://localhost:* http://127.0.0.1:*";

export async function middleware(request: NextRequest) {
  const res = await updateSession(request);

  // Security headers
  res.headers.set("X-Frame-Options", "DENY");
  res.headers.set("X-Content-Type-Options", "nosniff");
  res.headers.set(
    "Strict-Transport-Security",
    "max-age=63072000; includeSubDomains; preload"
  );
  res.headers.set(
    "Content-Security-Policy",
    [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
      "style-src 'self' 'unsafe-inline'",
      `connect-src 'self' https://accounts.google.com https://*.supabase.co wss://*.supabase.co ${serviceOrigins} ${devOrigins}`,
      "frame-src https://accounts.google.com",
      `img-src 'self' data: blob: https: ${devOrigins}`,
      `media-src 'self' blob: https: ${devOrigins}`,
    ].join("; ")
  );

  return res;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
