"use client";

import { useState, useEffect, Suspense } from "react";
import { VideoUploader } from '@/components/VideoUploader';
import { ProcessingStatus } from '@/components/ProcessingStatus';
import { ResultsDisplay } from '@/components/ResultsDisplay';
import { Video, HelpCircle, X, CheckCircle2, Loader2, MoveUp, Activity } from 'lucide-react';
import { Navbar } from "@/components/Navbar";
import { ApiService, StatusResponse, AnalysisResult } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";
import { useSearchParams } from "next/navigation";
import { useSession, getSession } from "next-auth/react";

interface VideoUpload {
  id: string;
  file: File;
  uploadedUrl: string;
  status: StatusResponse;
  analysisResults?: AnalysisResult;
}

function InstructionsModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-lg bg-background border-2 border-border shadow-[8px_8px_0px_0px_rgba(var(--accent),0.2)] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b-2 border-border bg-surface">
          <h2 className="text-xl font-black uppercase tracking-tight font-heading">
            How it <span className="text-accent">Works</span>
          </h2>
          <button 
            onClick={onClose}
            className="p-1 hover:bg-background border-2 border-transparent hover:border-border transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="p-6 space-y-6">
          <div className="space-y-4">
            {[
              "Record a video of your gymnastics element (e.g., Handstand).",
              "Ensure your full body is visible in the frame at all times.",
              "Upload the video using the dropzone below.",
              "Wait for the AI to process and analyze your form.",
              "Review your score, detailed metrics, and feedback."
            ].map((step, idx) => (
              <div key={idx} className="flex gap-4 items-start">
                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-accent/10 border border-accent flex items-center justify-center mt-0.5">
                  <span className="text-xs font-bold text-accent font-mono">{idx + 1}</span>
                </div>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {step}
                </p>
              </div>
            ))}
          </div>
          
          <div className="p-4 bg-accent/5 border border-accent/20 flex gap-3 items-start">
            <CheckCircle2 className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="text-xs font-bold uppercase text-accent tracking-wide">Pro Tip</p>
              <p className="text-xs text-muted-foreground">
                For best results, use a tripod or stable surface and ensure good lighting conditions.
              </p>
            </div>
          </div>
        </div>
        
        <div className="p-6 border-t-2 border-border bg-surface flex justify-end">
          <button onClick={onClose} className="btn-primary py-2 px-6 text-sm">
            Got it
          </button>
        </div>
      </div>
      
      {/* Click backdrop to close */}
      <div className="absolute inset-0 -z-10" onClick={onClose} />
    </div>
  );
}

function UploadPageContent() {
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const { data: session } = useSession();
  const [videos, setVideos] = useState<VideoUpload[]>([]);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [exerciseType, setExerciseType] = useState<string>("handstand");

  const exercises = [
    { id: "handstand", name: "Handstand", icon: MoveUp },
    { id: "straddle_jump", name: "Straddle Jump", icon: Activity },
  ];

  useEffect(() => {
    const id = searchParams.get("id");
    if (id && !videos.some(v => v.id === id)) {
      loadVideo(id);
    }
  }, [searchParams]);

  const loadVideo = async (id: string) => {
    try {
      const status = await ApiService.getStatus(id);
      let results: AnalysisResult | undefined;

      if (status.status === "completed") {
        try {
          results = await ApiService.getResponseJson(id);
        } catch (e) {
          console.error("Failed to load results", e);
        }
      }

      // Create a dummy file object since we can't reconstruct the original
      const dummyFile = new File([], status.video_path || "video.mp4", { type: "video/mp4" });

      const video: VideoUpload = {
        id,
        file: dummyFile,
        uploadedUrl: "",
        status,
        analysisResults: results
      };

      setVideos(prev => [...prev, video]);
      if (status.status === "completed") {
        setSelectedVideoId(id);
      }
    } catch (e) {
      console.error("Failed to load video", e);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load video details",
      });
    }
  };

  const handleFileSelect = async (fileList: FileList) => {
    const newFiles = Array.from(fileList);
    
    // Create initial state for new files
    const newVideoUploads: VideoUpload[] = newFiles.map(file => ({
      id: Math.random().toString(36).substring(7), // Temporary ID until upload
      file,
      uploadedUrl: "",
      status: { status: "pending", progress: 0 }
    }));

    setVideos(prev => [...prev, ...newVideoUploads]);

    // Process each file
    for (const videoUpload of newVideoUploads) {
      processVideo(videoUpload);
    }
  };

  const processVideo = async (videoUpload: VideoUpload) => {
    let analysisId: string | null = null;
    try {
      // Get fresh session to ensure we have the user ID if logged in
      const session = await getSession();
      const userId = session?.user?.id;

      // Debug logging
      console.log("🔍 Session data:", session);
      console.log("🔍 User ID:", userId);

      // 1. Upload - This creates the analysis record in the backend with ID = pid
      updateVideoStatus(videoUpload.id, { status: "processing", progress: 10 });
      const uploadResp = await ApiService.uploadVideo(videoUpload.file, userId);
      
      const pid = uploadResp.pid;
      setVideos(prev => prev.map(v => v.id === videoUpload.id ? { ...v, id: pid } : v));

      // If user is logged in, the backend created a record with id=pid
      if (userId) {
        analysisId = pid;
        console.log("✅ Using backend analysis record:", analysisId);
      }
      
      // Update analysis status to processing
      if (analysisId) {
        try {
          await ApiService.updateAnalysis(analysisId, { status: "processing", progress: 0.1 });
        } catch (error) {
          console.error("⚠️ Failed to update analysis status:", error);
        }
      }
      
      // 2. Start Processing using selected exerciseType
      updateVideoStatus(pid, { status: "processing", progress: 30 });
      await ApiService.startProcessing(pid, exerciseType);
      
      if (analysisId) {
        try {
          await ApiService.updateAnalysis(analysisId, { status: "processing", progress: 0.3 });
        } catch (error) {
          console.error("⚠️ Failed to update analysis status:", error);
        }
      }
      
      // 3. Poll for Status
      updateVideoStatus(pid, { status: "processing", progress: 50 });
      await ApiService.pollUntilComplete(pid);
      
      if (analysisId) {
        try {
          await ApiService.updateAnalysis(analysisId, { status: "processing", progress: 0.5 });
        } catch (error) {
          console.error("⚠️ Failed to update analysis status:", error);
        }
      }
      
      // 4. Get Results
      updateVideoStatus(pid, { status: "processing", progress: 90 });
      const results = await ApiService.getResponseJson(pid);
      
      // 5. Save results to database
      if (analysisId) {
        try {
          await ApiService.updateAnalysis(analysisId, {
            status: "completed",
            progress: 1.0,
            overallScore: results.overall_score,
            maxScore: results.max_score,
            percentage: results.percentage,
            resultsJson: results,
            completedAt: new Date().toISOString()
          });
          console.log("✅ Saved analysis results to database");
        } catch (error) {
          console.error("⚠️ Failed to save analysis results:", error);
        }
      }
      
      updateVideoStatus(pid, { status: "completed", progress: 100 });
      setVideos(prev => prev.map(v => v.id === pid ? { ...v, analysisResults: results } : v));
      
      if (!selectedVideoId) {
        setSelectedVideoId(pid);
      }
      
      toast({
        title: "Analysis Complete",
        description: `Successfully analyzed ${videoUpload.file.name}`,
      });

    } catch (error: any) {
      console.error("Processing failed:", error);
      const targetId = videos.find(v => v.file === videoUpload.file)?.id || videoUpload.id;
      
      // Update analysis status to failed
      if (analysisId) {
        try {
          await ApiService.updateAnalysis(analysisId, {
            status: "failed",
            errorMessage: error.message || "Processing failed"
          });
        } catch (dbError) {
          console.error("⚠️ Failed to update analysis status to failed:", dbError);
        }
      }
      
      updateVideoStatus(targetId, { 
        status: "failed", 
        progress: 0, 
        error_message: error.message || "Processing failed" 
      });
      
      toast({
        variant: "destructive",
        title: "Processing Failed",
        description: error.message || "Failed to process video",
      });
    }
  };

  const updateVideoStatus = (id: string, status: StatusResponse) => {
    setVideos(prev => prev.map(v => v.id === id ? { ...v, status } : v));
  };

  const totalSize = videos.reduce((acc, v) => acc + v.file.size, 0);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="container mx-auto px-6 pt-24 pb-12 max-w-5xl">
        {/* Header */}
        <header className="mb-12">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 border-2 border-accent bg-accent/10">
              <Video className="w-8 h-8 text-accent" />
            </div>
            <div className="h-[2px] flex-1 bg-border" />
          </div>

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
            <div>
              <h1 className="text-3xl md:text-5xl font-black tracking-tight mb-4 font-heading leading-none uppercase">
                {exerciseType.replace('_', ' ')}<br />
                <span className="text-accent">ANALYSIS</span>
              </h1>

              <p className="text-base text-muted-foreground font-light max-w-lg">
                Choose your exercise category, then upload your video for AI-powered form correction.
              </p>
            </div>
            
            <button 
              onClick={() => setShowInstructions(true)}
              className="btn-secondary flex items-center gap-2 self-start md:self-end"
            >
              <HelpCircle className="w-4 h-4" />
              <span className="text-sm">Instructions</span>
            </button>
          </div>
        </header>

        {/* Exercise Selection */}
        <div className="mb-12">
          <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground mb-4">
            1. Select Exercise Category
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {exercises.map((ex) => {
              const Icon = ex.icon;
              return (
                <button
                  key={ex.id}
                  onClick={() => setExerciseType(ex.id)}
                  className={`
                    flex items-center gap-4 p-6 border-2 transition-all duration-200
                    ${exerciseType === ex.id 
                      ? "border-accent bg-accent/5 shadow-[4px_4px_0px_0px_rgba(var(--accent),1)]" 
                      : "border-border hover:border-accent hover:bg-surface"}
                  `}
                >
                  <div className={`p-2 border-2 ${exerciseType === ex.id ? 'border-accent bg-accent/10' : 'border-border'}`}>
                    <Icon className={`w-6 h-6 ${exerciseType === ex.id ? 'text-accent' : 'text-muted-foreground'}`} />
                  </div>
                  <span className={`text-xl font-black uppercase tracking-tight ${exerciseType === ex.id ? 'text-accent' : ''}`}>
                    {ex.name}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Main Content */}
        <div className="space-y-8">
          <div>
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground mb-4">
              2. Upload Video
            </h2>
            <VideoUploader 
              onFileSelect={handleFileSelect}
              uploadedCount={videos.length}
              totalSize={totalSize}
            />
          </div>
          
          <ProcessingStatus videos={videos} />
          
          <ResultsDisplay 
            videos={videos}
            selectedVideoId={selectedVideoId}
            onSelectVideo={setSelectedVideoId}
          />
        </div>
      </main>

      {showInstructions && <InstructionsModal onClose={() => setShowInstructions(false)} />}
    </div>
  )
}

export default function UploadPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    }>
      <UploadPageContent />
    </Suspense>
  );
}