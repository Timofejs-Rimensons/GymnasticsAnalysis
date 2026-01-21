import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getToken } from "next-auth/jwt";
import { customDecode } from "@/lib/jwt";

export async function middleware(req: NextRequest) {
  const token = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET || "development-secret-key-123",
    decode: customDecode,
  });

  const { pathname } = req.nextUrl;

  // Protect only history and profile routes - upload is public
  if (
    pathname.startsWith("/history") ||
    pathname.startsWith("/profile")
  ) {
    if (!token) {
      const url = new URL("/login", req.url);
      url.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(url);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/history/:path*",
    "/profile/:path*",
  ],
};