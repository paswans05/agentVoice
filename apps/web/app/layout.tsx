import type { Metadata } from "next";
import { DashboardShell } from "@/components/dashboard-shell";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "agentVoice — Your AI. Your Voice. Your Infrastructure.",
  description: "Open-source, self-hosted, local-first AI voice agent platform.",
  icons: {
    icon: [
      { url: "/agentvoice-favicon.ico" },
      { url: "/agentvoice-favicon-16.png", sizes: "16x16", type: "image/png" },
      { url: "/agentvoice-favicon-32.png", sizes: "32x32", type: "image/png" },
      { url: "/agentvoice-icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    shortcut: "/agentvoice-favicon.ico",
    apple: "/agentvoice-icon-192.png",
  },
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
