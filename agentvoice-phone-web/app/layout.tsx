import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "agentVoice — iPhone Safari Gateway",
  description: "Your AI. Your Voice. Your Infrastructure.",
  manifest: "/manifest.json",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-50 antialiased">{children}</body>
    </html>
  );
}
