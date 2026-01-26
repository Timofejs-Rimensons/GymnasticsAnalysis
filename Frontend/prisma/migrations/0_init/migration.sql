-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- CreateTable
CREATE TABLE IF NOT EXISTS "users" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "email" VARCHAR(255) NOT NULL,
    "password_hash" VARCHAR(255) NOT NULL,
    "name" VARCHAR(255),
    "created_at" TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_login" TIMESTAMP(3) WITH TIME ZONE,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "sessions" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "session_token" VARCHAR(500) NOT NULL,
    "user_id" UUID NOT NULL,
    "expires_at" TIMESTAMP(3) WITH TIME ZONE NOT NULL,
    "created_at" TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "sessions_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE IF NOT EXISTS "analyses" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "user_id" UUID,
    "file_name" VARCHAR(500) NOT NULL,
    "exercise_type" VARCHAR(100) NOT NULL,
    "input_video" BYTEA,
    "input_video_size" INTEGER,
    "input_video_mime_type" VARCHAR(100) DEFAULT 'video/mp4',
    "output_video" BYTEA,
    "output_video_size" INTEGER,
    "output_video_mime_type" VARCHAR(100) DEFAULT 'video/mp4',
    "status" VARCHAR(50) NOT NULL DEFAULT 'pending',
    "progress" DECIMAL(3,2) DEFAULT 0.00,
    "error_message" TEXT,
    "overall_score" DECIMAL(5,2),
    "max_score" DECIMAL(5,2),
    "percentage" DECIMAL(5,2),
    "results_json" JSONB,
    "pdf_report" BYTEA,
    "pdf_report_size" INTEGER,
    "json_report" JSONB,
    "created_at" TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMP(3) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMP(3) WITH TIME ZONE,

    CONSTRAINT "analyses_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX IF NOT EXISTS "users_email_idx" ON "users"("email");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "sessions_user_id_idx" ON "sessions"("user_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "sessions_session_token_idx" ON "sessions"("session_token");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "sessions_expires_at_idx" ON "sessions"("expires_at");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "analyses_user_id_idx" ON "analyses"("user_id");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "analyses_status_idx" ON "analyses"("status");

-- CreateIndex
CREATE INDEX IF NOT EXISTS "analyses_created_at_idx" ON "analyses"("created_at" DESC);

-- CreateIndex
CREATE INDEX IF NOT EXISTS "analyses_exercise_type_idx" ON "analyses"("exercise_type");

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX IF NOT EXISTS "sessions_session_token_key" ON "sessions"("session_token");

-- AddForeignKey
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'sessions_user_id_fkey'
    ) THEN
        ALTER TABLE "sessions" ADD CONSTRAINT "sessions_user_id_fkey" 
        FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
    END IF;
END $$;

-- AddForeignKey
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'analyses_user_id_fkey'
    ) THEN
        ALTER TABLE "analyses" ADD CONSTRAINT "analyses_user_id_fkey" 
        FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
    END IF;
END $$;

-- CreateFunction
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- CreateTrigger
DROP TRIGGER IF EXISTS update_users_updated_at ON "users";
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON "users"
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- CreateTrigger
DROP TRIGGER IF EXISTS update_analyses_updated_at ON "analyses";
CREATE TRIGGER update_analyses_updated_at 
    BEFORE UPDATE ON "analyses"
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
