import type { Metadata } from "next";
import { SessionProvider } from "@/components/providers/SessionProvider";
import { ThemeProvider } from "@/components/providers/ThemeProvider";
import { ToastProvider } from "@/components/ui/Toaster";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "Gymnastics Analysis | AI-Powered Movement Analysis",
  description:
    "Professional AI-powered gymnastics analysis for training optimization",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <SessionProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem
            disableTransitionOnChange
          >
            <ToastProvider>
              {/* Grid background pattern */}
              <div className="fixed inset-0 pointer-events-none opacity-[0.05] z-0 bg-grid" />
              <div className="relative z-10 min-h-screen">{children}</div>
            </ToastProvider>
          </ThemeProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
