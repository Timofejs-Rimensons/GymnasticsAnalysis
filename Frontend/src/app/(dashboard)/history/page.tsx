"use client";

import { Navbar } from "@/components/Navbar";
import { HistoryCard } from "@/components/HistoryCard";
import { Filter, Search, SortAsc, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";
import { ApiService } from "@/lib/api";
import { useSession } from "next-auth/react";

export default function HistoryPage() {
  const { data: session } = useSession();
  const [filter, setFilter] = useState("all");
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadHistory() {
      try {
        const userId = session?.user?.id;
        console.log("🔍 History - Session:", session);
        console.log("🔍 History - User ID:", userId);

        const response = await ApiService.getHistory(userId);
        const mapped = response.data.map((item: any) => ({
            id: item.id,
            // Map created_at to date
            date: item.created_at ? new Date(item.created_at).toLocaleDateString() : "Unknown",
            // Map exerciseType (already in camelCase from Next.js API)
            exerciseType: item.exerciseType || "Unknown",
            // Use .score (as formatted by API)
            score: item.score || 0,
            status: item.status,
            thumbnailUrl: null
        }));
        setHistory(mapped);
      } catch (err) {
        console.error("Failed to load history", err);
      } finally {
        setLoading(false);
      }
    }
    loadHistory();
  }, [session]);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="container mx-auto px-6 pt-24 pb-12">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-12">
           <div>
             <h1 className="text-4xl font-black uppercase tracking-tight mb-2 font-heading">
               Analysis <span className="text-accent">History</span>
             </h1>
             <p className="text-muted-foreground">
               Review your past performances and track your progress over time.
             </p>
           </div>

           {/* Filters Toolbar */}
           <div className="flex flex-wrap gap-4">
              <div className="relative">
                 <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                 <input 
                   type="text" 
                   placeholder="Search exercises..." 
                   className="pl-9 pr-4 py-2 border-2 border-border bg-background font-mono text-sm focus:border-accent focus:outline-none w-full md:w-64"
                 />
              </div>
              
              <button className="flex items-center gap-2 px-4 py-2 border-2 border-border bg-surface hover:border-accent transition-colors font-bold uppercase text-sm">
                 <Filter className="w-4 h-4" />
                 Filter
              </button>
              
              <button className="flex items-center gap-2 px-4 py-2 border-2 border-border bg-surface hover:border-accent transition-colors font-bold uppercase text-sm">
                 <SortAsc className="w-4 h-4" />
                 Sort
              </button>
           </div>
        </div>

        {/* Grid */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-accent" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
             {history.length === 0 ? (
               <p className="text-muted-foreground col-span-full text-center">No analysis history found.</p>
             ) : (
               history.map((item) => (
                 <HistoryCard key={item.id} {...item} />
               ))
             )}
          </div>
        )}
      </main>
    </div>
  );
}
