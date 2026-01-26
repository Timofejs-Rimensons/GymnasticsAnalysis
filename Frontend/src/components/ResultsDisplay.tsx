"use client";

import { useState } from "react";
import { Download, ChevronDown, AlertCircle, Info } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { ApiService, AnalysisResult, StatusResponse, Pose } from "@/lib/api";
import { formatFileSize } from "@/lib/utils";
import {
  Tooltip as UITooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface VideoUpload {
  id: string;
  file: File;
  uploadedUrl: string;
  status: StatusResponse;
  analysisResults?: AnalysisResult;
}

interface ResultsDisplayProps {
  videos: VideoUpload[];
  selectedVideoId: string | null;
  onSelectVideo: (id: string) => void;
}

const CHART_COLORS = [
  "#00b4d8",
  "#f2f2f2",
  "#999999",
  "#666666",
  "#404040",
  "#cccccc",
  "#808080",
];

export function ResultsDisplay({
  videos,
  selectedVideoId,
  onSelectVideo,
}: ResultsDisplayProps) {
  const [showVideoSelector, setShowVideoSelector] = useState(false);

  const completedVideos = videos.filter((v) => v.status.status === "completed");
  const selectedVideo = videos.find((v) => v.id === selectedVideoId);
  const resultsData = selectedVideo?.analysisResults;

  // Flatten all poses from all categories
  const allPoses: (Pose & { color: string })[] = resultsData?.categories
    ? resultsData.categories.flatMap((category) =>
        category.poses.map((pose, poseIndex) => {
          const globalIndex = resultsData.categories
            .slice(0, resultsData.categories.indexOf(category))
            .reduce((sum, cat) => sum + cat.poses.length, 0) + poseIndex;

          return {
            ...pose,
            color: CHART_COLORS[globalIndex % CHART_COLORS.length],
          };
        })
      )
    : [];

  // Calculate totals
  const totalScore = resultsData?.overall_score || 0;
  const maxScore = resultsData?.max_score || 100;
  const roomForImprovement = Math.max(0, maxScore - totalScore);

  // Prepare chart data - Use actual scores for proportional values
  const chartData = [
    ...allPoses.map((pose) => ({
      name: pose.name,
      value: pose.score,
      actualScore: pose.score,
      maxScore: pose.max_score,
      poseData: pose,
      color: pose.color,
    })),
    {
      name: "Room for Improvement",
      value: roomForImprovement,
      actualScore: roomForImprovement,
      maxScore: maxScore,
      poseData: null,
      color: "#333333",
    },
  ];

  const handleSaveVideo = () => {
    if (!selectedVideoId) return;
    const downloadUrl = ApiService.getDownloadUrl(selectedVideoId);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `processed_${selectedVideo?.file.name || "video"}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSaveReport = () => {
    if (!selectedVideoId) return;
    const pdfUrl = ApiService.getReportPdfUrl(selectedVideoId);
    const link = document.createElement("a");
    link.href = pdfUrl;
    link.download = `report_${selectedVideoId}.pdf`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (completedVideos.length === 0) return null;

  return (
    <section className="border-2 border-border p-6 bg-surface">
      <TooltipProvider>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-3 h-3 bg-accent" />
        <h2
          className="text-lg font-black uppercase tracking-tight"
          style={{ fontFamily: "'Archivo Black', sans-serif" }}
        >
          Analysis Results
        </h2>
      </div>

      {/* Video Selector */}
      <div className="mb-6">
        <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
          Select Video
        </label>
        <div className="relative">
          <button
            onClick={() => setShowVideoSelector(!showVideoSelector)}
            className="w-full px-4 py-3 border-2 border-border flex items-center justify-between transition-all duration-200 hover:border-accent bg-background"
          >
            <span className="truncate font-mono text-sm">
              {selectedVideo ? selectedVideo.file.name : "Select a video"}
            </span>
            <ChevronDown
              className={`w-5 h-5 transition-transform ${showVideoSelector ? "rotate-180" : ""}`}
            />
          </button>

          {showVideoSelector && (
            <div className="absolute top-full left-0 right-0 mt-1 border-2 border-border z-20 bg-background">
              {completedVideos.map((video) => (
                <button
                  key={video.id}
                  onClick={() => {
                    onSelectVideo(video.id);
                    setShowVideoSelector(false);
                  }}
                  className={`w-full px-4 py-3 text-left border-b last:border-b-0 transition-all duration-200 ${
                    selectedVideoId === video.id
                      ? "bg-accent/10 border-accent"
                      : "border-border hover:bg-surface"
                  }`}
                >
                  <div className="truncate font-mono text-sm">
                    {video.file.name}
                  </div>
                  <div className="text-xs font-mono mt-1 text-muted-foreground">
                    {formatFileSize(video.file.size)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Video Preview */}
      {selectedVideo && (
        <div className="mb-6">
          <div className="border-2 border-border overflow-hidden bg-black">
            <video
              key={`processed-${selectedVideo.id}`}
              src={ApiService.getDownloadUrl(selectedVideo.id)}
              controls
              className="w-full h-auto max-h-[400px] object-contain"
            />
          </div>
          <p className="text-xs uppercase tracking-wider mt-2 text-muted-foreground">
            Processed Video
          </p>
        </div>
      )}

      {/* Analysis Results */}
      {resultsData && (
        <div className="mb-6 border-2 border-border">
          {/* Overall Score */}
          <div className="p-6 border-b-2 border-border">
            <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3">
              Overall Score
            </p>
            <div className="flex items-baseline gap-2">
              <span
                className="text-5xl font-black text-accent"
                style={{ fontFamily: "'Archivo Black', sans-serif" }}
              >
                {resultsData.overall_score}
              </span>
              <span className="text-2xl text-muted">
                / {resultsData.max_score}
              </span>
            </div>
            <div className="text-xl font-bold mt-2">
              {resultsData.percentage.toFixed(1)}%
            </div>
          </div>

          {/* Poses Grid and Chart */}
          {chartData.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2">
              {/* Pose Cards */}
              <div className="lg:border-r-2 lg:border-border">
                {allPoses.map((pose, index) => (
                  <div
                    key={index}
                    className="p-4 border-b-2 border-border last:border-b-0"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <h4 className="font-bold uppercase text-sm tracking-wide">
                          {pose.name}
                        </h4>
                        {pose.tips && pose.tips.length > 0 && (
                          <UITooltip>
                            <TooltipTrigger asChild>
                              <button className="inline-flex items-center justify-center w-5 h-5 rounded-full border border-accent bg-accent/10 text-accent hover:bg-accent hover:text-accent-foreground transition-colors">
                                <Info className="w-3 h-3" />
                              </button>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                              <div className="space-y-2">
                                <p className="font-bold text-xs uppercase tracking-wider mb-2">
                                  Improvement Tips
                                </p>
                                {pose.tips.map((tip, tipIndex) => (
                                  <div
                                    key={tipIndex}
                                    className={`text-xs ${
                                      !tip.met
                                        ? "text-accent font-semibold"
                                        : "text-muted-foreground"
                                    }`}
                                  >
                                    <span className="inline-block mr-1">
                                      {!tip.met ? "⚠" : "✓"}
                                    </span>
                                    <span className="font-mono text-[10px] uppercase tracking-wide">
                                      {tip.criterion}:
                                    </span>{" "}
                                    {tip.tip}
                                  </div>
                                ))}
                              </div>
                            </TooltipContent>
                          </UITooltip>
                        )}
                      </div>
                    </div>
  
                    {/* Score with Tooltip */}
                    <div className="flex justify-end mb-2">
                      <UITooltip>
                        <TooltipTrigger asChild>
                          <span
                            className="font-mono text-sm font-bold cursor-help"
                            style={{ color: pose.color }}
                          >
                            {pose.score}/{pose.max_score}
                          </span>
                        </TooltipTrigger>
                        {pose.errors && pose.errors.length > 0 && (
                          <TooltipContent className="max-w-xs">
                            <div className="space-y-2">
                              <p className="font-bold text-xs uppercase tracking-wider mb-2">
                                Improvements Needed
                              </p>
                              {pose.errors.map((error, errorIndex) => (
                                <div key={errorIndex} className="text-xs text-accent font-semibold">
                                  <span className="inline-block mr-1">⚠</span>
                                  <span className="font-mono text-[10px] uppercase tracking-wide">
                                    {error.criterion}:
                                  </span>{' '}
                                  {error.improvement}
                                </div>
                              ))}
                            </div>
                          </TooltipContent>
                        )}
                      </UITooltip>
                    </div>

                    {/* Progress Bar */}
                    <div className="h-2 mb-2 bg-muted">
                      <div
                        className="h-full transition-all duration-300"
                        style={{
                          width: `${(pose.score / pose.max_score) * 100}%`,
                          backgroundColor: pose.color,
                        }}
                      />
                    </div>

                    {pose.description && (
                      <p className="text-xs text-muted-foreground">
                        {pose.description}
                      </p>
                    )}

                    {(pose.improvement_needed ||
                      pose.score / pose.max_score <= 0.5) && (
                      <div className="mt-2 inline-flex items-center gap-1 px-2 py-1 bg-accent/10 border border-accent">
                        <AlertCircle className="w-3 h-3 text-accent" />
                        <span className="text-xs font-bold uppercase text-accent">
                          Needs Work
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Pie Chart */}
              <div className="p-6">
                <div className="w-full h-[280px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={90}
                        innerRadius={50}
                        fill="#8884d8"
                        dataKey="value"
                        strokeWidth={2}
                        stroke="#141414"
                      >
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const entry = payload[0].payload;
                            const isRoomForImprovement =
                              entry.name === "Room for Improvement";

                            return (
                              <div className="p-3 border-2 border-border bg-background">
                                <p className="font-bold uppercase text-sm mb-1">
                                  {entry.name}
                                </p>
                                <p className="text-sm font-mono text-muted-foreground">
                                  {isRoomForImprovement
                                    ? `Points to gain: ${entry.actualScore}`
                                    : `Score: ${entry.actualScore}/${entry.maxScore}`}
                                </p>
                              </div>
                            );
                          }
                          return null;
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                {/* Legend */}
                <div className="space-y-2 mt-4">
                  {chartData.map((entry, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-2 text-xs"
                    >
                      <div
                        className="w-3 h-3 flex-shrink-0"
                        style={{ backgroundColor: entry.color }}
                      />
                      <span className="flex-1 uppercase tracking-wide text-muted-foreground">
                        {entry.name}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Download Buttons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button
          onClick={handleSaveVideo}
          disabled={
            !selectedVideoId || selectedVideo?.status.status !== "completed"
          }
          className="flex items-center justify-center gap-3 px-6 py-4 border-2 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:-translate-y-0.5 bg-accent border-accent text-accent-foreground hover:bg-accent/90"
        >
          <Download className="w-5 h-5" />
          <span className="font-bold uppercase tracking-wider text-sm">
            Download Video
          </span>
        </button>

        <button
          onClick={handleSaveReport}
          disabled={!selectedVideoId || !resultsData}
          className="flex items-center justify-center gap-3 px-6 py-4 border-2 border-foreground transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed hover:-translate-y-0.5 hover:bg-foreground hover:text-background"
        >
          <Download className="w-5 h-5" />
          <span className="font-bold uppercase tracking-wider text-sm">
            Download Report (PDF)
          </span>
        </button>
      </div>
      </TooltipProvider>
    </section>
  );
}
