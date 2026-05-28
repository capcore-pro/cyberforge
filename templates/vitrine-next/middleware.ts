import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const COOKIE_NAME = "vf_unlocked";

function allowedPath(pathname: string): boolean {
  return (
    pathname.startsWith("/auth") ||
    pathname.startsWith("/api/auth") ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon") ||
    pathname.startsWith("/robots.txt") ||
    pathname.startsWith("/sitemap")
  );
}

export async function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (allowedPath(pathname)) return NextResponse.next();

  const unlocked = req.cookies.get(COOKIE_NAME)?.value === "1";
  if (unlocked) return NextResponse.next();

  const backend = process.env.VITRINE_BACKEND_URL || process.env.NEXT_PUBLIC_VITRINE_BACKEND_URL;
  const slug = process.env.NEXT_PUBLIC_VITRINE_SLUG;
  if (!backend || !slug) return NextResponse.next(); // fail-open

  try {
    const r = await fetch(`${backend}/api/vitrines/${encodeURIComponent(slug)}/auth/status`, {
      headers: { "User-Agent": "CyberForge/vitrine-middleware" },
      cache: "no-store",
    });
    if (!r.ok) return NextResponse.next();
    const data = (await r.json()) as { enabled?: boolean };
    if (!data?.enabled) return NextResponse.next();
  } catch {
    return NextResponse.next();
  }

  const url = req.nextUrl.clone();
  url.pathname = "/auth";
  url.searchParams.set("next", pathname + (search || ""));
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};

