import { PrismaClient } from "@prisma/client";
import { Prisma } from "@prisma/client";

const globalForPrisma = global as unknown as { prisma: PrismaClient };

// Get DATABASE_URL - use dummy value during build if not set
const databaseUrl = process.env.DATABASE_URL || "postgresql://dummy:dummy@localhost:5432/dummy";

// Create Prisma client with connection pooling configuration
// Note: During build time, DATABASE_URL might not be set, so we use a dummy value
// The actual connection will be validated at runtime
export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    log: process.env.NODE_ENV === "development" ? ["query", "error", "warn"] : ["error"],
    datasources: {
      db: {
        url: databaseUrl,
      },
    },
  });

// Validate DATABASE_URL at runtime (not during build)
if (typeof window === "undefined" && process.env.NODE_ENV !== "test") {
  // Only validate when actually running, not during build
  const actualUrl = process.env.DATABASE_URL;
  if (!actualUrl || actualUrl.includes("dummy")) {
    // Don't throw during build - will be set at runtime
    if (process.env.NEXT_PHASE !== "phase-production-build") {
      console.warn("⚠️ DATABASE_URL not set - database operations will fail");
    }
  }
}

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;

// Graceful shutdown handler
if (typeof window === "undefined") {
  process.on("beforeExit", async () => {
    await prisma.$disconnect();
  });

  process.on("SIGINT", async () => {
    await prisma.$disconnect();
    process.exit(0);
  });

  process.on("SIGTERM", async () => {
    await prisma.$disconnect();
    process.exit(0);
  });
}

// Helper function to handle Prisma errors
export function handlePrismaError(error: unknown): { message: string; statusCode: number } {
  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    switch (error.code) {
      case "P2002":
        return { message: "Unique constraint violation", statusCode: 409 };
      case "P2025":
        return { message: "Record not found", statusCode: 404 };
      case "P2003":
        return { message: "Foreign key constraint violation", statusCode: 400 };
      default:
        return { message: `Database error: ${error.message}`, statusCode: 500 };
    }
  }
  
  if (error instanceof Prisma.PrismaClientValidationError) {
    return { message: "Invalid data provided", statusCode: 400 };
  }

  if (error instanceof Prisma.PrismaClientInitializationError) {
    return { message: "Database connection failed", statusCode: 503 };
  }

  return { message: "An unexpected error occurred", statusCode: 500 };
}
