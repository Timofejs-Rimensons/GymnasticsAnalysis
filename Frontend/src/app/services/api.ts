const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// --- NEW API INTERFACES ---

export interface AnalysisJob {
  id: string; // This is the UUID, now called jobId
  video_filename: string;
  status: "uploaded" | "processing" | "completed" | "failed";
  results: AnalysisResult | null;
  created_at: string;
  updated_at: string;
}

export interface StatusResponse {
  status: "uploaded" | "processing" | "completed" | "failed";
  progress: number;
}

export interface ProcessRequest {
  // The new process endpoint doesn't require a body,
  // but we'll keep this for potential future use.
  exercise_name?: string; 
}

// --- EXISTING DATA STRUCTURES (ASSUMED UNCHANGED) ---

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

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

export class ApiService {
  /**
   * Register a new user.
   */
  static async register(username: string, email: string, password: string): Promise<UserResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(error.detail || `Registration error: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Login user and get access token.
   */
  static async login(username: string, password: string): Promise<TokenResponse> {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Login failed" }));
      throw new Error(error.detail || `Login error: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Uploads a video and returns the created analysis job.
   */
  static async uploadVideo(file: File, exerciseName: string, token: string): Promise<AnalysisJob> {
    const formData = new FormData();
    formData.append("video", file);
    formData.append("exercise_name", exerciseName);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
      },
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

  /**
   * Triggers the processing for a given job ID.
   */
  static async startProcessing(jobId: string): Promise<AnalysisJob> {
    const response = await fetch(`${API_BASE_URL}/process/${jobId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // The new endpoint doesn't require a body, but we send an empty one.
      body: JSON.stringify({}), 
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Processing request failed" }));
      throw new Error(error.detail || "Failed to trigger processing");
    }
    return response.json();
  }

  /**
   * Retrieves the current status of an analysis job.
   */
  static async getStatus(jobId: string): Promise<StatusResponse> {
    const response = await fetch(`${API_BASE_URL}/status/${jobId}`);

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to check status" }));
      throw new Error(error.detail || "Failed to check status");
    }
    
    return response.json();
  }

  /**
   * Polls the status endpoint until the job is completed or fails.
   */
  static async pollUntilComplete(
    jobId: string,
    interval = 2000
  ): Promise<StatusResponse> {
    return new Promise<StatusResponse>((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const res = await this.getStatus(jobId);

          if (res.status === "completed") {
            resolve(res);
            return;
          }

          if (res.status === "failed") {
            reject(new Error("Processing failed"));
            return;
          }

          // Still "uploaded" or "processing": poll again
          setTimeout(checkStatus, interval);
        } catch (err) {
          reject(err);
        }
      };

      checkStatus();
    });
  }

  /**
   * Fetches the final analysis results for a completed job.
   */
  static async getResults(jobId: string): Promise<AnalysisJob> {
    const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to fetch analysis result" }));
      throw new Error(error.detail || "Failed to fetch analysis result");
    }
    return response.json();
  }

  /**
   * Fetches user's analysis history (all jobs).
   */
  static async getHistory(token: string): Promise<AnalysisJob[]> {
    const response = await fetch(`${API_BASE_URL}/history`, {
      headers: {
        "Authorization": `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Failed to fetch history" }));
      throw new Error(error.detail || "Failed to fetch history");
    }

    return response.json();
  }

  /**
   * Retrieves the processed video URL with skeleton visualization.
   */
  static getProcessedVideoUrl(jobId: string): string {
    return `${API_BASE_URL}/video/${jobId}`;
  }

  // The following methods are now deprecated as the new API flow
  // does not provide direct download links for video/PDF.
  // This functionality should be re-implemented based on where the
  // backend stores the processed files (e.g., S3 URLs in the 'results' JSON).

  /**
   * @deprecated Use getProcessedVideoUrl instead
   */
  static getDownloadUrl(jobId: string): string {
    return this.getProcessedVideoUrl(jobId);
  }

  /**
   * @deprecated Re-implement based on file storage strategy (e.g., get URL from results).
   */
  static getReportPdfUrl(jobId: string): string {
    console.warn("getReportPdfUrl is deprecated. PDF URL should be retrieved from job results.");
    return `#`;
  }
}