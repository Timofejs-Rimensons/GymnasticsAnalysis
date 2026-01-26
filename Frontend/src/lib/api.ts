const API_BASE_URL = "/api/backend";

export interface UploadResponse {
  pid: string;
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

export interface Tip {
  met: boolean;
  criterion: string;
  tip: string;
}

interface Error {
  criterion: string;
  improvement: string;
  frequency: number;
}

export interface Pose {
  name: string;
  score: number;
  max_score: number;
  description: string;
  improvement_needed: boolean;
  tips?: Tip[];
  errors?: Error[];
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
  static async getHistory(userId?: string): Promise<any[]> {
    const headers: HeadersInit = {};
    if (userId) {
      headers['X-User-Id'] = userId;
    }

    const response = await fetch(`${API_BASE_URL}/history`, { headers });
    if (!response.ok) throw new Error("Failed to fetch history");
    return response.json();
  }

  static async uploadVideo(file: File, userId?: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("video", file);

    const headers: HeadersInit = {};
    if (userId) {
      headers['X-User-Id'] = userId;
    }

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || `Upload error: ${response.statusText}`);
    }

    return response.json();
  }

  static async startProcessing(
    pid: string,
    exercise_name: string
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/process/${pid}`, {
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
  }

  static async getStatus(pid: string): Promise<StatusResponse> {
    const response = await fetch(`${API_BASE_URL}/status/${pid}`);

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
    const response = await fetch(`${API_BASE_URL}/download/json/${pid}`);
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
    return `${API_BASE_URL}/download/video/${pid}`;
  }

  static getReportPdfUrl(pid: string): string {
    return `${API_BASE_URL}/download/pdf/${pid}`;
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
