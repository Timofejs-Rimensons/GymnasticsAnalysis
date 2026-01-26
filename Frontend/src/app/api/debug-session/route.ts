import { NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { customDecode } from "@/lib/jwt";
import { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  const token = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET || "development-secret-key-123",
    decode: customDecode
  });

  return NextResponse.json({
    hasToken: !!token,
    token: token,
    userId: token?.id,
    email: token?.email,
    name: token?.name
  });
}
