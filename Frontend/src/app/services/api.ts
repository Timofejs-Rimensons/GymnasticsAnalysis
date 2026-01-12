const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export interface UploadResponse {
  pid: string;
  message?: string;
}

export interface StatusResponse {
  status: "pending" | "processing" | "completed" | "failed";
  progress: number | boolean;
  error_message?: string;
}

export interface ProcessRequest {
  exercise_type: string;
}

export interface CategoryScore {
  // write when the json structure is known
}

export interface AnalysisResult {
  overall_score: number;
  max_score: number;
  percentage: number;
  categories: CategoryScore[];
}

export class ApiService {
  static async uploadVideo(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: "POST",
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
    exercise_type: string
  ): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/process/${pid}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ exercise_type: exercise_type }),
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
    const data: StatusResponse = await response.json();
    return data;
  }

  static async pollUntilComplete(
    pid: string,
    interval = 2000
  ): Promise<StatusResponse> {
    return new Promise<StatusResponse>((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const res = await this.getStatus(pid);

          // Completed: resolve with the full status payload
          if (
            res.status === "completed" ||
            res.progress === true ||
            res.progress === 1 || // if server uses 0/1
            res.progress === 100 // if server uses percentage
          ) {
            resolve(res);
            return;
          }

          // Failed: reject with server-provided error
          if (res.status === "failed") {
            reject(new Error(res.error_message || "Processing failed"));
            return;
          }

          // Still pending/processing: poll again
          setTimeout(checkStatus, interval);
        } catch (err) {
          reject(err);
        }
      };

      checkStatus();
    });
  }

  static async getResponseJson(pid: string): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/download/reportjson/${pid}`);
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
    return `${API_BASE_URL}/download/reportpdf/${pid}`;
  }
}
