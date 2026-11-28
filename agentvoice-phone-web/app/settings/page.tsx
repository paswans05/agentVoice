"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { clearDeviceIdentity, loadDeviceIdentity } from "@/services/device";

export default function PhoneSettingsPage() {
  const router = useRouter();
  const id = typeof window !== "undefined" ? loadDeviceIdentity() : null;

  return (
    <div className="mx-auto max-w-md space-y-5 p-4 pt-6">
      <div className="flex items-center gap-3">
        <Link
          href="/gateway"
          className="inline-flex items-center gap-1 rounded-lg border border-zinc-800 px-3 py-1.5 text-xs"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </Link>
        <h1 className="text-lg font-bold">Device Settings</h1>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4 text-xs space-y-1.5 text-zinc-300">
        <div>Device ID: {id?.deviceId ?? "Not paired"}</div>
        <div>Device Name: {id?.deviceName ?? "—"}</div>
        <div>Server Origin: {id?.apiBaseUrl ?? "—"}</div>
        <div>Credential Storage: In-memory + sessionStorage (never localStorage)</div>
      </div>

      <button
        type="button"
        onClick={() => {
          clearDeviceIdentity();
          router.replace("/pair");
        }}
        className="w-full rounded-xl bg-rose-600 py-3 text-xs font-semibold text-white"
      >
        Disconnect & Clear Session
      </button>
    </div>
  );
}
