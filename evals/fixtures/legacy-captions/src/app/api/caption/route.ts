import { NextResponse } from "next/server";

export async function POST(request: Request) {
  const { imageUrl } = await request.json();
  const response = await fetch("https://api.example-ai.test/v1/captions", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.AI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({ image_url: imageUrl }),
  });
  const { caption } = await response.json();
  return NextResponse.json({ caption });
}
