import { LoginForm } from "@/components/LoginForm";
import { Navbar } from "@/components/Navbar";
import { Suspense } from "react";
import { Loader2 } from "lucide-react";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-background relative flex flex-col">
      <Navbar />
      <div className="flex-1 flex items-center justify-center p-6 relative z-10">
         {/* Background decoration */}
         <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
             <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl" />
             <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-accent/5 rounded-full blur-3xl" />
         </div>
         
         <Suspense fallback={<div className="flex items-center justify-center"><Loader2 className="w-8 h-8 animate-spin text-accent" /></div>}>
            <LoginForm />
         </Suspense>
      </div>
    </main>
  );
}