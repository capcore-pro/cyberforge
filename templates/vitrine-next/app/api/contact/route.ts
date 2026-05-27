import { NextResponse } from "next/server";
import { z } from "zod";

const contactSchema = z.object({
  name: z.string().min(2).max(120),
  email: z.string().email().max(200),
  message: z.string().min(10).max(5000),
});

/**
 * Stub Phase 4.2a — sera branché sur CyberForge / Brevo en 4.2d.
 */
export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "Corps JSON invalide." },
      { status: 400 },
    );
  }

  const parsed = contactSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { detail: "Vérifiez les champs du formulaire." },
      { status: 422 },
    );
  }

  const backendBase =
    process.env.VITRINE_BACKEND_URL ??
    process.env.DEMO_API_BASE_URL ??
    "https://cyberforge-backend-production.up.railway.app";

  const siteUrl =
    request.headers.get("origin") ??
    request.headers.get("referer") ??
    null;

  const res = await fetch(`${backendBase.replace(/\/$/, "")}/api/vitrine/contact`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...parsed.data, site: siteUrl }),
    // avoid caching POST in edge environments
    cache: "no-store",
  });

  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { detail: typeof payload.detail === "string" ? payload.detail : "Envoi impossible." },
      { status: 502 },
    );
  }

  return NextResponse.json({ ok: true, ...payload });
}
