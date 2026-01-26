import { SignJWT, jwtVerify } from "jose";
import { JWT, JWTDecodeParams, JWTEncodeParams } from "next-auth/jwt";

export async function customEncode({ token, secret }: JWTEncodeParams): Promise<string> {
  if (!token) return "";
  const encodedSecret = new TextEncoder().encode(String(secret));

  return new SignJWT(token)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("30d")
    .sign(encodedSecret);
}

export async function customDecode({ token, secret }: JWTDecodeParams): Promise<JWT | null> {
  if (!token) return null;
  const encodedSecret = new TextEncoder().encode(String(secret));
  try {
    const { payload } = await jwtVerify(token, encodedSecret);

    const id =
      typeof payload.id === "string"
        ? payload.id
        : typeof payload.sub === "string"
        ? payload.sub
        : "";

    return {
      id,
      name: typeof payload.name === "string" ? payload.name : undefined,
      email: typeof payload.email === "string" ? payload.email : undefined,
      picture: typeof payload.picture === "string" ? payload.picture : undefined,
      sub: payload.sub,
      iat: payload.iat,
      exp: payload.exp,
      jti: payload.jti,
    } satisfies JWT;
  } catch (error) {
    return null;
  }
}
