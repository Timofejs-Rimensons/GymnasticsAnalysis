import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { customDecode } from "@/lib/jwt";
import { prisma, handlePrismaError } from "@/lib/prisma";
import { validateUUID } from "@/lib/validation";

export async function GET(req: NextRequest) {
  try {
    // Get JWT token from session to extract user ID
    const tokenData = await getToken({
      req,
      secret: process.env.NEXTAUTH_SECRET || "development-secret-key-123",
      decode: customDecode
    });

    if (!tokenData?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Validate UUID format
    let userId: string;
    try {
      userId = validateUUID(tokenData.id as string, "User ID");
    } catch (error) {
      return NextResponse.json(
        { error: error instanceof Error ? error.message : "Invalid user ID format" },
        { status: 400 }
      );
    }

    // Get pagination parameters from query string
    const searchParams = req.nextUrl.searchParams;
    const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10));
    const limit = Math.min(100, Math.max(1, parseInt(searchParams.get("limit") || "20", 10)));
    const skip = (page - 1) * limit;

    // Query the database for analyses belonging to this user
    const [analyses, total] = await Promise.all([
      prisma.analysis.findMany({
        where: {
          userId: userId
        },
        orderBy: {
          createdAt: 'desc'
        },
        select: {
          id: true,
          exerciseType: true,
          status: true,
          overallScore: true,
          maxScore: true,
          createdAt: true,
          fileName: true
        },
        take: limit,
        skip: skip
      }),
      prisma.analysis.count({
        where: {
          userId: userId
        }
      })
    ]);

    // Map the database results to the format expected by the frontend
    const history = analyses.map((analysis) => ({
      id: analysis.id,
      created_at: analysis.createdAt.toISOString(),
      exerciseType: analysis.exerciseType,
      score: analysis.overallScore ? Number(analysis.overallScore) : null,
      maxScore: analysis.maxScore ? Number(analysis.maxScore) : null,
      status: analysis.status,
      fileName: analysis.fileName
    }));

    return NextResponse.json({
      data: history,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasMore: skip + analyses.length < total
      }
    });
  } catch (error) {
    console.error("❌ History API Error:", error);
    const { message, statusCode } = handlePrismaError(error);
    return NextResponse.json(
      { error: message },
      { status: statusCode }
    );
  }
}
