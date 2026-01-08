// Use relative URLs when served by nginx (production), otherwise use env variable for local dev
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export interface CategoryScore {
  name: string;
  score: number;
  maxScore: number;
  feedback?: string;
}

export interface AnalysisResult {
  overall_score: number;
  max_score: number;
  percentage: number;
  categories: CategoryScore[];
  video_id: string;
  processed_video_path: string;
}

export interface UploadResponse {
  video_id: string;
  filename: string;
  size: number;
  message: string;
}

export interface ExportResponse {
  download_url: string;
  filename: string;
  format: string;
}

export class ApiService {
  static async uploadVideo(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/video/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  }

  static async processVideo(videoId: string, option: number): Promise<AnalysisResult> {
    const response = await fetch(`${API_BASE_URL}/video/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ video_id: videoId, option }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Processing failed');
    }

    return response.json();
  }

  static async getProcessedVideo(videoId: string): Promise<string> {
    return `${API_BASE_URL}/video/processed/${videoId}`;
  }

  static async exportVideo(videoId: string, format: string): Promise<ExportResponse> {
    const response = await fetch(`${API_BASE_URL}/video/export/video`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ video_id: videoId, format }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Export failed');
    }

    return response.json();
  }

  static async exportReport(videoId: string, format: string): Promise<ExportResponse> {
    const response = await fetch(`${API_BASE_URL}/video/export/report`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ video_id: videoId, format }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Report generation failed');
    }

    return response.json();
  }

  static downloadFile(url: string, filename: string) {
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
