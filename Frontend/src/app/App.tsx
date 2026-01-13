import { useState, useRef } from "react";
import { Upload, Download, Video, Sun, Moon, HelpCircle, Hand, ArrowLeft, CheckCircle, XCircle, Loader, ChevronDown } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./components/ui/dialog";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { ApiService, StatusResponse, AnalysisResult } from "./services/api";

interface VideoUpload {
  id: string;
  file: File;
  uploadedUrl: string; // Local blob URL for preview
  status: StatusResponse;
  analysisResults?: AnalysisResult;
}

export default function App() {
  const [videos, setVideos] = useState<VideoUpload[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [showInstructions, setShowInstructions] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [showVideoSelector, setShowVideoSelector] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const selectedVideo = videos.find(v => v.id === selectedVideoId);
  const resultsData = selectedVideo?.analysisResults;

  // Pie chart colors
  const categoryColors = theme === "dark"
    ? ["#a78bfa", "#818cf8", "#60a5fa", "#34d399", "#fbbf24", "#f472b6", "#fb923c"]
    : ["#7c3aed", "#4f46e5", "#2563eb", "#059669", "#d97706", "#db2777", "#ea580c"];

  // Prepare chart data from backend categories
  const chartData = resultsData?.categories
    ? resultsData.categories.map((category, index) => ({
        name: `Category ${index + 1}`,
        value: 1, // Equal size for visualization
        categoryData: category, // Store full category data for tooltip
        color: categoryColors[index % categoryColors.length]
      }))
    : [];

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const handleOptionSelect = (option: string) => {
    setSelectedOption(option);
  };

  /**
   * Poll status and fetch results when completed
   */
  const pollVideoStatus = async (videoId: string) => {
    try {
      const status = await ApiService.pollUntilComplete(videoId, 2000);

      // Update status to completed
      setVideos(prev => prev.map(v =>
        v.id === videoId ? { ...v, status } : v
      ));

      // Fetch analysis results from backend
      if (status.status === "completed") {
        try {
          const analysisResults = await ApiService.getResponseJson(videoId);
          setVideos(prev => prev.map(v =>
            v.id === videoId ? { ...v, analysisResults } : v
          ));
        } catch (error) {
          console.error("Error fetching analysis results:", error);
        }
      }
    } catch (error) {
      console.error("Error polling status for video:", videoId, error);
      // On error, mark as failed
      setVideos(prev => prev.map(v =>
        v.id === videoId ? {
          ...v,
          status: {
            status: "failed",
            progress: 0,
            error_message: error instanceof Error ? error.message : "Failed to process video"
          }
        } : v
      ));
    }
  };

  /**
   * Handle file selection from input
   */
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file && file.type.startsWith("video/")) {
        try {
          // Step 1: Upload video and get process ID
          const uploadResponse = await ApiService.uploadVideo(file);
          const videoId = uploadResponse.pid;

          const newVideo: VideoUpload = {
            id: videoId,
            file: file,
            uploadedUrl: URL.createObjectURL(file),
            status: {
              status: "pending",
              progress: 0,
            }
          };

          setVideos(prev => {
            const updated = [...prev, newVideo];
            // Set as selected if it's the first video
            if (prev.length === 0) {
              setSelectedVideoId(videoId);
            }
            return updated;
          });

          // Step 2: Start processing with selected exercise type
          await ApiService.startProcessing(videoId, selectedOption || "handstand");

          // Step 3: Start polling for status
          pollVideoStatus(videoId);
        } catch (error) {
          console.error("Error uploading video:", error);
          alert(error instanceof Error ? error.message : "Failed to upload video");
        }
      }
    }
  };

  /**
   * Handle drag and drop events
   */
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (!files) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file && file.type.startsWith("video/")) {
        try {
          // Step 1: Upload video and get process ID
          const uploadResponse = await ApiService.uploadVideo(file);
          const videoId = uploadResponse.pid;

          const newVideo: VideoUpload = {
            id: videoId,
            file: file,
            uploadedUrl: URL.createObjectURL(file),
            status: {
              status: "pending",
              progress: 0,
            }
          };

          setVideos(prev => {
            const updated = [...prev, newVideo];
            if (prev.length === 0) {
              setSelectedVideoId(videoId);
            }
            return updated;
          });

          // Step 2: Start processing with selected exercise type
          await ApiService.startProcessing(videoId, selectedOption || "handstand");

          // Step 3: Start polling for status
          pollVideoStatus(videoId);
        } catch (error) {
          console.error("Error uploading video:", error);
          alert(error instanceof Error ? error.message : "Failed to upload video");
        }
      }
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  /**
   * Download processed video from backend
   */
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

  /**
   * Download report from backend
   */
  const handleSaveReport = (format: "pdf" | "json") => {
    if (!selectedVideoId) return;

    if (format === "pdf") {
      const pdfUrl = ApiService.getReportPdfUrl(selectedVideoId);
      const link = document.createElement("a");
      link.href = pdfUrl;
      link.download = `report_${selectedVideoId}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } else if (format === "json") {
      // JSON is already fetched, download it as a file
      if (resultsData) {
        const dataStr = JSON.stringify(resultsData, null, 2);
        const dataBlob = new Blob([dataStr], { type: "application/json" });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `report_${selectedVideoId}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      }
    }
  };

  /**
   * UI Helper Functions
   */
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return theme === "dark" ? "text-green-400" : "text-green-600";
      case "failed":
        return theme === "dark" ? "text-red-400" : "text-red-600";
      case "processing":
        return theme === "dark" ? "text-blue-400" : "text-blue-600";
      default:
        return theme === "dark" ? "text-gray-400" : "text-gray-600";
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

  const hasCompletedVideos = videos.some(v => v.status.status === "completed");

  return (
    <div className={`min-h-screen relative overflow-hidden font-['Inter',sans-serif] transition-colors duration-500 ${
      theme === "dark" ? "bg-[#0a0a1a]" : "bg-white"
    }`}>
      {/* Animated background orbs */}
      {theme === "dark" ? (
        <>
          <div className="absolute top-20 left-20 w-96 h-96 bg-purple-600/30 rounded-full blur-[120px] animate-pulse"></div>
          <div className="absolute bottom-20 right-20 w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-600/10 rounded-full blur-[150px]"></div>
        </>
      ) : (
        <>
          <div className="absolute top-20 left-20 w-96 h-96 bg-blue-400/20 rounded-full blur-[120px] animate-pulse"></div>
          <div className="absolute bottom-20 right-20 w-[500px] h-[500px] bg-cyan-400/15 rounded-full blur-[120px] animate-pulse" style={{ animationDelay: '1s' }}></div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-sky-400/10 rounded-full blur-[150px]"></div>
        </>
      )}

      {/* Theme Toggle Button */}
      <button
        onClick={toggleTheme}
        className={`fixed top-8 right-8 z-50 p-4 rounded-2xl backdrop-blur-xl transition-all duration-300 hover:scale-110 shadow-2xl ${
          theme === "dark"
            ? "bg-white/10 border border-white/20 hover:bg-white/20"
            : "bg-blue-500/10 border border-blue-500/30 hover:bg-blue-500/20"
        }`}
      >
        {theme === "dark" ? (
          <Sun className="w-6 h-6 text-yellow-300" />
        ) : (
          <Moon className="w-6 h-6 text-blue-600" />
        )}
      </button>

      {/* Main Content */}
      <div className="relative z-10 container mx-auto px-6 py-16 max-w-4xl">
        {/* Option Selection Screen */}
        {selectedOption === null ? (
          <>
            {/* Header */}
            <div className="text-center mb-16">
              <div className="flex items-center justify-center gap-3 mb-4">
                <div className={`p-3 rounded-2xl backdrop-blur-xl border shadow-2xl ${
                  theme === "dark"
                    ? "bg-white/10 border-white/20"
                    : "bg-blue-500/10 border-blue-500/20"
                }`}>
                  <Video className={`w-8 h-8 ${theme === "dark" ? "text-white" : "text-blue-600"}`} />
                </div>
              </div>
              <h1 className={`text-5xl font-semibold mb-3 tracking-tight ${
                theme === "dark" ? "text-white" : "text-gray-900"
              }`}>
                Video Processor
              </h1>
              <p className={`text-lg mb-5 ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                Transform your videos with cutting-edge processing
              </p>
              
              {/* How to Use Button */}
              <button
                onClick={() => setShowInstructions(true)}
                className={`
                  inline-flex items-center gap-2 px-6 py-3
                  backdrop-blur-xl border rounded-full
                  transition-all duration-200
                  hover:scale-105
                  shadow-lg hover:shadow-xl
                  ${theme === "dark"
                    ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                    : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                  }
                `}
              >
                <HelpCircle className="w-5 h-5" />
                <span className="font-medium">How to Use</span>
              </button>
            </div>

            {/* Option Tiles */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
              {/* Handstand Option */}
              <button
                onClick={() => handleOptionSelect("handstand")}
                className={`
                  group relative
                  backdrop-blur-2xl
                  border-2 rounded-3xl
                  p-12 transition-all duration-300
                  shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]
                  hover:scale-[1.02]
                  ${theme === "dark"
                    ? "bg-white/5 border-white/20 hover:bg-white/10 hover:border-purple-400/40"
                    : "bg-blue-50/50 border-blue-200/40 hover:bg-blue-100/60 hover:border-blue-400/60"
                  }
                `}
              >
                <div className="flex justify-center mb-8">
                  <div className={`
                    p-6 rounded-2xl border-2 transition-all duration-300
                    ${theme === "dark"
                      ? "bg-white/10 border-white/20 group-hover:bg-purple-500/20 group-hover:border-purple-400/40"
                      : "bg-white/60 border-blue-200/40 group-hover:bg-blue-500/20 group-hover:border-blue-500/40"
                    }
                  `}>
                    <Hand className={`w-12 h-12 ${
                      theme === "dark" ? "text-white/70 group-hover:text-purple-300" : "text-blue-500 group-hover:text-blue-600"
                    }`} strokeWidth={1.5} />
                  </div>
                </div>
                
                <p className={`text-xl font-medium ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}>
                  Handstand
                </p>
                
                <div className={`absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none ${
                  theme === "dark"
                    ? "bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10"
                    : "bg-gradient-to-br from-blue-400/10 via-transparent to-cyan-400/10"
                }`}></div>
              </button>

              {/* Straddle Jump Option */}
              <button
                onClick={() => handleOptionSelect("straddle_jump")}
                className={`
                  group relative
                  backdrop-blur-2xl
                  border-2 rounded-3xl
                  p-12 transition-all duration-300
                  shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]
                  hover:scale-[1.02]
                  ${theme === "dark"
                    ? "bg-white/5 border-white/20 hover:bg-white/10 hover:border-purple-400/40"
                    : "bg-blue-50/50 border-blue-200/40 hover:bg-blue-100/60 hover:border-blue-400/60"
                  }
                `}
              >
                <div className="flex justify-center mb-8">
                  <div className={`
                    p-6 rounded-2xl border-2 transition-all duration-300
                    ${theme === "dark"
                      ? "bg-white/10 border-white/20 group-hover:bg-purple-500/20 group-hover:border-purple-400/40"
                      : "bg-white/60 border-blue-200/40 group-hover:bg-blue-500/20 group-hover:border-blue-500/40"
                    }
                  `}>
                    <svg className={`w-12 h-12 ${
                      theme === "dark" ? "text-white/70 group-hover:text-purple-300" : "text-blue-500 group-hover:text-blue-600"
                    }`} strokeWidth={1.5} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 15.3m14.8 0l-.94 3.013c-.07.22-.263.348-.49.348h-2.25a.75.75 0 01-.75-.75V17.5m-7.5 0v.563a.75.75 0 01-.75.75H5.12c-.227 0-.42-.128-.49-.348L3.7 15.3" />
                    </svg>
                  </div>
                </div>
                
                <p className={`text-xl font-medium ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}>
                  Straddle Jump
                </p>
                
                <div className={`absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none ${
                  theme === "dark"
                    ? "bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10"
                    : "bg-gradient-to-br from-blue-400/10 via-transparent to-cyan-400/10"
                }`}></div>
              </button>
            </div>

            {/* Footer */}
            <div className="mt-16 text-center">
              <p className={`text-sm ${theme === "dark" ? "text-white/40" : "text-gray-400"}`}>
                Powered by advanced AI processing • Secure & Private
              </p>
            </div>
          </>
        ) : (
          <>
            {/* Back Button */}
            <button
              onClick={() => {
                setSelectedOption(null);
                setVideos([]);
                setSelectedVideoId(null);
              }}
              className={`
                fixed top-8 left-8 z-50
                inline-flex items-center gap-2 px-5 py-3
                backdrop-blur-xl border-2 rounded-full
                transition-all duration-300
                hover:scale-105
                shadow-2xl
                ${theme === "dark"
                  ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                  : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                }
              `}
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">Back</span>
            </button>

            {/* Upload Interface */}
            <div className="text-center mb-16">
              <div className="flex items-center justify-center gap-3 mb-4">
                <div className={`p-3 rounded-2xl backdrop-blur-xl border shadow-2xl ${
                  theme === "dark"
                    ? "bg-white/10 border-white/20"
                    : "bg-blue-500/10 border-blue-500/20"
                }`}>
                  <Video className={`w-8 h-8 ${theme === "dark" ? "text-white" : "text-blue-600"}`} />
                </div>
              </div>
              <h1 className={`text-5xl font-semibold mb-3 tracking-tight ${
                theme === "dark" ? "text-white" : "text-gray-900"
              }`}>
                {selectedOption === "handstand" ? "Handstand" : "Straddle Jump"} Analysis
              </h1>
              <p className={`text-lg mb-5 ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                Upload your videos for AI-powered analysis
              </p>
              
              {/* How to Use Button */}
              <button
                onClick={() => setShowInstructions(true)}
                className={`
                  inline-flex items-center gap-2 px-6 py-3
                  backdrop-blur-xl border rounded-full
                  transition-all duration-200
                  hover:scale-105
                  shadow-lg hover:shadow-xl
                  ${theme === "dark"
                    ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                    : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                  }
                `}
              >
                <HelpCircle className="w-5 h-5" />
                <span className="font-medium">How to Use</span>
              </button>
            </div>

            {/* Upload Area */}
            <div className="mb-8">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
                multiple
                onChange={handleFileChange}
                className="hidden"
              />
              <div
                onClick={handleUploadClick}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                className={`
                  relative group cursor-pointer
                  backdrop-blur-2xl
                  border-2 border-dashed rounded-3xl
                  p-16 transition-all duration-300
                  shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]
                  ${theme === "dark" 
                    ? `bg-white/5 hover:bg-white/10 ${isDragging ? 'border-purple-400/60 bg-white/15 scale-[1.02]' : 'border-white/20'} ${videos.length > 0 ? 'border-purple-400/40 bg-purple-500/10' : ''} hover:border-white/30`
                    : `bg-blue-50/50 hover:bg-blue-50/80 ${isDragging ? 'border-blue-400/60 bg-blue-100/70 scale-[1.02]' : 'border-blue-300/40'} ${videos.length > 0 ? 'border-blue-500/60 bg-blue-100/60' : ''} hover:border-blue-400/60`
                  }
                `}
              >
                <div className={`absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${
                  theme === "dark"
                    ? "bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10"
                    : "bg-gradient-to-br from-blue-400/10 via-transparent to-cyan-400/10"
                }`}></div>
                
                <div className="relative flex flex-col items-center justify-center text-center">
                  <div className={`
                    mb-6 p-6 rounded-2xl transition-all duration-300
                    ${theme === "dark"
                      ? videos.length > 0
                        ? 'bg-purple-500/20 border-2 border-purple-400/40' 
                        : 'bg-white/10 border-2 border-white/20'
                      : videos.length > 0
                        ? 'bg-blue-500/20 border-2 border-blue-500/40'
                        : 'bg-blue-500/10 border-2 border-blue-300/30'
                    }
                  `}>
                    <Upload className={`w-12 h-12 transition-colors duration-300 ${
                      theme === "dark"
                        ? videos.length > 0 ? 'text-purple-300' : 'text-white/70'
                        : videos.length > 0 ? 'text-blue-600' : 'text-blue-500'
                    }`} />
                  </div>
                  
                  {videos.length > 0 ? (
                    <div>
                      <p className={`text-xl mb-2 ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
                        {videos.length} video{videos.length > 1 ? 's' : ''} uploaded
                      </p>
                      <p className={`text-sm ${theme === "dark" ? "text-white/50" : "text-gray-500"}`}>
                        Total: {(videos.reduce((sum, v) => sum + v.file.size, 0) / (1024 * 1024)).toFixed(2)} MB
                      </p>
                      <p className={`text-sm mt-3 ${theme === "dark" ? "text-purple-300" : "text-blue-600"}`}>
                        Click or drop to add more videos
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className={`text-xl mb-2 ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
                        Drop videos here or click to upload
                      </p>
                      <p className={`text-sm ${theme === "dark" ? "text-white/50" : "text-gray-500"}`}>
                        Supports multiple videos • MP4, MOV, AVI, and more
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Video Status List */}
            {videos.length > 0 && (
              <div className={`
                mb-8 p-6 rounded-3xl
                backdrop-blur-2xl border-2
                shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]
                ${theme === "dark"
                  ? "bg-white/5 border-white/20"
                  : "bg-white/60 border-blue-200/60"
                }
              `}>
                <h3 className={`text-lg font-semibold mb-4 ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}>
                  Processing Status
                </h3>
                
                <div className="space-y-3">
                  {videos.map((video) => (
                    <div
                      key={video.id}
                      className={`
                        p-4 rounded-xl border
                        transition-all duration-200
                        ${theme === "dark"
                          ? "bg-white/5 border-white/10 hover:bg-white/10"
                          : "bg-white/60 border-blue-200/30 hover:bg-white/80"
                        }
                      `}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div className={getStatusColor(video.status.status)}>
                            {getStatusIcon(video.status.status)}
                          </div>
                          <span className={`font-medium truncate ${
                            theme === "dark" ? "text-white" : "text-gray-900"
                          }`}>
                            {video.file.name}
                          </span>
                        </div>
                        <span className={`text-sm capitalize ${getStatusColor(video.status.status)}`}>
                          {video.status.status}
                        </span>
                      </div>
                      
                      {/* Progress bar for processing videos */}
                      {(video.status.status === "processing" || video.status.status === "pending") && typeof video.status.progress === 'number' && (
                        <div className={`h-2 rounded-full overflow-hidden ${
                          theme === "dark" ? "bg-white/10" : "bg-gray-200"
                        }`}>
                          <div 
                            className={`h-full rounded-full transition-all duration-300 ${
                              theme === "dark" 
                                ? "bg-gradient-to-r from-purple-500 to-blue-500" 
                                : "bg-gradient-to-r from-blue-500 to-cyan-500"
                            }`}
                            style={{ width: `${video.status.progress}%` }}
                          ></div>
                        </div>
                      )}
                      
                      {/* Error message */}
                      {video.status.status === "failed" && video.status.error_message && (
                        <p className={`text-sm mt-2 ${
                          theme === "dark" ? "text-red-400" : "text-red-600"
                        }`}>
                          {video.status.error_message}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Results Section - Only show if at least one video is completed */}
            {hasCompletedVideos && (
              <div className={`
                backdrop-blur-2xl
                border rounded-3xl
                p-8
                mb-64
                shadow-[0_8px_32px_0_rgba(0,0,0,0.37)]
                animate-in fade-in slide-in-from-bottom-4 duration-700
                ${theme === "dark"
                  ? "bg-white/5 border-white/20"
                  : "bg-white/60 border-blue-200/60"
                }
              `}>
                <h2 className={`text-2xl mb-6 flex items-center gap-2 ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}>
                  <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse"></div>
                  Analysis Results
                </h2>
                
                {/* Video Selector Dropdown */}
                <div className="mb-8">
                  <label className={`block text-sm font-medium mb-2 ${
                    theme === "dark" ? "text-white/80" : "text-gray-700"
                  }`}>
                    Select Video to Preview
                  </label>
                  <div className="relative">
                    <button
                      onClick={() => setShowVideoSelector(!showVideoSelector)}
                      className={`
                        w-full px-4 py-3 rounded-xl
                        backdrop-blur-xl border-2
                        flex items-center justify-between
                        transition-all duration-200
                        ${theme === "dark"
                          ? "bg-white/5 border-white/20 text-white hover:bg-white/10"
                          : "bg-white/60 border-blue-200/40 text-gray-900 hover:bg-white/80"
                        }
                      `}
                    >
                      <span className="truncate">
                        {selectedVideo ? selectedVideo.file.name : "Select a video"}
                      </span>
                      <ChevronDown className={`w-5 h-5 transition-transform ${
                        showVideoSelector ? "rotate-180" : ""
                      }`} />
                    </button>
                    
                    {showVideoSelector && (
                      <div className={`
                        absolute top-full left-0 right-0 mt-2
                        backdrop-blur-2xl border-2 rounded-xl
                        overflow-hidden shadow-[0_8px_32px_0_rgba(0,0,0,0.6)]
                        z-20
                        ${theme === "dark"
                          ? "bg-[#1a1a2e]/95 border-white/20"
                          : "bg-white/95 border-blue-200/60"
                        }
                      `}>
                        {videos.filter(v => v.status.status === "completed").map((video) => (
                          <button
                            key={video.id}
                            onClick={() => {
                              setSelectedVideoId(video.id);
                              setShowVideoSelector(false);
                            }}
                            className={`
                              w-full px-4 py-3 text-left
                              transition-all duration-200
                              ${selectedVideoId === video.id
                                ? theme === "dark"
                                  ? "bg-purple-500/20 text-white"
                                  : "bg-blue-500/20 text-gray-900"
                                : theme === "dark"
                                  ? "text-white hover:bg-white/10"
                                  : "text-gray-900 hover:bg-blue-50"
                              }
                            `}
                          >
                            <div className="truncate">{video.file.name}</div>
                            <div className={`text-xs mt-1 ${
                              theme === "dark" ? "text-white/60" : "text-gray-600"
                            }`}>
                              {(video.file.size / (1024 * 1024)).toFixed(2)} MB
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
                
                {/* Video Preview */}
                {selectedVideo && (
                  <div className="mb-8">
                    <div className={`
                      relative rounded-2xl overflow-hidden
                      backdrop-blur-xl
                      border-2
                      shadow-[0_8px_32px_0_rgba(0,0,0,0.4)]
                      ${theme === "dark"
                        ? "bg-black/40 border-white/20"
                        : "bg-gray-100/80 border-blue-200/40"
                      }
                    `}>
                      <video
                        src={
                          selectedVideo.status.status === "completed"
                            ? ApiService.getDownloadUrl(selectedVideo.id)
                            : selectedVideo.uploadedUrl
                        }
                        controls
                        className="w-full h-auto max-h-[400px] object-contain"
                      />
                      <div className={`absolute inset-0 pointer-events-none ${
                        theme === "dark"
                          ? "bg-gradient-to-t from-purple-900/10 to-transparent"
                          : "bg-gradient-to-t from-blue-900/5 to-transparent"
                      }`}></div>
                    </div>
                    {selectedVideo.status.status === "completed" && (
                      <p className={`text-xs mt-2 text-center ${
                        theme === "dark" ? "text-white/60" : "text-gray-500"
                      }`}>
                        Showing processed video from backend
                      </p>
                    )}
                  </div>
                )}
                
                {/* Analysis Results Section */}
                {resultsData && (
                  <div className={`
                    mb-8 p-6 rounded-2xl
                    backdrop-blur-xl border-2
                    shadow-[0_4px_16px_0_rgba(0,0,0,0.25)]
                    ${theme === "dark"
                      ? "bg-white/5 border-white/10"
                      : "bg-blue-50/50 border-blue-200/40"
                    }
                  `}>
                    <h3 className={`text-xl mb-6 font-semibold ${
                      theme === "dark" ? "text-white" : "text-gray-900"
                    }`}>
                      Analysis Results
                    </h3>

                    {/* Overall Score Card */}
                    <div className={`
                      mb-6 p-6 rounded-2xl
                      backdrop-blur-xl border-2
                      shadow-[0_4px_16px_0_rgba(0,0,0,0.3)]
                      ${theme === "dark"
                        ? "bg-gradient-to-br from-purple-500/20 via-white/5 to-blue-500/20 border-purple-400/40"
                        : "bg-gradient-to-br from-blue-500/20 via-white/60 to-cyan-500/20 border-blue-400/60"
                      }
                    `}>
                      <div className="text-center">
                        <p className={`text-sm mb-2 uppercase tracking-wider ${
                          theme === "dark" ? "text-white/60" : "text-gray-600"
                        }`}>
                          Overall Score
                        </p>
                        <div className="flex items-center justify-center gap-3 mb-2">
                          <span className={`text-5xl font-bold ${
                            theme === "dark" ? "text-white" : "text-gray-900"
                          }`}>
                            {resultsData.overall_score}
                          </span>
                          <span className={`text-3xl ${
                            theme === "dark" ? "text-white/40" : "text-gray-400"
                          }`}>
                            / {resultsData.max_score}
                          </span>
                        </div>
                        <div className={`text-2xl font-semibold ${
                          theme === "dark" ? "text-purple-300" : "text-blue-600"
                        }`}>
                          {resultsData.percentage.toFixed(1)}%
                        </div>
                      </div>
                    </div>
                    
                    {/* Categories Section with Pie Chart */}
                    {chartData.length > 0 && (
                      <div className={`
                        p-6 rounded-2xl
                        backdrop-blur-xl border-2
                        ${theme === "dark"
                          ? "bg-white/5 border-white/10"
                          : "bg-white/60 border-blue-200/30"
                        }
                      `}>
                        <h4 className={`text-lg font-semibold mb-6 ${
                          theme === "dark" ? "text-white" : "text-gray-900"
                        }`}>
                          Category Breakdown
                        </h4>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                          {/* Pie Chart */}
                          <div className="flex flex-col items-center justify-center">
                            <div className="w-full h-[350px]">
                              <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                  <Pie
                                    data={chartData}
                                    cx="50%"
                                    cy="50%"
                                    labelLine={false}
                                    label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                                    outerRadius={100}
                                    fill="#8884d8"
                                    dataKey="value"
                                  >
                                    {chartData.map((entry, index) => (
                                      <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                  </Pie>
                                  <Tooltip
                                    content={({ active, payload }) => {
                                      if (active && payload && payload.length) {
                                        const data = payload[0].payload;
                                        return (
                                          <div className={`
                                            p-4 rounded-xl border-2
                                            backdrop-blur-2xl
                                            shadow-2xl
                                            ${theme === "dark"
                                              ? "bg-[#1a1a2e]/95 border-white/20"
                                              : "bg-white/95 border-blue-200/60"
                                            }
                                          `}>
                                            <p className={`font-semibold mb-2 ${
                                              theme === "dark" ? "text-white" : "text-gray-900"
                                            }`}>
                                              {data.name}
                                            </p>
                                            <pre className={`text-xs whitespace-pre-wrap ${
                                              theme === "dark" ? "text-white/80" : "text-gray-700"
                                            }`}>
                                              {JSON.stringify(data.categoryData, null, 2)}
                                            </pre>
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
                            <div className="w-full mt-4 space-y-2">
                              {chartData.map((item, index) => (
                                <div key={index} className="flex items-center gap-2 text-sm">
                                  <div
                                    className="w-4 h-4 rounded-sm flex-shrink-0"
                                    style={{ backgroundColor: item.color }}
                                  ></div>
                                  <span className={`${
                                    theme === "dark" ? "text-white/80" : "text-gray-700"
                                  }`}>
                                    {item.name}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Category Details List */}
                          <div className="space-y-3 max-h-[400px] overflow-y-auto">
                            {resultsData?.categories.map((category, index) => (
                              <div
                                key={index}
                                className={`
                                  p-4 rounded-xl border-2
                                  transition-all duration-200
                                  hover:scale-[1.02]
                                  ${theme === "dark"
                                    ? "bg-white/5 border-white/10 hover:bg-white/10"
                                    : "bg-white/80 border-blue-200/40 hover:bg-white"
                                  }
                                `}
                              >
                                <div className="flex items-center gap-2 mb-2">
                                  <div
                                    className="w-3 h-3 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: categoryColors[index % categoryColors.length] }}
                                  ></div>
                                  <span className={`font-semibold ${
                                    theme === "dark" ? "text-white" : "text-gray-900"
                                  }`}>
                                    Category {index + 1}
                                  </span>
                                </div>
                                <pre className={`text-xs whitespace-pre-wrap ${
                                  theme === "dark" ? "text-white/70" : "text-gray-600"
                                }`}>
                                  {JSON.stringify(category, null, 2)}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>

                        <p className={`text-xs mt-4 text-center ${
                          theme === "dark" ? "text-white/50" : "text-gray-500"
                        }`}>
                          Hover over pie chart sections to see detailed category information
                        </p>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Save Buttons */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Save Video Button */}
                  <button
                    onClick={handleSaveVideo}
                    disabled={!selectedVideoId || selectedVideo?.status.status !== "completed"}
                    className={`
                      group w-full h-14 px-6
                      backdrop-blur-xl
                      border-2
                      rounded-2xl
                      transition-all duration-200
                      flex items-center justify-center gap-3
                      shadow-lg hover:shadow-xl
                      hover:scale-[1.02]
                      disabled:opacity-50 disabled:cursor-not-allowed
                      ${theme === "dark"
                        ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                        : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                      }
                    `}
                  >
                    <Download className="w-5 h-5 group-hover:animate-bounce" />
                    <span className="font-medium">Download Processed Video</span>
                  </button>

                  {/* Download Report PDF Button */}
                  <button
                    onClick={() => handleSaveReport("pdf")}
                    disabled={!selectedVideoId || !resultsData}
                    className={`
                      group w-full h-14 px-6
                      backdrop-blur-xl
                      border-2
                      rounded-2xl
                      transition-all duration-200
                      flex items-center justify-center gap-3
                      shadow-lg hover:shadow-xl
                      hover:scale-[1.02]
                      disabled:opacity-50 disabled:cursor-not-allowed
                      ${theme === "dark"
                        ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                        : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                      }
                    `}
                  >
                    <Download className="w-5 h-5 group-hover:animate-bounce" />
                    <span className="font-medium">Download Report (PDF)</span>
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Instructions Dialog */}
      <Dialog open={showInstructions} onOpenChange={setShowInstructions}>
        <DialogContent className={`
          max-w-2xl
          backdrop-blur-2xl
          border-2 rounded-3xl
          shadow-[0_8px_32px_0_rgba(0,0,0,0.6)]
          ${theme === "dark"
            ? "bg-[#1a1a2e]/95 border-white/20 text-white"
            : "bg-white/95 border-blue-200/60 text-gray-900"
          }
        `}>
          <DialogHeader>
            <DialogTitle className={`text-3xl mb-6 flex items-center gap-3 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}>
              <div className={`p-2 rounded-xl ${
                theme === "dark" ? "bg-purple-500/20" : "bg-blue-500/20"
              }`}>
                <HelpCircle className={`w-6 h-6 ${
                  theme === "dark" ? "text-purple-300" : "text-blue-600"
                }`} />
              </div>
              How to Use Video Processor
            </DialogTitle>
            <DialogDescription className="sr-only">
              Step-by-step instructions for using the video processor application
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-6 mt-4">
            <div className={`p-5 rounded-2xl border-2 ${
              theme === "dark"
                ? "bg-white/5 border-white/10"
                : "bg-blue-50/50 border-blue-200/40"
            }`}>
              <div className="flex gap-4">
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  theme === "dark"
                    ? "bg-purple-500/30 text-purple-300"
                    : "bg-blue-500/30 text-blue-700"
                }`}>
                  1
                </div>
                <div>
                  <h3 className={`font-semibold mb-2 ${
                    theme === "dark" ? "text-white" : "text-gray-900"
                  }`}>
                    Choose Your Activity
                  </h3>
                  <p className={`text-sm ${
                    theme === "dark" ? "text-white/70" : "text-gray-600"
                  }`}>
                    Select either Handstand or Straddle Jump to begin your analysis.
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-5 rounded-2xl border-2 ${
              theme === "dark"
                ? "bg-white/5 border-white/10"
                : "bg-blue-50/50 border-blue-200/40"
            }`}>
              <div className="flex gap-4">
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  theme === "dark"
                    ? "bg-purple-500/30 text-purple-300"
                    : "bg-blue-500/30 text-blue-700"
                }`}>
                  2
                </div>
                <div>
                  <h3 className={`font-semibold mb-2 ${
                    theme === "dark" ? "text-white" : "text-gray-900"
                  }`}>
                    Upload Your Videos
                  </h3>
                  <p className={`text-sm ${
                    theme === "dark" ? "text-white/70" : "text-gray-600"
                  }`}>
                    Click the upload area or drag and drop multiple video files. Videos will automatically start processing.
                  </p>
                </div>
              </div>
            </div>

            <div className={`p-5 rounded-2xl border-2 ${
              theme === "dark"
                ? "bg-white/5 border-white/10"
                : "bg-blue-50/50 border-blue-200/40"
            }`}>
              <div className="flex gap-4">
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold ${
                  theme === "dark"
                    ? "bg-purple-500/30 text-purple-300"
                    : "bg-blue-500/30 text-blue-700"
                }`}>
                  3
                </div>
                <div>
                  <h3 className={`font-semibold mb-2 ${
                    theme === "dark" ? "text-white" : "text-gray-900"
                  }`}>
                    Review & Export
                  </h3>
                  <p className={`text-sm ${
                    theme === "dark" ? "text-white/70" : "text-gray-600"
                  }`}>
                    Monitor processing status, preview completed videos, and download results in your preferred format.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className={`mt-8 p-4 rounded-2xl border ${
            theme === "dark"
              ? "bg-purple-500/10 border-purple-500/30"
              : "bg-blue-500/10 border-blue-500/30"
          }`}>
            <p className={`text-sm ${
              theme === "dark" ? "text-purple-200" : "text-blue-700"
            }`}>
              💡 <strong>Tip:</strong> All processing happens securely and your videos are never stored on our servers.
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
