import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard-shell";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "agentVoice — Your AI. Your Voice. Your Infrastructure.",
  description: "Open-source, self-hosted, local-first AI voice agent platform.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased">
        <Providers>
          <DashboardShell>{children}</DashboardShell>
        </Providers>
      </body>
    </html>
  );
}
