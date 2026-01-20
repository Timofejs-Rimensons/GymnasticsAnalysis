"use client";

import { CheckCircle, XCircle, Loader } from "lucide-react";
import { StatusResponse } from "@/lib/api";

interface VideoUpload {
  id: string;
  file: File;
  status: StatusResponse;
}

interface ProcessingStatusProps {
  videos: VideoUpload[];
}

export function ProcessingStatus({ videos }: ProcessingStatusProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-accent";
      case "failed":
        return "text-destructive";
      case "processing":
        return "text-foreground";
      default:
        return "text-muted-foreground";
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-5 h-5" />;
      case "failed":
        return <XCircle className="w-5 h-5" />;
      case "processing":
        return <Loader className="w-5 h-5 animate-spin" />;
      default:
        return <Loader className="w-5 h-5" />;
    }
  };

  if (videos.length === 0) return null;

  return (
    <section className="border-2 border-border bg-surface">
      <div className="px-6 py-4 border-b-2 border-border">
        <h2
          className="text-sm font-bold uppercase tracking-wider"
          style={{ fontFamily: "'Archivo Black', sans-serif" }}
        >
          Processing Status
        </h2>
      </div>

      <div className="divide-y-2 divide-border">
        {videos.map((video) => (
          <div key={video.id} className="px-6 py-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <div className={getStatusColor(video.status.status)}>
                  {getStatusIcon(video.status.status)}
                </div>
                <span className="font-mono text-sm truncate">
                  {video.file.name}
                </span>
              </div>
              <span
                className={`text-xs uppercase tracking-wider font-bold ${getStatusColor(video.status.status)}`}
              >
                {video.status.status}
              </span>
            </div>

            {/* Progress bar */}
            {(video.status.status === "processing" ||
              video.status.status === "pending") &&
              typeof video.status.progress === "number" && (
                <div className="h-2 bg-muted">
                  <div
                    className="h-full bg-accent transition-all duration-300"
                    style={{ width: `${video.status.progress}%` }}
                  />
                </div>
              )}

            {/* Error message */}
            {video.status.status === "failed" &&
              video.status.error_message && (
                <p className="text-sm mt-2 text-destructive font-mono">
                  {video.status.error_message}
                </p>
              )}
          </div>
        ))}
      </div>
    </section>
  );
}
