import { NextResponse } from "next/server";
import bcrypt from "bcryptjs";
// import { prisma } from "@/lib/prisma";

export async function POST(req: Request) {
  try {
    const { name, email, password } = await req.json();

    if (!email || !password) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    // Disabled prisma for now
    // const exists = await prisma.user.findUnique({
    //   where: {
    //     email,
    //   },
    // });
    //
    // if (exists) {
    //   return NextResponse.json(
    //     { error: "User already exists" },
    //     { status: 400 }
    //   );
    // }
    //
    // const hashedPassword = await bcrypt.hash(password, 10);
    //
    // const user = await prisma.user.create({
    //   data: {
    //     name,
    //     email,
    //     password: hashedPassword,
    //   },
    // });
    //
    // return NextResponse.json(user);

    // Stub response
    return NextResponse.json({
      id: 1,
      email,
      name,
      createdAt: new Date(),
    });
  } catch (error) {
    console.error("Registration error:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}
