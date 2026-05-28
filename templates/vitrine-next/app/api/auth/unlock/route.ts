import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const backend = process.env.VITRINE_BACKEND_URL;
  const slug = process.env.NEXT_PUBLIC_VITRINE_SLUG;
  if (!backend || !slug) {
    return NextResponse.json(
      { ok: false, message: "Configuration manquante." },
      { status: 500 },
    );
  }

  const body = (await req.json()) as { password?: string };
  const password = (body?.password || "").trim();
  if (!password) {
    return NextResponse.json(
      { ok: false, message: "Mot de passe requis." },
      { status: 400 },
    );
  }

  const r = await fetch(`${backend}/api/vitrines/${encodeURIComponent(slug)}/auth/unlock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    cache: "no-store",
  });
  const data = (await r.json()) as { ok?: boolean };
  if (!r.ok || !data.ok) {
    return NextResponse.json({ ok: false, message: "Mot de passe invalide." }, { status: 401 });
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.set("vf_unlocked", "1", {
    httpOnly: true,
    sameSite: "lax",
    secure: true,
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
  return res;
}

