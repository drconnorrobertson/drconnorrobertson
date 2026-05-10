import { NextResponse } from "next/server";
import { signIn, signOut } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const body = (await req.json().catch(() => ({}))) as {
    password?: string;
    action?: "in" | "out";
  };
  if (body.action === "out") {
    await signOut();
    return NextResponse.json({ ok: true });
  }
  const ok = await signIn(body.password ?? "");
  return NextResponse.json({ ok }, { status: ok ? 200 : 401 });
}
