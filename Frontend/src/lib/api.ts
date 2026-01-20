// Determine API base URL
// From browser: http://localhost:8000 or from env var
// From server (during build/SSR): use docker internal address
const API_BASE_URL = (() => {
  const envUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (envUrl) return envUrl;
  
  // Default to localhost for browser
  return "http://localhost:8000";
})();

export interface UploadResponse {
  pid: string;
  id?: string;
  message?: string;
}

export interface StatusResponse {
  status: "pending" | "processing" | "completed" | "failed";
  progress: number | boolean;
  error_message?: string;
  video_path?: string;
}

export interface ProcessRequest {
  exercise_name: string;
}

export interface Pose {
  name: string;
  score: number;
  max_score: number;
  description: string;
  improvement_needed: boolean;
}

export interface CategoryScore {
  name: string;
  poses: Pose[];
}

export interface AnalysisResult {
  overall_score: number;
  max_score: number;
  percentage: number;
  categories: CategoryScore[];
}

export interface AnalysisHistoryItem {
  id: string;
  fileName: string;
  exerciseType: "handstand" | "straddle_jump";
  uploadedAt: Date;
  status: StatusResponse["status"];
  score?: number;
  maxScore?: number;
  thumbnail?: string;
}

export class ApiService {
  static async getHistory(): Promise<any[]> {
    const response = await fetch(`${API_BASE_URL}/api/jobs`);
    if (!response.ok) throw new Error("Failed to fetch history");
    return response.json();
  }

  static async uploadVideo(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("video", file);
    formData.append("exercise_name", "handstand");

    const url = `${API_BASE_URL}/api/upload`;
    console.log("Uploading to:", url);
    
    try {
      const response = await fetch(url, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail || `Upload error: ${response.statusText}`);
      }

      const data = await response.json();
      console.log("Upload response:", data);
      return {
        pid: data.id || data.pid,
        message: data.message,
      };
    } catch (error) {
      console.error("Upload error:", error);
      throw error;
    }
  }

  static async startProcessing(
    pid: string,
    exercise_name: string
  ): Promise<void> {
    const url = `${API_BASE_URL}/api/process/${pid}`;
    console.log("Starting processing at:", url, "with exercise:", exercise_name);
    
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ exercise_name: exercise_name }),
      });

      if (!response.ok) {
        const error = await response
          .json()
          .catch(() => ({ detail: "Processing request failed" }));
        throw new Error(error.detail || "Failed to trigger processing");
      }
      console.log("Processing started successfully");
    } catch (error) {
      console.error("Start processing error:", error);
      throw error;
    }
  }

  static async getStatus(pid: string): Promise<StatusResponse> {
    const response = await fetch(`${API_BASE_URL}/api/status/${pid}`);

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to check status" }));
      throw new Error(error.detail || "Failed to check status");
    }

    const rawData = await response.json();

    // Adapt backend "0-1" status to frontend Expected format
    if (typeof rawData.status === "number" || typeof rawData.status === "boolean") {
      const val = Number(rawData.status);
      if (val >= 1) {
        return {
          status: "completed",
          progress: 100,
        };
      }
      return {
        status: "processing",
        progress: Math.round(val * 100),
      };
    }

    return rawData;
  }

  static async pollUntilComplete(
    pid: string,
    interval = 2000
  ): Promise<StatusResponse> {
    return new Promise<StatusResponse>((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const res = await this.getStatus(pid);

          if (
            res.status === "completed" ||
            res.progress === true ||
            res.progress === 1 ||
            res.progress === 100
          ) {
            resolve(res);
            return;
          }

          if (res.status === "failed") {
            reject(new Error(res.error_message || "Processing failed"));
            return;
          }

          setTimeout(checkStatus, interval);
        } catch (err) {
          reject(err);
        }
      };

      checkStatus();
    });
  }

  static async getResponseJson(pid: string): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/api/download/json/${pid}`);
    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to fetch analysis result" }));
      throw new Error(error.detail || "Failed to fetch analysis result");
    }
    const data: AnalysisResult = await response.json();
    return data;
  }

  static getDownloadUrl(pid: string): string {
    return `${API_BASE_URL}/api/download/video/${pid}`;
  }

  static getReportPdfUrl(pid: string): string {
    return `${API_BASE_URL}/api/download/pdf/${pid}`;
  }
}

// Mock history data - In production, this would come from a database
export const mockHistoryData: AnalysisHistoryItem[] = [
  {
    id: "1",
    fileName: "handstand_practice_01.mp4",
    exerciseType: "handstand",
    uploadedAt: new Date("2024-11-10T14:30:00"),
    status: "completed",
    score: 8.5,
    maxScore: 10,
  },
  {
    id: "2",
    fileName: "straddle_jump_session.mp4",
    exerciseType: "straddle_jump",
    uploadedAt: new Date("2024-11-08T10:15:00"),
    status: "completed",
    score: 7.2,
    maxScore: 10,
  },
  {
    id: "3",
    fileName: "morning_handstand.mp4",
    exerciseType: "handstand",
    uploadedAt: new Date("2024-11-05T08:45:00"),
    status: "completed",
    score: 9.1,
    maxScore: 10,
  },
];
