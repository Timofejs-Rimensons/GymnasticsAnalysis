import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { customDecode } from "@/lib/jwt";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000/api";

async function handler(req: NextRequest, props: { params: Promise<{ path: string[] }> }) {
  const params = await props.params;
  const path = params.path.join("/");

  // Public endpoints that don't require authentication
  const publicPaths = ["upload", "status", "process", "download", "analyze"];
  const isPublicPath = publicPaths.some(publicPath => path.startsWith(publicPath));

  // Get JWT token from session (decoded to get user data)
  const tokenData = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET || "development-secret-key-123",
    decode: customDecode
  });

  console.log("🔍 Proxy - Path:", path);
  console.log("🔍 Proxy - Token data:", tokenData);
  console.log("🔍 Proxy - User ID from token:", tokenData?.id);

  if (!tokenData && !isPublicPath) {
    console.log("❌ Proxy - Unauthorized (no token)");
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = `${BACKEND_URL}/${path}${req.nextUrl.search}`;
  console.log("🔍 Proxy - Backend URL:", url);

  const headers = new Headers();

  // Copy content-type if present
  if (req.headers.get("content-type")) {
      headers.set("content-type", req.headers.get("content-type")!);
  }

  // Forward user ID as X-User-Id header for backend
  if (tokenData?.id) {
    headers.set("X-User-Id", tokenData.id as string);
    console.log(`✅ Proxy - Forwarding X-User-Id: ${tokenData.id}`);
  } else if (tokenData) {
    console.log(`⚠️ Proxy - Token exists but no ID:`, JSON.stringify(tokenData));
  } else {
    console.log(`⚠️ Proxy - No token data (public path)`);
  }

  // Copy X-User-Id from incoming request if present (for upload)
  const incomingUserId = req.headers.get("X-User-Id");
  if (incomingUserId && !headers.has("X-User-Id")) {
    headers.set("X-User-Id", incomingUserId);
    console.log(`✅ Proxy - Using X-User-Id from request: ${incomingUserId}`);
  }

  const body = req.method !== "GET" && req.method !== "HEAD" ? await req.blob() : undefined;

  try {
    const response = await fetch(url, {
      method: req.method,
      headers: headers,
      body: body,
      // @ts-ignore
      duplex: 'half'
    });

    const data = await response.blob();
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error("❌ Proxy Error:", error);
    return NextResponse.json({ error: "Backend error" }, { status: 500 });
  }
}

export { handler as GET, handler as POST, handler as PUT, handler as DELETE };
