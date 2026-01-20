import { SignJWT, jwtVerify } from "jose";

export async function customEncode({ token, secret }: { token?: any; secret: string | Buffer }) {
  if (!token) return "";
  const encodedSecret = new TextEncoder().encode(String(secret));
  return new SignJWT(token)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(encodedSecret);
}

export async function customDecode({ token, secret }: { token?: string; secret: string | Buffer }) {
  if (!token) return null;
  const encodedSecret = new TextEncoder().encode(String(secret));
  try {
    const { payload } = await jwtVerify(token, encodedSecret);
    return payload;
  } catch (error) {
    return null;
  }
}
