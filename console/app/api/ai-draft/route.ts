// POST /api/ai-draft → genera bozza AI via Groq (server). Nessun segreto al client.
import { NextResponse } from "next/server";
import { generateAiDraft } from "@/lib/ai";

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as { subject?: string; body?: string; instruction?: string; partnerName?: string };
    const out = await generateAiDraft({
      subject: body.subject ?? "",
      body: body.body ?? "",
      instruction: body.instruction,
      partnerName: body.partnerName,
    });
    return NextResponse.json(out);
  } catch (e) {
    return NextResponse.json({ error: (e as Error).message }, { status: 500 });
  }
}
