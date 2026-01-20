import { useState, useRef } from "react";
import { Upload, Download, Video, Sun, Moon, HelpCircle, ArrowLeft, CheckCircle, XCircle, Loader, ChevronDown, AlertCircle } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./components/ui/dialog";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { ApiService, StatusResponse, AnalysisResult, Pose } from "./services/api";

// Handstand SVG Icon Component
const HandstandIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 3000 3000" xmlns="http://www.w3.org/2000/svg">
    <path fillRule="nonzero" fill="currentColor" d="M 946.203125 2260.960938 C 890.367188 2393.160156 952.273438 2545.59375 1084.46875 2601.433594 C 1216.671875 2657.269531 1369.109375 2595.363281 1424.949219 2463.164062 C 1480.78125 2330.964844 1418.878906 2178.527344 1286.679688 2122.691406 C 1154.480469 2066.855469 1002.039062 2128.757812 946.203125 2260.960938 "/>
    <path fillRule="nonzero" fill="currentColor" d="M 1101.671875 1818.789062 C 1068.640625 1896.988281 1105.261719 1987.160156 1183.460938 2020.191406 L 1463.289062 2138.382812 C 1541.488281 2171.410156 1631.660156 2134.792969 1664.691406 2056.589844 L 1929.910156 1428.648438 C 1962.941406 1350.449219 1926.328125 1260.28125 1848.121094 1227.25 L 1568.300781 1109.058594 C 1490.101562 1076.03125 1399.921875 1112.648438 1366.890625 1190.851562 L 1101.671875 1818.789062 "/>
    <path fill="none" strokeWidth="2824.53" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor" strokeMiterlimit="10" d="M 15077.617188 17700.78125 L 15651.601562 27282.5 " transform="matrix(0.1, 0, 0, -0.1, 0, 3000)"/>
    <path fill="none" strokeWidth="2824.53" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor" strokeMiterlimit="10" d="M 18091.992188 16427.617188 L 21774.6875 25146.71875 " transform="matrix(0.1, 0, 0, -0.1, 0, 3000)"/>
    <path fill="none" strokeWidth="2259.63" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor" strokeMiterlimit="10" d="M 15612.8125 9527.890625 L 17543.007812 6038.945312 L 17439.804688 2340.859375 " transform="matrix(0.1, 0, 0, -0.1, 0, 3000)"/>
    <path fill="none" strokeWidth="2259.63" strokeLinecap="round" strokeLinejoin="round" stroke="currentColor" strokeMiterlimit="10" d="M 11978.515625 11062.890625 L 8601.367188 12322.382812 L 5549.0625 12099.804688 " transform="matrix(0.1, 0, 0, -0.1, 0, 3000)"/>
  </svg>
);

interface VideoUpload {
  id: string;
  file: File;
  uploadedUrl: string;
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

  // Monochromatic chart colors with accent
  const poseColors = theme === "dark"
    ? ["#00b4d8", "#f2f2f2", "#999999", "#666666", "#404040", "#cccccc", "#808080"]
    : ["#00b4d8", "#1a1a1a", "#666666", "#999999", "#cccccc", "#404040", "#808080"];

  // Flatten all poses from all categories for display
  const allPoses: (Pose & { color: string })[] = resultsData?.categories
    ? resultsData.categories.flatMap((category) =>
        category.poses.map((pose, poseIndex) => {
          const globalIndex = resultsData.categories
            .slice(0, resultsData.categories.indexOf(category))
            .reduce((sum, cat) => sum + cat.poses.length, 0) + poseIndex;

          return {
            ...pose,
            color: poseColors[globalIndex % poseColors.length]
          };
        })
      )
    : [];

  // Calculate total possible points and current points
  const totalMaxScore = allPoses.reduce((sum, pose) => sum + pose.max_score, 0);
  const totalCurrentScore = allPoses.reduce((sum, pose) => sum + pose.score, 0);
  const roomForImprovement = totalMaxScore - totalCurrentScore;

  // Number of categories including "Room for Improvement"
  const numberOfCategories = allPoses.length + 1;
  const percentagePerCategory = 100 / numberOfCategories;

  // Prepare chart data from flattened poses with equal distribution
  const chartData = [
    ...allPoses.map((pose) => ({
      name: pose.name,
      value: percentagePerCategory,
      actualScore: pose.score,
      maxScore: pose.max_score,
      poseData: pose,
      color: pose.color
    })),
    {
      name: "Room for Improvement",
      value: percentagePerCategory,
      actualScore: roomForImprovement,
      maxScore: totalMaxScore,
      poseData: null,
      color: theme === "dark" ? "#333333" : "#e5e5e5"
    }
  ];

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  const handleOptionSelect = (option: string) => {
    setSelectedOption(option);
  };

  const pollVideoStatus = async (videoId: string) => {
    try {
      const status = await ApiService.pollUntilComplete(videoId, 2000);

      setVideos(prev => prev.map(v =>
        v.id === videoId ? { ...v, status } : v
      ));

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

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file && file.type.startsWith("video/")) {
        try {
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

          await ApiService.startProcessing(videoId, selectedOption || "handstand");
          pollVideoStatus(videoId);
        } catch (error) {
          console.error("Error uploading video:", error);
          alert(error instanceof Error ? error.message : "Failed to upload video");
        }
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

    const files = e.dataTransfer.files;
    if (!files) return;

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      if (file && file.type.startsWith("video/")) {
        try {
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

          await ApiService.startProcessing(videoId, selectedOption || "handstand");
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-[#00b4d8]";
      case "failed":
        return theme === "dark" ? "text-red-400" : "text-red-600";
      case "processing":
        return theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]";
      default:
        return theme === "dark" ? "text-[#999999]" : "text-[#666666]";
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
    <div className={`min-h-screen relative transition-colors duration-300 ${theme === "dark" ? "dark bg-[#141414]" : "bg-[#fafafa]"}`}>
      {/* Subtle grid background */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: theme === "dark"
            ? 'linear-gradient(90deg, #f2f2f2 1px, transparent 1px), linear-gradient(#f2f2f2 1px, transparent 1px)'
            : 'linear-gradient(90deg, #1a1a1a 1px, transparent 1px), linear-gradient(#1a1a1a 1px, transparent 1px)',
          backgroundSize: '40px 40px'
        }}
      />

      {/* Theme Toggle Button */}
      <button
        onClick={toggleTheme}
        className={`
          fixed top-6 right-6 z-50 p-3
          border-2 transition-all duration-200
          hover:-translate-y-0.5
          ${theme === "dark"
            ? "bg-[#1a1a1a] border-[#404040] hover:border-[#00b4d8]"
            : "bg-white border-[#d4d4d4] hover:border-[#00b4d8]"
          }
        `}
      >
        {theme === "dark" ? (
          <Sun className="w-5 h-5 text-[#f2f2f2]" />
        ) : (
          <Moon className="w-5 h-5 text-[#1a1a1a]" />
        )}
      </button>

      {/* Main Content */}
      <div className="relative z-10 container mx-auto px-6 py-12 max-w-5xl">
        {/* Option Selection Screen */}
        {selectedOption === null ? (
          <>
            {/* Header */}
            <header className="mb-16">
              <div className="flex items-center gap-4 mb-6">
                <div className={`p-3 border-2 ${theme === "dark" ? "border-[#00b4d8] bg-[#00b4d8]/10" : "border-[#00b4d8] bg-[#00b4d8]/5"}`}>
                  <Video className="w-8 h-8 text-[#00b4d8]" />
                </div>
                <div className={`h-[2px] flex-1 ${theme === "dark" ? "bg-[#404040]" : "bg-[#d4d4d4]"}`} />
              </div>

              <h1 className={`text-4xl md:text-5xl font-black tracking-tight mb-4 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}
                style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                GYMNASTICS<br />ANALYSIS
              </h1>

              <p className={`text-lg mb-6 max-w-md ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}
                style={{ fontFamily: "'DM Sans', sans-serif" }}>
                AI-powered movement analysis for gymnastics training
              </p>

              {/* How to Use Button */}
              <button
                onClick={() => setShowInstructions(true)}
                className={`
                  inline-flex items-center gap-2 px-6 py-3
                  border-2 transition-all duration-200
                  hover:-translate-y-0.5
                  ${theme === "dark"
                    ? "bg-transparent border-[#404040] text-[#f2f2f2] hover:border-[#00b4d8]"
                    : "bg-transparent border-[#d4d4d4] text-[#1a1a1a] hover:border-[#00b4d8]"
                  }
                `}
              >
                <HelpCircle className="w-4 h-4" />
                <span className="text-sm font-bold uppercase tracking-wider">How to Use</span>
              </button>
            </header>

            {/* Exercise Selection */}
            <section className="mb-16">
              <div className={`border-t-4 pt-8 ${theme === "dark" ? "border-[#f2f2f2]" : "border-[#1a1a1a]"}`}>
                <h2 className={`text-sm font-bold uppercase tracking-wider mb-8 ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                  Select Exercise Type
                </h2>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Handstand Option */}
                  <button
                    onClick={() => handleOptionSelect("handstand")}
                    className={`
                      group relative
                      border-2 p-8
                      text-left transition-all duration-200
                      hover:-translate-y-1
                      ${theme === "dark"
                        ? "bg-[#1a1a1a] border-[#404040] hover:border-[#00b4d8]"
                        : "bg-white border-[#d4d4d4] hover:border-[#00b4d8]"
                      }
                    `}
                  >
                    <div className={`
                      mb-6 p-4 border-2 inline-block transition-colors duration-200
                      ${theme === "dark"
                        ? "border-[#404040] group-hover:border-[#00b4d8] group-hover:bg-[#00b4d8]/10"
                        : "border-[#d4d4d4] group-hover:border-[#00b4d8] group-hover:bg-[#00b4d8]/5"
                      }
                    `}>
                      <HandstandIcon className={`w-10 h-10 transition-colors duration-200 ${
                        theme === "dark"
                          ? "text-[#f2f2f2] group-hover:text-[#00b4d8]"
                          : "text-[#1a1a1a] group-hover:text-[#00b4d8]"
                      }`} />
                    </div>

                    <h3 className={`text-2xl font-black uppercase tracking-tight mb-2 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}
                      style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                      Handstand
                    </h3>
                    <p className={`text-sm ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                      Analyze handstand form and balance
                    </p>

                    {/* Accent line on hover */}
                    <div className="absolute bottom-0 left-0 w-0 h-1 bg-[#00b4d8] transition-all duration-200 group-hover:w-full" />
                  </button>

                  {/* Straddle Jump Option */}
                  <button
                    onClick={() => handleOptionSelect("straddle_jump")}
                    className={`
                      group relative
                      border-2 p-8
                      text-left transition-all duration-200
                      hover:-translate-y-1
                      ${theme === "dark"
                        ? "bg-[#1a1a1a] border-[#404040] hover:border-[#00b4d8]"
                        : "bg-white border-[#d4d4d4] hover:border-[#00b4d8]"
                      }
                    `}
                  >
                    <div className={`
                      mb-6 p-4 border-2 inline-block transition-colors duration-200
                      ${theme === "dark"
                        ? "border-[#404040] group-hover:border-[#00b4d8] group-hover:bg-[#00b4d8]/10"
                        : "border-[#d4d4d4] group-hover:border-[#00b4d8] group-hover:bg-[#00b4d8]/5"
                      }
                    `}>
                      <svg className={`w-10 h-10 transition-colors duration-200 ${
                        theme === "dark"
                          ? "text-[#f2f2f2] group-hover:text-[#00b4d8]"
                          : "text-[#1a1a1a] group-hover:text-[#00b4d8]"
                      }`} strokeWidth={1.5} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23.693L5 15.3m14.8 0l-.94 3.013c-.07.22-.263.348-.49.348h-2.25a.75.75 0 01-.75-.75V17.5m-7.5 0v.563a.75.75 0 01-.75.75H5.12c-.227 0-.42-.128-.49-.348L3.7 15.3" />
                      </svg>
                    </div>

                    <h3 className={`text-2xl font-black uppercase tracking-tight mb-2 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}
                      style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                      Straddle Jump
                    </h3>
                    <p className={`text-sm ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                      Analyze jump form and extension
                    </p>

                    <div className="absolute bottom-0 left-0 w-0 h-1 bg-[#00b4d8] transition-all duration-200 group-hover:w-full" />
                  </button>
                </div>
              </div>
            </section>

            {/* Footer */}
            <footer className={`pt-8 border-t-2 ${theme === "dark" ? "border-[#404040]" : "border-[#d4d4d4]"}`}>
              <p className={`text-xs uppercase tracking-wider ${theme === "dark" ? "text-[#666666]" : "text-[#999999]"}`}>
                Powered by AI / Secure & Private
              </p>
              <a
                href="https://www.vecteezy.com/free-vector/handstand"
                target="_blank"
                rel="noopener noreferrer"
                className={`text-xs mt-2 block hover:text-[#00b4d8] transition-colors ${theme === "dark" ? "text-[#404040]" : "text-[#cccccc]"}`}
              >
                Handstand Vectors by Vecteezy
              </a>
            </footer>
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
                fixed top-6 left-6 z-50
                inline-flex items-center gap-2 px-4 py-2
                border-2 transition-all duration-200
                hover:-translate-y-0.5
                ${theme === "dark"
                  ? "bg-[#1a1a1a] border-[#404040] text-[#f2f2f2] hover:border-[#00b4d8]"
                  : "bg-white border-[#d4d4d4] text-[#1a1a1a] hover:border-[#00b4d8]"
                }
              `}
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="text-sm font-bold uppercase tracking-wider">Back</span>
            </button>

            {/* Upload Interface Header */}
            <header className="mb-12">
              <div className="flex items-center gap-4 mb-6">
                <div className={`p-3 border-2 ${theme === "dark" ? "border-[#00b4d8] bg-[#00b4d8]/10" : "border-[#00b4d8] bg-[#00b4d8]/5"}`}>
                  <Video className="w-8 h-8 text-[#00b4d8]" />
                </div>
                <div className={`h-[2px] flex-1 ${theme === "dark" ? "bg-[#404040]" : "bg-[#d4d4d4]"}`} />
              </div>

              <h1 className={`text-3xl md:text-4xl font-black tracking-tight mb-4 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}
                style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                {selectedOption === "handstand" ? "HANDSTAND" : "STRADDLE JUMP"}<br />
                <span className="text-[#00b4d8]">ANALYSIS</span>
              </h1>

              <p className={`text-base mb-6 ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                Upload your videos for AI-powered analysis
              </p>

              <button
                onClick={() => setShowInstructions(true)}
                className={`
                  inline-flex items-center gap-2 px-5 py-2
                  border-2 transition-all duration-200
                  hover:-translate-y-0.5
                  ${theme === "dark"
                    ? "bg-transparent border-[#404040] text-[#f2f2f2] hover:border-[#00b4d8]"
                    : "bg-transparent border-[#d4d4d4] text-[#1a1a1a] hover:border-[#00b4d8]"
                  }
                `}
              >
                <HelpCircle className="w-4 h-4" />
                <span className="text-sm font-bold uppercase tracking-wider">Instructions</span>
              </button>
            </header>

            {/* Upload Area */}
            <section className="mb-8">
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
                  border-2 border-dashed
                  p-12 min-h-[250px]
                  flex flex-col items-center justify-center
                  transition-all duration-200
                  ${isDragging ? 'border-[#00b4d8] bg-[#00b4d8]/5' : ''}
                  ${videos.length > 0 ? 'border-[#00b4d8]' : ''}
                  ${theme === "dark"
                    ? `bg-[#1a1a1a] ${!isDragging && videos.length === 0 ? 'border-[#404040]' : ''} hover:border-[#00b4d8]`
                    : `bg-white ${!isDragging && videos.length === 0 ? 'border-[#d4d4d4]' : ''} hover:border-[#00b4d8]`
                  }
                `}
              >
                <div className={`
                  mb-6 p-4 border-2 transition-colors duration-200
                  ${videos.length > 0
                    ? 'border-[#00b4d8] bg-[#00b4d8]/10'
                    : theme === "dark"
                      ? 'border-[#404040] group-hover:border-[#00b4d8]'
                      : 'border-[#d4d4d4] group-hover:border-[#00b4d8]'
                  }
                `}>
                  <Upload className={`w-10 h-10 transition-colors duration-200 ${
                    videos.length > 0
                      ? 'text-[#00b4d8]'
                      : theme === "dark"
                        ? 'text-[#999999] group-hover:text-[#00b4d8]'
                        : 'text-[#666666] group-hover:text-[#00b4d8]'
                  }`} />
                </div>

                {videos.length > 0 ? (
                  <div className="text-center">
                    <p className={`text-xl font-bold uppercase tracking-tight mb-2 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                      {videos.length} VIDEO{videos.length > 1 ? 'S' : ''} UPLOADED
                    </p>
                    <p className={`text-sm font-mono ${theme === "dark" ? "text-[#666666]" : "text-[#999999]"}`}>
                      {(videos.reduce((sum, v) => sum + v.file.size, 0) / (1024 * 1024)).toFixed(2)} MB total
                    </p>
                    <p className="text-sm text-[#00b4d8] mt-3 font-medium">
                      Click or drop to add more
                    </p>
                  </div>
                ) : (
                  <div className="text-center">
                    <p className={`text-xl font-bold uppercase tracking-tight mb-2 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                      DROP VIDEO HERE
                    </p>
                    <p className={`text-sm ${theme === "dark" ? "text-[#666666]" : "text-[#999999]"}`}>
                      or click to upload / MP4, MOV, AVI
                    </p>
                  </div>
                )}
              </div>
            </section>

            {/* Video Status List */}
            {videos.length > 0 && (
              <section className={`mb-8 border-2 ${theme === "dark" ? "bg-[#1a1a1a] border-[#404040]" : "bg-white border-[#d4d4d4]"}`}>
                <div className={`px-6 py-4 border-b-2 ${theme === "dark" ? "border-[#404040]" : "border-[#d4d4d4]"}`}>
                  <h2 className={`text-sm font-bold uppercase tracking-wider ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                    Processing Status
                  </h2>
                </div>

                <div className="divide-y-2 divide-[#404040] dark:divide-[#404040]">
                  {videos.map((video) => (
                    <div key={video.id} className="px-6 py-4">
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-3 flex-1 min-w-0">
                          <div className={getStatusColor(video.status.status)}>
                            {getStatusIcon(video.status.status)}
                          </div>
                          <span className={`font-medium truncate font-mono text-sm ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                            {video.file.name}
                          </span>
                        </div>
                        <span className={`text-xs uppercase tracking-wider font-bold ${getStatusColor(video.status.status)}`}>
                          {video.status.status}
                        </span>
                      </div>

                      {/* Progress bar */}
                      {(video.status.status === "processing" || video.status.status === "pending") && typeof video.status.progress === 'number' && (
                        <div className={`h-2 ${theme === "dark" ? "bg-[#333333]" : "bg-[#e5e5e5]"}`}>
                          <div
                            className="h-full bg-[#00b4d8] transition-all duration-300"
                            style={{ width: `${video.status.progress}%` }}
                          />
                        </div>
                      )}

                      {/* Error message */}
                      {video.status.status === "failed" && video.status.error_message && (
                        <p className="text-sm mt-2 text-red-500 font-mono">
                          {video.status.error_message}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Results Section */}
            {hasCompletedVideos && (
              <section className={`border-2 p-6 mb-16 ${theme === "dark" ? "bg-[#1a1a1a] border-[#404040]" : "bg-white border-[#d4d4d4]"}`}>
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-3 h-3 bg-[#00b4d8]" />
                  <h2 className={`text-lg font-black uppercase tracking-tight ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}
                    style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                    Analysis Results
                  </h2>
                </div>

                {/* Video Selector */}
                <div className="mb-6">
                  <label className={`block text-xs font-bold uppercase tracking-wider mb-2 ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                    Select Video
                  </label>
                  <div className="relative">
                    <button
                      onClick={() => setShowVideoSelector(!showVideoSelector)}
                      className={`
                        w-full px-4 py-3 border-2
                        flex items-center justify-between
                        transition-all duration-200
                        ${theme === "dark"
                          ? "bg-[#1f1f1f] border-[#404040] text-[#f2f2f2] hover:border-[#00b4d8]"
                          : "bg-[#f5f5f5] border-[#d4d4d4] text-[#1a1a1a] hover:border-[#00b4d8]"
                        }
                      `}
                    >
                      <span className="truncate font-mono text-sm">
                        {selectedVideo ? selectedVideo.file.name : "Select a video"}
                      </span>
                      <ChevronDown className={`w-5 h-5 transition-transform ${showVideoSelector ? "rotate-180" : ""}`} />
                    </button>

                    {showVideoSelector && (
                      <div className={`
                        absolute top-full left-0 right-0 mt-1
                        border-2 z-20
                        ${theme === "dark"
                          ? "bg-[#1f1f1f] border-[#404040]"
                          : "bg-white border-[#d4d4d4]"
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
                              border-b last:border-b-0
                              transition-all duration-200
                              ${selectedVideoId === video.id
                                ? "bg-[#00b4d8]/10 border-[#00b4d8]"
                                : theme === "dark"
                                  ? "border-[#404040] hover:bg-[#2a2a2a]"
                                  : "border-[#e5e5e5] hover:bg-[#f5f5f5]"
                              }
                            `}
                          >
                            <div className={`truncate font-mono text-sm ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                              {video.file.name}
                            </div>
                            <div className={`text-xs font-mono mt-1 ${theme === "dark" ? "text-[#666666]" : "text-[#999999]"}`}>
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
                  <div className="mb-6">
                    <div className={`border-2 overflow-hidden ${theme === "dark" ? "bg-black border-[#404040]" : "bg-[#1a1a1a] border-[#d4d4d4]"}`}>
                      <video
                        key={selectedVideo.status.status === "completed" ? `processed-${selectedVideo.id}` : `preview-${selectedVideo.id}`}
                        src={
                          selectedVideo.status.status === "completed"
                            ? ApiService.getDownloadUrl(selectedVideo.id)
                            : selectedVideo.uploadedUrl
                        }
                        controls
                        className="w-full h-auto max-h-[400px] object-contain"
                      />
                    </div>
                    {selectedVideo.status.status === "completed" && (
                      <p className={`text-xs uppercase tracking-wider mt-2 ${theme === "dark" ? "text-[#666666]" : "text-[#999999]"}`}>
                        Processed Video
                      </p>
                    )}
                  </div>
                )}

                {/* Analysis Results */}
                {resultsData && (
                  <div className={`mb-6 border-2 ${theme === "dark" ? "border-[#404040]" : "border-[#d4d4d4]"}`}>
                    {/* Overall Score */}
                    <div className={`p-6 border-b-2 ${theme === "dark" ? "border-[#404040]" : "border-[#d4d4d4]"}`}>
                      <p className={`text-xs font-bold uppercase tracking-wider mb-3 ${theme === "dark" ? "text-[#666666]" : "text-[#999999]"}`}>
                        Overall Score
                      </p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-5xl font-black text-[#00b4d8]" style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                          {resultsData.overall_score}
                        </span>
                        <span className={`text-2xl ${theme === "dark" ? "text-[#404040]" : "text-[#d4d4d4]"}`}>
                          / {resultsData.max_score}
                        </span>
                      </div>
                      <div className={`text-xl font-bold mt-2 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                        {resultsData.percentage.toFixed(1)}%
                      </div>
                    </div>

                    {/* Poses Grid and Chart */}
                    {chartData.length > 0 && (
                      <div className="grid grid-cols-1 lg:grid-cols-2">
                        {/* Pose Cards */}
                        <div className={`border-r-0 lg:border-r-2 ${theme === "dark" ? "lg:border-[#404040]" : "lg:border-[#d4d4d4]"}`}>
                          {allPoses.map((pose, index) => (
                            <div
                              key={index}
                              className={`p-4 border-b-2 last:border-b-0 ${theme === "dark" ? "border-[#404040]" : "border-[#d4d4d4]"}`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <h4 className={`font-bold uppercase text-sm tracking-wide ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                                  {pose.name}
                                </h4>
                                <span className="font-mono text-sm font-bold" style={{ color: pose.color }}>
                                  {pose.score}/{pose.max_score}
                                </span>
                              </div>

                              {/* Progress Bar */}
                              <div className={`h-2 mb-2 ${theme === "dark" ? "bg-[#333333]" : "bg-[#e5e5e5]"}`}>
                                <div
                                  className="h-full transition-all duration-300"
                                  style={{
                                    width: `${(pose.score / pose.max_score) * 100}%`,
                                    backgroundColor: pose.color
                                  }}
                                />
                              </div>

                              {pose.description && (
                                <p className={`text-xs ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                                  {pose.description}
                                </p>
                              )}

                              {(pose.improvement_needed || (pose.score / pose.max_score) <= 0.5) && (
                                <div className="mt-2 inline-flex items-center gap-1 px-2 py-1 bg-[#00b4d8]/10 border border-[#00b4d8]">
                                  <AlertCircle className="w-3 h-3 text-[#00b4d8]" />
                                  <span className="text-xs font-bold uppercase text-[#00b4d8]">Needs Work</span>
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
                                  stroke={theme === "dark" ? "#141414" : "#fafafa"}
                                >
                                  {chartData.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                  ))}
                                </Pie>
                                <Tooltip
                                  content={({ active, payload }) => {
                                    if (active && payload && payload.length) {
                                      const entry = payload[0].payload;
                                      const isRoomForImprovement = entry.name === "Room for Improvement";

                                      return (
                                        <div className={`p-3 border-2 ${theme === "dark" ? "bg-[#1a1a1a] border-[#404040]" : "bg-white border-[#d4d4d4]"}`}>
                                          <p className={`font-bold uppercase text-sm mb-1 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                                            {entry.name}
                                          </p>
                                          <p className={`text-sm font-mono ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                                            {isRoomForImprovement
                                              ? `Points to gain: ${entry.actualScore}`
                                              : `Score: ${entry.actualScore}/${entry.maxScore}`
                                            }
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
                              <div key={index} className="flex items-center gap-2 text-xs">
                                <div className="w-3 h-3 flex-shrink-0" style={{ backgroundColor: entry.color }} />
                                <span className={`flex-1 uppercase tracking-wide ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
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
                    disabled={!selectedVideoId || selectedVideo?.status.status !== "completed"}
                    className={`
                      group flex items-center justify-center gap-3
                      px-6 py-4 border-2
                      transition-all duration-200
                      disabled:opacity-40 disabled:cursor-not-allowed
                      hover:-translate-y-0.5
                      bg-[#00b4d8] border-[#00b4d8] text-white
                      hover:bg-[#00b4d8]/90
                    `}
                  >
                    <Download className="w-5 h-5" />
                    <span className="font-bold uppercase tracking-wider text-sm">Download Video</span>
                  </button>

                  <button
                    onClick={() => handleSaveReport("pdf")}
                    disabled={!selectedVideoId || !resultsData}
                    className={`
                      group flex items-center justify-center gap-3
                      px-6 py-4 border-2
                      transition-all duration-200
                      disabled:opacity-40 disabled:cursor-not-allowed
                      hover:-translate-y-0.5
                      ${theme === "dark"
                        ? "bg-transparent border-[#f2f2f2] text-[#f2f2f2] hover:bg-[#f2f2f2] hover:text-[#141414]"
                        : "bg-transparent border-[#1a1a1a] text-[#1a1a1a] hover:bg-[#1a1a1a] hover:text-white"
                      }
                    `}
                  >
                    <Download className="w-5 h-5" />
                    <span className="font-bold uppercase tracking-wider text-sm">Download Report (PDF)</span>
                  </button>
                </div>
              </section>
            )}
          </>
        )}
      </div>

      {/* Instructions Dialog */}
      <Dialog open={showInstructions} onOpenChange={setShowInstructions}>
        <DialogContent className={`
          max-w-xl border-2
          ${theme === "dark"
            ? "bg-[#1a1a1a] border-[#404040] text-[#f2f2f2]"
            : "bg-white border-[#d4d4d4] text-[#1a1a1a]"
          }
        `}>
          <DialogHeader>
            <DialogTitle className={`text-2xl font-black uppercase tracking-tight flex items-center gap-3 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}
              style={{ fontFamily: "'Archivo Black', sans-serif" }}>
              <div className="p-2 border-2 border-[#00b4d8] bg-[#00b4d8]/10">
                <HelpCircle className="w-5 h-5 text-[#00b4d8]" />
              </div>
              How to Use
            </DialogTitle>
            <DialogDescription className="sr-only">
              Step-by-step instructions for using the gymnastics analysis application
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-6">
            {[
              { step: "01", title: "Choose Activity", desc: "Select either Handstand or Straddle Jump to begin analysis" },
              { step: "02", title: "Upload Videos", desc: "Drag and drop or click to upload your training videos" },
              { step: "03", title: "Review & Export", desc: "View results, watch processed videos, download reports" }
            ].map((item) => (
              <div key={item.step} className={`p-4 border-2 ${theme === "dark" ? "border-[#404040]" : "border-[#d4d4d4]"}`}>
                <div className="flex gap-4">
                  <span className="text-3xl font-black text-[#00b4d8]" style={{ fontFamily: "'Archivo Black', sans-serif" }}>
                    {item.step}
                  </span>
                  <div>
                    <h3 className={`font-bold uppercase tracking-wide mb-1 ${theme === "dark" ? "text-[#f2f2f2]" : "text-[#1a1a1a]"}`}>
                      {item.title}
                    </h3>
                    <p className={`text-sm ${theme === "dark" ? "text-[#999999]" : "text-[#666666]"}`}>
                      {item.desc}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 p-4 border-2 border-[#00b4d8] bg-[#00b4d8]/5">
            <p className="text-sm">
              <span className="font-bold text-[#00b4d8]">TIP:</span>{" "}
              <span className={theme === "dark" ? "text-[#999999]" : "text-[#666666]"}>
                All processing happens securely. Your videos are never stored permanently.
              </span>
            </p>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
