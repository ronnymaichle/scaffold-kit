import { NextResponse } from "next/server";
import { db } from "@/lib/firebase-admin";
import { getUserFromSession } from "@/lib/session";

export async function DELETE(request: Request, { params }: { params: { id: string } }) {
  const user = await getUserFromSession(request);
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  await db.collection("photos").doc(params.id).delete();
  return NextResponse.json({ ok: true });
}
