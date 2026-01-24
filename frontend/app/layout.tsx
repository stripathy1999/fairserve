<<<<<<< HEAD
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FairServe",
  description: "FairServe Zone1 + Zone2 operational dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <div className="min-h-screen bg-zinc-50 text-zinc-900">
          <header className="border-b border-zinc-200 bg-white">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
              <div>
                <p className="text-sm uppercase tracking-wide text-zinc-500">
                  FairServe
                </p>
                <h1 className="text-xl font-semibold">Zone2 Control Room</h1>
              </div>
              <nav className="flex gap-4 text-sm font-medium text-zinc-600">
                <a href="/" className="hover:text-zinc-900">
                  Overview
                </a>
                <a href="/intake" className="hover:text-zinc-900">
                  Intake
                </a>
                <a href="/fairness" className="hover:text-zinc-900">
                  Fairness
                </a>
                <a href="/policy" className="hover:text-zinc-900">
                  Policy
                </a>
                <a href="/review" className="hover:text-zinc-900">
                  Review
                </a>
                <a href="/agents" className="hover:text-zinc-900">
                  Agents
                </a>
              </nav>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
=======
import type { ReactNode } from "react";

import "./globals.css";

export const metadata = {
  title: "FairServe",
  description: "Fairness and policy review demo",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
>>>>>>> 521b4f51 (Move project into frontend directory.)
    </html>
  );
}
