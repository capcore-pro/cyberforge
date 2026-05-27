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

  // Phase 4.2d : proxy vers backend CyberForge + Brevo
  console.info("[contact] message reçu (stub)", {
    name: parsed.data.name,
    email: parsed.data.email,
    messageLength: parsed.data.message.length,
  });

  return NextResponse.json({ ok: true, recorded: true });
}
