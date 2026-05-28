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

  const body = (await req.json()) as {
    current_password?: string;
    new_password?: string;
  };

  const r = await fetch(
    `${backend}/api/vitrines/${encodeURIComponent(slug)}/auth/change-password`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    },
  );

  const data = (await r.json()) as { ok?: boolean; detail?: string };
  if (!r.ok) {
    return NextResponse.json(
      { ok: false, message: data?.detail || "Erreur." },
      { status: r.status },
    );
  }
  return NextResponse.json({ ok: Boolean(data.ok) });
}

