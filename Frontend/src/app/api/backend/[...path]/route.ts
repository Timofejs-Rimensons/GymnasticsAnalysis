import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000/api";

async function handler(req: NextRequest, props: { params: Promise<{ path: string[] }> }) {
  const params = await props.params;
  const path = params.path.join("/");
  
  // Get raw JWT token from session
  const token = await getToken({ req, raw: true });

  if (!token) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = `${BACKEND_URL}/${path}${req.nextUrl.search}`;
  
  const headers = new Headers();
  // Copy necessary headers, but be careful with host/content-length
  if (req.headers.get("content-type")) {
      headers.set("content-type", req.headers.get("content-type")!);
  }
  headers.set("Authorization", `Bearer ${token}`);

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
    console.error("Proxy Error:", error);
    return NextResponse.json({ error: "Backend error" }, { status: 500 });
  }
}

export { handler as GET, handler as POST, handler as PUT, handler as DELETE };
