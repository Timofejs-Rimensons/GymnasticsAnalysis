import React, { useState, useEffect } from 'react';
import { ApiService } from '../services/api';
import { AlertCircle, Download, PlayCircle } from 'lucide-react';
import { Alert, AlertDescription } from './ui/alert';
import { Card } from './ui/card';
import { Badge } from './ui/badge';

interface AnalysisJob {
  id: string;
  video_filename: string;
  status: string;
  results: {
    overall_score?: number;
    max_score?: number;
    percentage?: number;
    categories?: Array<{
      name: string;
      poses: Array<{
        name: string;
        score: number;
        max_score: number;
        description: string;
        improvement_needed: boolean;
      }>;
    }>;
  } | null;
  exercise_id: number | null;
  created_at: string;
  updated_at: string;
  uploaded_at: string | null;
  processed_at: string | null;
}

const PoseScoreCard = ({
  pose,
}: {
  pose: {
    name: string;
    score: number;
    max_score: number;
    description: string;
    improvement_needed: boolean;
  };
}) => {
  const percentage = (pose.score / pose.max_score) * 100;
  const isMissing = pose.score === 0;

  return (
    <div className="bg-gray-700 rounded-lg p-4 mb-3">
      <div className="flex justify-between items-start mb-2">
        <span className="font-medium text-white">{pose.name}</span>
        <span className="text-sm font-bold text-blue-400">
          {pose.score}/{pose.max_score}
        </span>
      </div>
      <p className="text-xs text-gray-400 mb-2">
        {isMissing ? `${pose.name} missing` : pose.description}
      </p>
      <div className="w-full bg-gray-600 rounded-full h-2 mb-2">
        <div
          className={`h-2 rounded-full transition-all ${
            isMissing ? 'bg-red-500' : percentage < 50 ? 'bg-orange-500' : 'bg-green-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {(pose.improvement_needed || isMissing) && (
        <Badge variant="secondary" className="bg-orange-500/20 text-orange-400 border-orange-500/30">
          ⚠️ Needs work
        </Badge>
      )}
    </div>
  );
};

const ScoreChart = ({ results }: { results: any }) => {
  if (!results?.categories?.[0]?.poses) {
    return null;
  }

  const poses = results.categories[0].poses;
  const total = poses.length;
  const completedCount = poses.filter((p: any) => p.score > 0).length;

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-32 h-32 mb-4">
        <svg viewBox="0 0 100 100" className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle cx="50" cy="50" r="45" fill="none" stroke="#4b5563" strokeWidth="12" />

          {/* Score circles */}
          {poses.map((pose: any, index: number) => {
            const circumference = 2 * Math.PI * 45;
            const percentage = (pose.score / pose.max_score) * 100;
            const offset =
              circumference -
              (percentage / 100) *
                circumference *
                (index + 1);
            const colors = [
              '#3b82f6', // blue
              '#a78bfa', // purple
              '#10b981', // green
              '#f59e0b', // amber
            ];

            return (
              <circle
                key={index}
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke={colors[index % colors.length]}
                strokeWidth="12"
                strokeDasharray={
                  (percentage / 100) * circumference
                }
                strokeDashoffset={offset}
                strokeLinecap="round"
              />
            );
          })}
        </svg>

        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-white">
            {results.overall_score || 0}
          </span>
          <span className="text-xs text-gray-400">
            /{results.max_score || 100}
          </span>
        </div>
      </div>

      {/* Legend */}
      <div className="w-full text-xs">
        {poses.map((pose: any, index: number) => {
          const colors = [
            'bg-blue-500',
            'bg-purple-500',
            'bg-green-500',
            'bg-amber-500',
          ];
          const status = pose.improvement_needed ? 'Needs work' : 'Good';
          return (
            <div key={index} className="flex items-center mb-2">
              <div className={`w-2 h-2 rounded-full ${colors[index % colors.length]} mr-2`} />
              <span className="text-gray-300">{pose.name}</span>
              <span className="text-gray-500 ml-auto text-xs">{status}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export const HistoryPage: React.FC<{
  authToken: string;
}> = ({ authToken }) => {
  const [jobs, setJobs] = useState<AnalysisJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [playingJobId, setPlayingJobId] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        const historyJobs = await ApiService.getHistory(authToken);
        setJobs(historyJobs);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load history');
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [authToken]);

  const selectedJob = jobs.find((j) => j.id === selectedJobId);
  const exerciseNames: { [key: number]: string } = {
    1: 'Handstand',
    2: 'Straddle Jump',
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-800">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
          <p className="text-gray-300">Loading your analysis history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-gray-800 min-h-screen">
        <Alert className="bg-red-500/10 border-red-500/50">
          <AlertCircle className="h-4 w-4 text-red-500" />
          <AlertDescription className="text-red-400">{error}</AlertDescription>
        </Alert>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-800">
        <div className="text-center">
          <p className="text-gray-400 mb-4">No analysis history yet</p>
          <p className="text-sm text-gray-500">Upload and process your first video to see results here</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-800 p-6">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Analysis History</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Jobs List */}
          <div className="lg:col-span-1 space-y-4">
            <h2 className="text-lg font-semibold text-white mb-4">
              Your Videos ({jobs.length})
            </h2>
            <div className="space-y-2 max-h-[calc(100vh-200px)] overflow-y-auto">
              {jobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() => setSelectedJobId(job.id)}
                  className={`w-full text-left p-4 rounded-lg transition-all ${
                    selectedJobId === job.id
                      ? 'bg-blue-600 border-2 border-blue-400'
                      : 'bg-gray-700 border-2 border-gray-600 hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <span className="font-medium text-white truncate">
                      {exerciseNames[job.exercise_id || 1]}
                    </span>
                    <Badge
                      variant="secondary"
                      className={`${
                        job.status === 'completed'
                          ? 'bg-green-500/20 text-green-400'
                          : job.status === 'processing'
                            ? 'bg-blue-500/20 text-blue-400'
                            : job.status === 'failed'
                              ? 'bg-red-500/20 text-red-400'
                              : 'bg-yellow-500/20 text-yellow-400'
                      }`}
                    >
                      {job.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-400 mb-2 truncate">{job.video_filename}</p>
                  <p className="text-xs text-gray-500">{job.uploaded_at || job.created_at}</p>
                  {job.results?.overall_score !== undefined && (
                    <div className="mt-2 pt-2 border-t border-gray-600">
                      <p className="text-sm font-bold text-blue-300">
                        {job.results.overall_score}/{job.results.max_score || 100}
                      </p>
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Details View */}
          {selectedJob ? (
            <div className="lg:col-span-2 space-y-6">
              {/* Video Player */}
              {selectedJob.status === 'completed' && (
                <Card className="bg-gray-700 border-gray-600 overflow-hidden">
                  <div
                    className="relative bg-black aspect-video flex items-center justify-center cursor-pointer hover:bg-gray-900"
                    onClick={() =>
                      setPlayingJobId(
                        playingJobId === selectedJob.id ? null : selectedJob.id
                      )
                    }
                  >
                    {playingJobId === selectedJob.id ? (
                      <video
                        key={selectedJob.id}
                        src={`http://localhost:8000/api/video/${selectedJob.id}`}
                        autoPlay
                        controls
                        className="w-full h-full"
                      />
                    ) : (
                      <div className="text-center">
                        <PlayCircle className="w-16 h-16 text-blue-400 mx-auto mb-2" />
                        <p className="text-sm text-gray-400">Click to play processed video</p>
                      </div>
                    )}
                  </div>
                  <div className="p-4 bg-gray-700">
                    <p className="text-xs text-gray-400">
                      Uploaded: {selectedJob.uploaded_at || selectedJob.created_at}
                    </p>
                    {selectedJob.processed_at && (
                      <p className="text-xs text-gray-400">Processed: {selectedJob.processed_at}</p>
                    )}
                  </div>
                </Card>
              )}

              {/* Analysis Results */}
              {selectedJob.status === 'completed' && selectedJob.results ? (
                <div className="space-y-6">
                  {/* Overall Score */}
                  <Card className="bg-gray-700 border-gray-600 p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Analysis Results</h3>
                    <div className="grid grid-cols-2 gap-6">
                      {/* Score Circle */}
                      <div>
                        <ScoreChart results={selectedJob.results} />
                      </div>

                      {/* Scores List */}
                      <div>
                        <h4 className="text-sm font-semibold text-gray-300 mb-4">Pose Scores</h4>
                        {selectedJob.results.categories?.[0]?.poses.map(
                          (pose: any, idx: number) => (
                            <PoseScoreCard key={idx} pose={pose} />
                          )
                        )}
                      </div>
                    </div>
                  </Card>

                  {/* Download Report */}
                  <div className="flex gap-3">
                    <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors">
                      <Download className="w-4 h-4" />
                      Download PDF Report
                    </button>
                    <button className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors">
                      Share Results
                    </button>
                  </div>
                </div>
              ) : selectedJob.status === 'processing' ? (
                <Card className="bg-gray-700 border-gray-600 p-6">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
                    <p className="text-gray-300">Your video is being processed...</p>
                    <p className="text-sm text-gray-500 mt-2">This may take a few moments</p>
                  </div>
                </Card>
              ) : selectedJob.status === 'failed' ? (
                <Alert className="bg-red-500/10 border-red-500/50">
                  <AlertCircle className="h-4 w-4 text-red-500" />
                  <AlertDescription className="text-red-400">
                    Processing failed. Please try uploading the video again.
                  </AlertDescription>
                </Alert>
              ) : (
                <Card className="bg-gray-700 border-gray-600 p-6">
                  <p className="text-gray-400">
                    Video uploaded and waiting to be processed. Click "Process" to start analysis.
                  </p>
                </Card>
              )}
            </div>
          ) : (
            <div className="lg:col-span-2 flex items-center justify-center bg-gray-700 rounded-lg h-96">
              <p className="text-gray-400">Select a video to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
