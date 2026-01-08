import { useState, useRef } from "react";
import { Upload, Download, Video, Sun, Moon, HelpCircle, Star, User, ArrowLeft } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./components/ui/dialog";
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from "recharts";
import { ApiService, AnalysisResult, CategoryScore } from "./services/api";

export default function App() {
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isProcessed, setIsProcessed] = useState(false);
  const [exportFormat, setExportFormat] = useState("mp4");
  const [reportFormat, setReportFormat] = useState("pdf");
  const [isDragging, setIsDragging] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const [showInstructions, setShowInstructions] = useState(false);
  const [selectedOption, setSelectedOption] = useState<number | null>(null);
  const [showVideoDropdown, setShowVideoDropdown] = useState(false);
  const [showReportDropdown, setShowReportDropdown] = useState(false);
  const [videoId, setVideoId] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Use API results if available, otherwise use mock data
  const resultsData = analysisResult
    ? analysisResult.categories
    : [
        { name: "Starting position", score: 15, maxScore: 20 },
        { name: "Swing-up", score: 16, maxScore: 20 },
        { name: "Hand placement", score: 18, maxScore: 20 },
        { name: "Body posture during handstand", score: 14, maxScore: 20 },
        { name: "Landing & finishing", score: 17, maxScore: 20 },
      ];

  // Calculate total room for improvement
  const totalRoomForImprovement = resultsData.reduce(
    (sum, item) => sum + (item.maxScore - item.score), 
    0
  );

  // Prepare data for pie chart - individual scores + combined remaining
  const chartData = [
    ...resultsData.map(item => ({
      name: item.name,
      value: item.score,
      type: 'achieved',
      fullName: `${item.name}: ${item.score}/${item.maxScore}`
    })),
    {
      name: "Room for improvement",
      value: totalRoomForImprovement,
      type: 'remaining',
      fullName: `Room for improvement: ${totalRoomForImprovement} points`
    }
  ];

  // Colors for each category in the pie chart
  const categoryColors = theme === "dark" 
    ? ["#a78bfa", "#818cf8", "#60a5fa", "#34d399", "#fbbf24"]
    : ["#7c3aed", "#4f46e5", "#2563eb", "#059669", "#d97706"];
  
  const remainingColor = theme === "dark" ? "#374151" : "#d1d5db";

  // Map colors to chart data
  const getColor = (index: number) => {
    if (index < categoryColors.length) {
      return categoryColors[index];
    }
    return remainingColor; // Last segment is room for improvement
  };

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const handleOptionSelect = (option: number) => {
    setSelectedOption(option);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Check file extension instead of MIME type (more reliable for .mov files)
      const validExtensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

      if (validExtensions.includes(fileExt) || file.type.startsWith("video/")) {
        setVideoFile(file);
        setIsProcessed(false);
        setError(null);
        setVideoUrl(URL.createObjectURL(file));

        // Upload video immediately
        try {
          const response = await ApiService.uploadVideo(file);
          setVideoId(response.video_id);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Upload failed");
          console.error("Upload error:", err);
        }
      } else {
        setError("Please upload a valid video file (MP4, MOV, AVI, WebM, MKV)");
      }
    }
  };

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
    const file = e.dataTransfer.files?.[0];
    if (file) {
      // Check file extension instead of MIME type (more reliable for .mov files)
      const validExtensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv'];
      const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

      if (validExtensions.includes(fileExt) || file.type.startsWith("video/")) {
        setVideoFile(file);
        setIsProcessed(false);
        setError(null);
        setVideoUrl(URL.createObjectURL(file));

        // Upload video immediately
        try {
          const response = await ApiService.uploadVideo(file);
          setVideoId(response.video_id);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Upload failed");
          console.error("Upload error:", err);
        }
      } else {
        setError("Please upload a valid video file (MP4, MOV, AVI, WebM, MKV)");
      }
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleProcess = async () => {
    if (!videoFile || !videoId || !selectedOption) return;

    setIsProcessing(true);
    setError(null);

    try {
      // Process video with selected option
      const result = await ApiService.processVideo(videoId, selectedOption);
      setAnalysisResult(result);

      // Get processed video URL
      const processedUrl = await ApiService.getProcessedVideo(videoId);
      setVideoUrl(processedUrl);

      setIsProcessed(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Processing failed");
      console.error("Processing error:", err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSave = async (format: string) => {
    if (!videoId) return;

    try {
      const response = await ApiService.exportVideo(videoId, format);
      ApiService.downloadFile(response.download_url, response.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
      console.error("Export error:", err);
    }
  };

  const handleSaveReport = async (format: string) => {
    if (!videoId) return;

    try {
      const response = await ApiService.exportReport(videoId, format);
      ApiService.downloadFile(response.download_url, response.filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Report generation failed");
      console.error("Report error:", err);
    }
  };

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
        {/* Option Selection Screen - Shows first */}
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
              {/* Option 1 */}
              <button
                onClick={() => handleOptionSelect(1)}
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
                {/* Icon Container */}
                <div className="flex justify-center mb-8">
                  <div className={`
                    p-6 rounded-2xl border-2 transition-all duration-300
                    ${theme === "dark"
                      ? "bg-white/10 border-white/20 group-hover:bg-purple-500/20 group-hover:border-purple-400/40"
                      : "bg-white/60 border-blue-200/40 group-hover:bg-blue-500/20 group-hover:border-blue-500/40"
                    }
                  `}>
                    <Star className={`w-12 h-12 ${
                      theme === "dark" ? "text-white/70 group-hover:text-purple-300" : "text-blue-500 group-hover:text-blue-600"
                    }`} strokeWidth={1.5} />
                  </div>
                </div>
                
                {/* Title */}
                <p className={`text-xl font-medium ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}>
                  Option 1
                </p>
                
                {/* Hover Glow */}
                <div className={`absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none ${
                  theme === "dark"
                    ? "bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10"
                    : "bg-gradient-to-br from-blue-400/10 via-transparent to-cyan-400/10"
                }`}></div>
              </button>

              {/* Option 2 */}
              <button
                onClick={() => handleOptionSelect(2)}
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
                {/* Icon Container */}
                <div className="flex justify-center mb-8">
                  <div className={`
                    p-6 rounded-2xl border-2 transition-all duration-300
                    ${theme === "dark"
                      ? "bg-white/10 border-white/20 group-hover:bg-purple-500/20 group-hover:border-purple-400/40"
                      : "bg-white/60 border-blue-200/40 group-hover:bg-blue-500/20 group-hover:border-blue-500/40"
                    }
                  `}>
                    <User className={`w-12 h-12 ${
                      theme === "dark" ? "text-white/70 group-hover:text-purple-300" : "text-blue-500 group-hover:text-blue-600"
                    }`} strokeWidth={1.5} />
                  </div>
                </div>
                
                {/* Title */}
                <p className={`text-xl font-medium ${
                  theme === "dark" ? "text-white" : "text-gray-900"
                }`}>
                  Option 2
                </p>
                
                {/* Hover Glow */}
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
                setVideoFile(null);
                setIsProcessed(false);
                setVideoUrl(null);
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

            {/* Upload Interface - Shows after option selection */}
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

            {/* Upload Area */}
            <div className="mb-8">
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*"
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
                    ? `bg-white/5 hover:bg-white/10 ${isDragging ? 'border-purple-400/60 bg-white/15 scale-[1.02]' : 'border-white/20'} ${videoFile ? 'border-purple-400/40 bg-purple-500/10' : ''} hover:border-white/30`
                    : `bg-blue-50/50 hover:bg-blue-50/80 ${isDragging ? 'border-blue-400/60 bg-blue-100/70 scale-[1.02]' : 'border-blue-300/40'} ${videoFile ? 'border-blue-500/60 bg-blue-100/60' : ''} hover:border-blue-400/60`
                  }
                `}
              >
                {/* Subtle glow effect */}
                <div className={`absolute inset-0 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-500 ${
                  theme === "dark"
                    ? "bg-gradient-to-br from-purple-500/10 via-transparent to-blue-500/10"
                    : "bg-gradient-to-br from-blue-400/10 via-transparent to-cyan-400/10"
                }`}></div>
                
                <div className="relative flex flex-col items-center justify-center text-center">
                  <div className={`
                    mb-6 p-6 rounded-2xl transition-all duration-300
                    ${theme === "dark"
                      ? videoFile 
                        ? 'bg-purple-500/20 border-2 border-purple-400/40' 
                        : 'bg-white/10 border-2 border-white/20'
                      : videoFile
                        ? 'bg-blue-500/20 border-2 border-blue-500/40'
                        : 'bg-blue-500/10 border-2 border-blue-300/30'
                    }
                  `}>
                    <Upload className={`w-12 h-12 transition-colors duration-300 ${
                      theme === "dark"
                        ? videoFile ? 'text-purple-300' : 'text-white/70'
                        : videoFile ? 'text-blue-600' : 'text-blue-500'
                    }`} />
                  </div>
                  
                  {videoFile ? (
                    <div>
                      <p className={`text-xl mb-2 ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
                        {videoFile.name}
                      </p>
                      <p className={`text-sm ${theme === "dark" ? "text-white/50" : "text-gray-500"}`}>
                        {(videoFile.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                      <p className={`text-sm mt-3 ${theme === "dark" ? "text-purple-300" : "text-blue-600"}`}>
                        Click or drop to replace
                      </p>
                    </div>
                  ) : (
                    <div>
                      <p className={`text-xl mb-2 ${theme === "dark" ? "text-white" : "text-gray-900"}`}>
                        Drop video here or click to upload
                      </p>
                      <p className={`text-sm ${theme === "dark" ? "text-white/50" : "text-gray-500"}`}>
                        Supports MP4, MOV, AVI, and more
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className={`mb-8 p-4 rounded-2xl border-2 ${
                theme === "dark"
                  ? "bg-red-500/10 border-red-500/40 text-red-300"
                  : "bg-red-50 border-red-300 text-red-700"
              }`}>
                <p className="font-medium">⚠️ Error: {error}</p>
              </div>
            )}

            {/* Process Button */}
            {videoFile && !isProcessed && (
              <div className="mb-12 flex justify-center">
                <button
                  onClick={handleProcess}
                  disabled={isProcessing}
                  className={`
                    group relative px-10 py-4 rounded-full
                    text-white font-medium text-lg
                    transition-all duration-300
                    hover:scale-105
                    disabled:opacity-50 disabled:cursor-not-allowed
                    disabled:hover:scale-100
                    border border-white/20
                    ${theme === "dark"
                      ? "bg-gradient-to-r from-purple-600 via-purple-500 to-blue-600 shadow-[0_0_40px_rgba(139,92,246,0.4)] hover:shadow-[0_0_60px_rgba(139,92,246,0.6)]"
                      : "bg-gradient-to-r from-blue-500 via-blue-600 to-cyan-500 shadow-[0_0_40px_rgba(59,130,246,0.4)] hover:shadow-[0_0_60px_rgba(59,130,246,0.6)]"
                    }
                  `}
                >
                  <span className="relative z-10 flex items-center gap-2">
                    {isProcessing ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                        Processing...
                      </>
                    ) : (
                      <>
                        <Video className="w-5 h-5" />
                        Process Video
                      </>
                    )}
                  </span>
                  <div className={`absolute inset-0 rounded-full opacity-0 group-hover:opacity-20 blur-xl transition-opacity duration-300 ${
                    theme === "dark"
                      ? "bg-gradient-to-r from-purple-400 to-blue-400"
                      : "bg-gradient-to-r from-blue-400 to-cyan-400"
                  }`}></div>
                </button>
              </div>
            )}

            {/* Results Section */}
            {isProcessed && (
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
                  Processing Complete
                </h2>
                
                {/* Video Preview */}
                {videoUrl && (
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
                        key={videoUrl}
                        src={videoUrl}
                        controls
                        controlsList="nodownload"
                        className="w-full h-auto max-h-[400px] object-contain bg-black"
                        onError={(e) => {
                          console.error("Video load error:", e);
                          setError("Failed to load video. Please try again.");
                        }}
                      >
                        Your browser does not support the video tag.
                      </video>
                      {/* Subtle overlay gradient */}
                      <div className={`absolute inset-0 pointer-events-none ${
                        theme === "dark"
                          ? "bg-gradient-to-t from-purple-900/10 to-transparent"
                          : "bg-gradient-to-t from-blue-900/5 to-transparent"
                      }`}></div>
                    </div>
                  </div>
                )}
                
                {/* Analysis Results Section */}
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
                          {resultsData.reduce((sum, item) => sum + item.score, 0)}
                        </span>
                        <span className={`text-3xl ${
                          theme === "dark" ? "text-white/40" : "text-gray-400"
                        }`}>
                          / {resultsData.reduce((sum, item) => sum + item.maxScore, 0)}
                        </span>
                      </div>
                      <div className={`text-2xl font-semibold ${
                        theme === "dark" ? "text-purple-300" : "text-blue-600"
                      }`}>
                        {Math.round((resultsData.reduce((sum, item) => sum + item.score, 0) / 
                          resultsData.reduce((sum, item) => sum + item.maxScore, 0)) * 100)}%
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* Text Results */}
                    <div className="space-y-4">
                      {resultsData.map((item, index) => (
                        <div 
                          key={index}
                          className={`
                            p-4 rounded-xl border
                            transition-all duration-200
                            hover:scale-[1.02]
                            ${theme === "dark"
                              ? "bg-white/5 border-white/10 hover:bg-white/10"
                              : "bg-white/60 border-blue-200/30 hover:bg-white/80"
                            }
                          `}
                        >
                          <div className="flex justify-between items-center mb-2">
                            <span className={`font-medium ${
                              theme === "dark" ? "text-white" : "text-gray-900"
                            }`}>
                              {item.name}
                            </span>
                            <span className={`text-lg font-semibold ${
                              theme === "dark" ? "text-purple-300" : "text-blue-600"
                            }`}>
                              {item.score}/{item.maxScore}
                            </span>
                          </div>
                          {/* Progress bar */}
                          <div className={`h-2 rounded-full overflow-hidden ${
                            theme === "dark" ? "bg-white/10" : "bg-gray-200"
                          }`}>
                            <div 
                              className={`h-full rounded-full transition-all duration-500 ${
                                theme === "dark" 
                                  ? "bg-gradient-to-r from-purple-500 to-blue-500" 
                                  : "bg-gradient-to-r from-blue-500 to-cyan-500"
                              }`}
                              style={{ width: `${(item.score / item.maxScore) * 100}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                    
                    {/* Pie Chart */}
                    <div className="flex flex-col items-center justify-center">
                      <div className="w-full h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <PieChart>
                            <Pie
                              data={chartData}
                              cx="50%"
                              cy="50%"
                              innerRadius={60}
                              outerRadius={100}
                              paddingAngle={2}
                              dataKey="value"
                            >
                              {chartData.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={getColor(index)} />
                              ))}
                            </Pie>
                            <Tooltip 
                              contentStyle={{
                                backgroundColor: theme === "dark" ? "rgba(26, 26, 46, 0.95)" : "rgba(255, 255, 255, 0.95)",
                                border: theme === "dark" ? "2px solid rgba(255, 255, 255, 0.2)" : "2px solid rgba(59, 130, 246, 0.3)",
                                borderRadius: "12px",
                                backdropFilter: "blur(10px)",
                              }}
                              itemStyle={{
                                color: theme === "dark" ? "#ffffff" : "#1f2937",
                              }}
                              labelStyle={{
                                color: theme === "dark" ? "#ffffff" : "#1f2937",
                              }}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      
                      {/* Custom Legend */}
                      <div className="w-full mt-4 space-y-2">
                        {resultsData.map((item, index) => (
                          <div key={index} className="flex items-center gap-2 text-sm">
                            <div 
                              className="w-3 h-3 rounded-sm flex-shrink-0"
                              style={{ backgroundColor: categoryColors[index] }}
                            ></div>
                            <span className={`truncate ${
                              theme === "dark" ? "text-white/80" : "text-gray-700"
                            }`}>
                              {item.name}
                            </span>
                          </div>
                        ))}
                        <div className="flex items-center gap-2 text-sm pt-2 border-t border-white/10">
                          <div 
                            className="w-3 h-3 rounded-sm flex-shrink-0"
                            style={{ backgroundColor: remainingColor }}
                          ></div>
                          <span className={`${
                            theme === "dark" ? "text-white/60" : "text-gray-500"
                          }`}>
                            Room for improvement
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Side-by-Side Save Buttons with Dropdowns */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Save Video Button with Dropdown */}
                  <div className="relative">
                    <button
                      onClick={() => {
                        setShowVideoDropdown(!showVideoDropdown);
                        setShowReportDropdown(false);
                      }}
                      className={`
                        group w-full h-14 px-6
                        backdrop-blur-xl
                        border-2
                        rounded-2xl
                        transition-all duration-200
                        flex items-center justify-center gap-3
                        shadow-lg hover:shadow-xl
                        hover:scale-[1.02]
                        ${theme === "dark"
                          ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                          : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                        }
                      `}
                    >
                      <Download className="w-5 h-5 group-hover:animate-bounce" />
                      <span className="font-medium">Save Video</span>
                    </button>

                    {/* Video Dropdown Menu */}
                    {showVideoDropdown && (
                      <div className={`
                        absolute top-full left-0 right-0 mt-2
                        backdrop-blur-2xl
                        border-2 rounded-2xl
                        overflow-hidden
                        shadow-[0_8px_32px_0_rgba(0,0,0,0.6)]
                        z-10
                        ${theme === "dark"
                          ? "bg-[#1a1a2e]/95 border-white/20"
                          : "bg-white/95 border-blue-200/60"
                        }
                      `}>
                        <button
                          onClick={() => {
                            setExportFormat("mp4");
                            handleSave("mp4");
                            setShowVideoDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">MP4</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            High Compatibility
                          </div>
                        </button>
                        <button
                          onClick={() => {
                            setExportFormat("mov");
                            handleSave("mov");
                            setShowVideoDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">MOV</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            Apple ProRes
                          </div>
                        </button>
                        <button
                          onClick={() => {
                            setExportFormat("gif");
                            handleSave("gif");
                            setShowVideoDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">GIF</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            Animated Image
                          </div>
                        </button>
                        <button
                          onClick={() => {
                            setExportFormat("webm");
                            handleSave("webm");
                            setShowVideoDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">WebM</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            Web Optimized
                          </div>
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Save Report Button with Dropdown */}
                  <div className="relative">
                    <button
                      onClick={() => {
                        setShowReportDropdown(!showReportDropdown);
                        setShowVideoDropdown(false);
                      }}
                      className={`
                        group w-full h-14 px-6
                        backdrop-blur-xl
                        border-2
                        rounded-2xl
                        transition-all duration-200
                        flex items-center justify-center gap-3
                        shadow-lg hover:shadow-xl
                        hover:scale-[1.02]
                        ${theme === "dark"
                          ? "bg-white/10 border-white/20 text-white hover:bg-white/15 hover:border-white/30"
                          : "bg-blue-500/10 border-blue-500/30 text-gray-900 hover:bg-blue-500/20 hover:border-blue-500/50"
                        }
                      `}
                    >
                      <Download className="w-5 h-5 group-hover:animate-bounce" />
                      <span className="font-medium">Save Report</span>
                    </button>

                    {/* Report Dropdown Menu */}
                    {showReportDropdown && (
                      <div className={`
                        absolute top-full left-0 right-0 mt-2
                        backdrop-blur-2xl
                        border-2 rounded-2xl
                        overflow-hidden
                        shadow-[0_8px_32px_0_rgba(0,0,0,0.6)]
                        z-10
                        ${theme === "dark"
                          ? "bg-[#1a1a2e]/95 border-white/20"
                          : "bg-white/95 border-blue-200/60"
                        }
                      `}>
                        <button
                          onClick={() => {
                            setReportFormat("pdf");
                            handleSaveReport("pdf");
                            setShowReportDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">PDF</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            Portable Document Format
                          </div>
                        </button>
                        <button
                          onClick={() => {
                            setReportFormat("docx");
                            handleSaveReport("docx");
                            setShowReportDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">DOCX</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            Microsoft Word Document
                          </div>
                        </button>
                        <button
                          onClick={() => {
                            setReportFormat("xlsx");
                            handleSaveReport("xlsx");
                            setShowReportDropdown(false);
                          }}
                          className={`
                            w-full px-4 py-3 text-left
                            transition-all duration-200
                            ${theme === "dark"
                              ? "text-white hover:bg-white/10"
                              : "text-gray-900 hover:bg-blue-50"
                            }
                          `}
                        >
                          <div className="font-medium">XLSX</div>
                          <div className={`text-sm ${theme === "dark" ? "text-white/60" : "text-gray-600"}`}>
                            Microsoft Excel Spreadsheet
                          </div>
                        </button>
                      </div>
                    )}
                  </div>
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
            {/* Step 1 */}
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
                    Upload Your Video
                  </h3>
                  <p className={`text-sm ${
                    theme === "dark" ? "text-white/70" : "text-gray-600"
                  }`}>
                    Click the upload area or drag and drop your video file. Supported formats include MP4, MOV, AVI, and more.
                  </p>
                </div>
              </div>
            </div>

            {/* Step 2 */}
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
                    Process the Video
                  </h3>
                  <p className={`text-sm ${
                    theme === "dark" ? "text-white/70" : "text-gray-600"
                  }`}>
                    Click the "Process Video" button to start AI-powered analysis. The processing typically takes a few seconds.
                  </p>
                </div>
              </div>
            </div>

            {/* Step 3 */}
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
                    Preview the processed video, then choose your export format (MP4, MOV, GIF, WebM) and save. You can also download the analysis report in PDF, DOCX, or XLSX format.
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