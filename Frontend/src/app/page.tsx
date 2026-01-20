import Link from "next/link";
import { Navbar } from "@/components/Navbar";
import { ArrowRight, CheckCircle2, PlayCircle, BarChart2 } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background relative selection:bg-accent selection:text-accent-foreground">
      <Navbar />

      <main className="pt-16">
        {/* Hero Section */}
        <section className="relative py-20 lg:py-32 overflow-hidden">
          <div className="container mx-auto px-6 relative z-10">
            <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-20">
              
              {/* Text Content */}
              <div className="lg:w-1/2 space-y-8">
                <div className="inline-block px-4 py-2 border-2 border-accent bg-accent/10">
                   <span className="font-mono text-accent font-bold uppercase tracking-wider text-sm">
                     AI-Powered Analysis
                   </span>
                </div>
                
                <h1 className="text-5xl lg:text-7xl font-black leading-[0.9] tracking-tighter uppercase font-heading">
                  Master Your <br/>
                  <span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-foreground">Technique</span>
                </h1>
                
                <p className="text-xl text-muted-foreground font-light max-w-xl leading-relaxed">
                  Advanced computer vision algorithms analyze your gymnastics form in real-time, providing professional-grade feedback and scoring.
                </p>
                
                <div className="flex flex-wrap items-center gap-4">
                  <Link href="/upload" className="btn-primary flex items-center gap-3 group">
                    Start Analysis
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                  </Link>
                  <Link href="#features" className="btn-secondary inline-flex items-center justify-center">
                    Learn More
                  </Link>
                </div>
              </div>

              {/* Hero Image/Visual */}
              <div className="lg:w-1/2 relative">
                <div className="relative z-10 border-4 border-border bg-surface p-2 shadow-[8px_8px_0px_0px_rgba(64,64,64,1)]">
                   {/* Placeholder for Gymnast Image */}
                   <div className="aspect-[4/3] bg-[#1a1a1a] relative overflow-hidden flex items-center justify-center">
                      <div className="absolute inset-0 bg-[url('https://images.unsplash.com/photo-1518619740027-6c0b91e92c2c?q=80&w=2000&auto=format&fit=crop')] bg-cover bg-center opacity-80 mix-blend-overlay"></div>
                      <div className="relative z-10 text-center p-8">
                        <PlayCircle className="w-20 h-20 text-accent mx-auto mb-4 opacity-80" />
                        <p className="font-mono text-sm text-white/60 uppercase tracking-widest">AI Vision Processing</p>
                      </div>
                      
                      {/* Overlay UI Elements */}
                      <div className="absolute top-4 right-4 bg-background border border-accent p-2">
                        <div className="flex items-center gap-2">
                           <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                           <span className="font-mono text-xs font-bold text-accent">TRACKING ACTIVE</span>
                        </div>
                      </div>
                      
                       <div className="absolute bottom-4 left-4 right-4 bg-background/90 border border-border p-4 backdrop-blur-sm">
                        <div className="flex justify-between items-end">
                           <div>
                              <p className="font-mono text-xs text-muted-foreground uppercase mb-1">Score</p>
                              <p className="font-heading text-3xl text-accent">9.85</p>
                           </div>
                            <div className="h-8 w-24 bg-surface flex items-end gap-1 pb-1">
                               <div className="w-1/3 bg-accent/40 h-[60%]"></div>
                               <div className="w-1/3 bg-accent/70 h-[80%]"></div>
                               <div className="w-1/3 bg-accent h-[40%]"></div>
                            </div>
                        </div>
                      </div>
                   </div>
                </div>
                
                {/* Decorative Elements */}
                <div className="absolute -top-12 -right-12 w-64 h-64 bg-accent/20 rounded-full blur-3xl -z-10"></div>
                <div className="absolute -bottom-12 -left-12 w-48 h-48 bg-purple-500/20 rounded-full blur-3xl -z-10"></div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-20 border-t-2 border-border bg-surface/30">
          <div className="container mx-auto px-6">
             <div className="grid md:grid-cols-3 gap-8">
                {[
                  {
                    icon: PlayCircle,
                    title: "Video Analysis",
                    desc: "Upload any gymnastics video for instant frame-by-frame breakdown."
                  },
                  {
                    icon: BarChart2,
                    title: "Precise Metrics",
                    desc: "Get joint angles, velocity tracking, and form deviation scores."
                  },
                  {
                    icon: CheckCircle2,
                    title: "Instant Feedback",
                    desc: "Receive actionable corrections to improve your performance immediately."
                  }
                ].map((feature, idx) => (
                  <div key={idx} className="card-brutalist group">
                     <div className="mb-6 p-4 bg-background border-2 border-border w-fit group-hover:border-accent transition-colors">
                        <feature.icon className="w-8 h-8 text-accent" />
                     </div>
                     <h3 className="text-2xl font-bold uppercase mb-4 font-heading">{feature.title}</h3>
                     <p className="text-muted-foreground leading-relaxed">{feature.desc}</p>
                  </div>
                ))}
             </div>
          </div>
        </section>
      </main>
      
      <footer className="py-12 border-t-2 border-border bg-background">
         <div className="container mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-6">
            <p className="font-mono text-sm text-muted-foreground">© 2026 Gymnastics Analysis AI. All rights reserved.</p>
            <div className="flex gap-6">
               <Link href="#" className="font-bold uppercase text-sm hover:text-accent transition-colors">Privacy</Link>
               <Link href="#" className="font-bold uppercase text-sm hover:text-accent transition-colors">Terms</Link>
               <Link href="#" className="font-bold uppercase text-sm hover:text-accent transition-colors">Contact</Link>
            </div>
         </div>
      </footer>
    </div>
  );
}