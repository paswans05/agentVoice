"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { MicrophoneTest } from "@/components/MicrophoneTest";
import { VoiceSession } from "@/components/VoiceSession";

export default function VoiceTestPage() {
  return (
    <div className="mx-auto max-w-md space-y-5 p-4 pt-6">
      <div className="flex items-center gap-3">
        <Link
          href="/gateway"
          className="inline-flex items-center gap-1 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Gateway
        </Link>
        <h1 className="text-lg font-bold">Audio & WebRTC Voice</h1>
      </div>

      <MicrophoneTest />
      <VoiceSession />
    </div>
  );
}
