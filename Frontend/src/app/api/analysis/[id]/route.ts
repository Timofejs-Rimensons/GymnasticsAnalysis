import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";
import { customDecode } from "@/lib/jwt";
import { prisma, handlePrismaError } from "@/lib/prisma";
import { validateUUID } from "@/lib/validation";

/**
 * PATCH /api/analysis/[id] - Update an analysis record
 */
export async function PATCH(
  req: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  try {
    const params = await props.params;
    const analysisId = params.id;

    // Get JWT token from session
    const tokenData = await getToken({
      req,
      secret: process.env.NEXTAUTH_SECRET || "development-secret-key-123",
      decode: customDecode
    });

    if (!tokenData?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Validate UUIDs
    const userId = validateUUID(tokenData.id as string, "User ID");
    const validAnalysisId = validateUUID(analysisId, "Analysis ID");

    // Verify analysis belongs to user
    const existingAnalysis = await prisma.analysis.findFirst({
      where: {
        id: validAnalysisId,
        userId: userId
      }
    });

    if (!existingAnalysis) {
      return NextResponse.json(
        { error: "Analysis not found" },
        { status: 404 }
      );
    }

    // Parse request body
    const body = await req.json();
    const {
      status,
      progress,
      overallScore,
      maxScore,
      percentage,
      resultsJson,
      errorMessage,
      completedAt
    } = body;

    // Build update data object (only include provided fields)
    const updateData: any = {};
    if (status !== undefined) updateData.status = status;
    if (progress !== undefined) updateData.progress = progress;
    if (overallScore !== undefined) updateData.overallScore = overallScore;
    if (maxScore !== undefined) updateData.maxScore = maxScore;
    if (percentage !== undefined) updateData.percentage = percentage;
    if (resultsJson !== undefined) updateData.resultsJson = resultsJson;
    if (errorMessage !== undefined) updateData.errorMessage = errorMessage;
    if (completedAt !== undefined) {
      updateData.completedAt = completedAt ? new Date(completedAt) : null;
    }

    // Update analysis record
    const analysis = await prisma.analysis.update({
      where: { id: validAnalysisId },
      data: updateData,
      select: {
        id: true,
        fileName: true,
        exerciseType: true,
        status: true,
        progress: true,
        overallScore: true,
        maxScore: true,
        percentage: true,
        resultsJson: true,
        errorMessage: true,
        createdAt: true,
        updatedAt: true,
        completedAt: true
      }
    });

    return NextResponse.json(analysis);
  } catch (error) {
    console.error("❌ Update Analysis Error:", error);
    const { message, statusCode } = handlePrismaError(error);
    return NextResponse.json(
      { error: message },
      { status: statusCode }
    );
  }
}

/**
 * DELETE /api/analysis/[id] - Delete an analysis record
 */
export async function DELETE(
  req: NextRequest,
  props: { params: Promise<{ id: string }> }
) {
  try {
    const params = await props.params;
    const analysisId = params.id;

    // Get JWT token from session
    const tokenData = await getToken({
      req,
      secret: process.env.NEXTAUTH_SECRET || "development-secret-key-123",
      decode: customDecode
    });

    if (!tokenData?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Validate UUIDs
    const userId = validateUUID(tokenData.id as string, "User ID");
    const validAnalysisId = validateUUID(analysisId, "Analysis ID");

    // Verify analysis belongs to user
    const existingAnalysis = await prisma.analysis.findFirst({
      where: {
        id: validAnalysisId,
        userId: userId
      }
    });

    if (!existingAnalysis) {
      return NextResponse.json(
        { error: "Analysis not found" },
        { status: 404 }
      );
    }

    // Delete analysis record
    await prisma.analysis.delete({
      where: { id: validAnalysisId }
    });

    return NextResponse.json({ message: "Analysis deleted successfully" });
  } catch (error) {
    console.error("❌ Delete Analysis Error:", error);
    const { message, statusCode } = handlePrismaError(error);
    return NextResponse.json(
      { error: message },
      { status: statusCode }
    );
  }
}
