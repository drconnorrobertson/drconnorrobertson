import { NextResponse } from "next/server";
import { Phorest, PhorestClientError } from "@/lib/phorest";
import { isAuthed } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET() {
  if (!(await isAuthed())) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  try {
    const branches = await new Phorest().listBranches();
    return NextResponse.json({ branches });
  } catch (err) {
    if (err instanceof PhorestClientError) {
      return NextResponse.json(
        { error: err.message, status: err.status },
        { status: 502 },
      );
    }
    throw err;
  }
}
