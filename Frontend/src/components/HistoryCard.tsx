import Link from "next/link";
import { Calendar, ChevronRight, Activity, TrendingUp, AlertTriangle } from "lucide-react";

interface HistoryCardProps {
  id: string;
  date: string;
  exerciseType: string;
  score: number | null;
  thumbnailUrl?: string;
  status: "completed" | "processing" | "failed" | "pending";
}

export function HistoryCard({
  id,
  date,
  exerciseType,
  score,
  thumbnailUrl,
  status,
}: HistoryCardProps) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500/10 text-green-500 border-green-500";
      case "processing":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500";
      case "pending":
        return "bg-blue-500/10 text-blue-500 border-blue-500";
      case "failed":
        return "bg-destructive/10 text-destructive border-destructive";
      default:
        return "bg-muted text-muted-foreground border-muted-foreground";
    }
  };

  return (
    <Link href={`/upload?id=${id}`} className="group block">
      <div className="card-brutalist h-full flex flex-col p-0 overflow-hidden">
        {/* Thumbnail Section */}
        <div className="relative aspect-video bg-surface border-b-2 border-border group-hover:border-accent transition-colors">
          {thumbnailUrl ? (
            <img
              src={thumbnailUrl}
              alt={exerciseType}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-muted-foreground">
              <Activity className="w-12 h-12 opacity-20" />
            </div>
          )}
          
          {/* Status Badge */}
          <div className="absolute top-3 right-3">
             <span className={`px-2 py-1 text-xs font-bold uppercase tracking-wider border ${getStatusColor(status)} bg-background`}>
                {status}
             </span>
          </div>
          
          {/* Score Overlay */}
          {status === "completed" && score !== null && (
            <div className="absolute bottom-3 left-3 bg-background border-2 border-accent px-3 py-1 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-accent" />
              <span className="font-heading font-bold text-accent">{score.toFixed(1)}</span>
            </div>
          )}
        </div>

        {/* Content Section */}
        <div className="p-5 flex-1 flex flex-col">
          <div className="flex items-start justify-between mb-2">
             <h3 className="font-heading text-lg font-bold uppercase leading-tight group-hover:text-accent transition-colors">
                {exerciseType}
             </h3>
             <ChevronRight className="w-5 h-5 text-muted-foreground group-hover:translate-x-1 group-hover:text-accent transition-all" />
          </div>
          
          <div className="mt-auto flex items-center gap-2 text-sm text-muted-foreground">
            <Calendar className="w-4 h-4" />
            <span className="font-mono text-xs">{date}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}