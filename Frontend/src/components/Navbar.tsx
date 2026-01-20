"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Menu,
  X,
  Upload,
  History,
  User,
  LogOut,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/ThemeToggle";

const navLinks = [
  { href: "/upload", label: "Upload", icon: Upload },
  { href: "/history", label: "History", icon: History },
  { href: "/profile", label: "Profile", icon: User },
];

export function Navbar() {
  const { data: session, status } = useSession();
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (href: string) => pathname === href;

  const handleSignOut = () => {
    signOut({ callbackUrl: "/" });
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b-2 border-border bg-background/95 backdrop-blur-sm">
      <div className="container mx-auto px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-3 group">
            <div className="p-2 border-2 border-accent bg-accent/10 transition-colors group-hover:bg-accent/20">
              <Activity className="w-5 h-5 text-accent" />
            </div>
            <span
              className="font-black text-lg uppercase tracking-tight hidden sm:block"
              style={{ fontFamily: "'Archivo Black', sans-serif" }}
            >
              GymAnalysis
            </span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-1">
            {status === "authenticated" &&
              navLinks.map((link) => {
                const Icon = link.icon;
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      "flex items-center gap-2 px-4 py-2 font-bold uppercase text-sm tracking-wide transition-all duration-200 border-b-2",
                      isActive(link.href)
                        ? "border-accent text-accent"
                        : "border-transparent hover:border-border hover:bg-surface"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    {link.label}
                  </Link>
                );
              })}
          </div>

          {/* Auth Buttons / User Menu */}
          <div className="hidden md:flex items-center gap-4">
            <ThemeToggle />
            
            {status === "authenticated" ? (
              <div className="flex items-center gap-4">
                <span className="text-sm text-muted-foreground font-mono">
                  {session.user?.email}
                </span>
                <button
                  onClick={handleSignOut}
                  className="flex items-center gap-2 px-4 py-2 border-2 border-border font-bold uppercase text-sm tracking-wide hover:border-destructive hover:text-destructive transition-all duration-200"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            ) : status === "loading" ? (
              <div className="w-20 h-8 bg-surface animate-pulse" />
            ) : (
              <Link
                href="/login"
                className="px-6 py-2 bg-accent text-accent-foreground font-bold uppercase text-sm tracking-wide border-2 border-accent hover:bg-accent/90 transition-colors"
              >
                Login
              </Link>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center gap-4">
            <ThemeToggle />
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 border-2 border-border hover:border-accent transition-colors"
            >
              {mobileMenuOpen ? (
                <X className="w-5 h-5" />
              ) : (
                <Menu className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden border-t-2 border-border bg-background"
          >
            <div className="container mx-auto px-6 py-4 space-y-2">
              {status === "authenticated" ? (
                <>
                  {navLinks.map((link) => {
                    const Icon = link.icon;
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        onClick={() => setMobileMenuOpen(false)}
                        className={cn(
                          "flex items-center gap-3 px-4 py-3 font-bold uppercase text-sm tracking-wide border-l-4 transition-all duration-200",
                          isActive(link.href)
                            ? "border-accent bg-accent/10 text-accent"
                            : "border-transparent hover:border-border hover:bg-surface"
                        )}
                      >
                        <Icon className="w-5 h-5" />
                        {link.label}
                      </Link>
                    );
                  })}
                  <div className="pt-4 border-t-2 border-border">
                    <p className="text-sm text-muted-foreground font-mono px-4 mb-2">
                      {session.user?.email}
                    </p>
                    <button
                      onClick={() => {
                        setMobileMenuOpen(false);
                        handleSignOut();
                      }}
                      className="w-full flex items-center gap-3 px-4 py-3 font-bold uppercase text-sm tracking-wide text-destructive hover:bg-destructive/10 transition-colors"
                    >
                      <LogOut className="w-5 h-5" />
                      Logout
                    </button>
                  </div>
                </>
              ) : (
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="block px-4 py-3 bg-accent text-accent-foreground font-bold uppercase text-sm tracking-wide text-center border-2 border-accent"
                >
                  Login
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  );
}