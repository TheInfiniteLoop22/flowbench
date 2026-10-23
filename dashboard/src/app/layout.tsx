import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import { Nav } from "@/components/Nav";
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
  title: {
    default: "FlowBench — Bike-Share Rebalancing Analytics",
    template: "%s · FlowBench",
  },
  description: "Demand, imbalance, and rebalancing insights for a 12-month window of NYC (Citi Bike) and Chicago (Divvy) trip data.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex h-full min-h-screen flex-col bg-background text-foreground md:flex-row">
        <Suspense fallback={<div className="h-14 shrink-0 border-b border-border bg-surface md:h-full md:w-56 md:border-b-0 md:border-r" />}>
          <Nav />
        </Suspense>
        <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden pb-16 md:pb-0">{children}</main>
      </body>
    </html>
  );
}
