"use client";

import { Navbar } from "@/components/Navbar";
import { useSession } from "next-auth/react";
import { User, Mail, Calendar, Settings, LogOut } from "lucide-react";
import { ApiService } from "@/lib/api";
import { useState, useEffect } from "react";

export default function ProfilePage() {
  const { data: session } = useSession();
  const [stats, setStats] = useState({ total: 0, avgScore: 0 });

  useEffect(() => {
    async function loadStats() {
      try {
        // Get first page to calculate stats (we'll use pagination.total for total count)
        // For accurate stats, we might want to fetch all, but for performance we'll use the first page
        const historyResponse = await ApiService.getHistory(undefined, 1, 100); // Get up to 100 records for stats
        const history = historyResponse.data;
        const total = historyResponse.pagination.total; // Use total from pagination
        const completed = history.filter((h: any) => h.status === "completed" && h.score !== null);
        const avgScore = completed.length > 0 
           ? completed.reduce((acc: number, curr: any) => acc + (curr.score || 0), 0) / completed.length 
           : 0;
           
        setStats({ total, avgScore });
      } catch (e) {
        console.error("Failed to load stats", e);
      }
    }
    loadStats();
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      
      <main className="container mx-auto px-6 pt-24 pb-12 max-w-4xl">
        <h1 className="text-4xl font-black uppercase tracking-tight mb-8 font-heading">
           User <span className="text-accent">Profile</span>
        </h1>

        <div className="grid md:grid-cols-3 gap-8">
           {/* Sidebar / User Card */}
           <div className="md:col-span-1">
              <div className="card-brutalist text-center">
                 <div className="w-32 h-32 mx-auto bg-surface border-2 border-accent rounded-full mb-6 flex items-center justify-center overflow-hidden">
                    {session?.user?.image ? (
                       <img src={session.user.image} alt="Profile" className="w-full h-full object-cover" />
                    ) : (
                       <User className="w-12 h-12 text-accent" />
                    )}
                 </div>
                 
                 <h2 className="text-xl font-bold uppercase mb-1">{session?.user?.name || "User"}</h2>
                 <p className="text-sm text-muted-foreground font-mono mb-6 truncate">{session?.user?.email}</p>
                 
                 <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm p-3 border-2 border-border bg-background">
                       <span className="text-muted-foreground uppercase text-xs font-bold">Joined</span>
                       <span className="font-mono">Jan 2024</span>
                    </div>
                    <div className="flex items-center justify-between text-sm p-3 border-2 border-border bg-background">
                       <span className="text-muted-foreground uppercase text-xs font-bold">Analyses</span>
                       <span className="font-mono">{stats.total}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm p-3 border-2 border-border bg-background">
                       <span className="text-muted-foreground uppercase text-xs font-bold">Avg Score</span>
                       <span className="font-mono text-accent">{stats.avgScore.toFixed(1)}</span>
                    </div>
                 </div>
              </div>
           </div>

           {/* Settings / Content */}
           <div className="md:col-span-2 space-y-8">
              {/* Account Settings */}
              <section>
                 <h3 className="text-lg font-bold uppercase mb-4 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-accent" />
                    Account Settings
                 </h3>
                 
                 <div className="card-brutalist space-y-4">
                    <div className="grid gap-2">
                       <label className="text-sm font-bold uppercase text-muted-foreground">Display Name</label>
                       <input 
                         type="text" 
                         defaultValue={session?.user?.name || ""}
                         className="input-brutalist"
                       />
                    </div>
                    <div className="grid gap-2">
                       <label className="text-sm font-bold uppercase text-muted-foreground">Email Address</label>
                       <input 
                         type="email" 
                         defaultValue={session?.user?.email || ""}
                         disabled
                         className="input-brutalist opacity-60 cursor-not-allowed"
                       />
                    </div>
                    
                    <div className="pt-4 flex justify-end">
                       <button className="btn-primary py-2 px-6 text-sm">Save Changes</button>
                    </div>
                 </div>
              </section>
           </div>
        </div>
      </main>
    </div>
  );
}
