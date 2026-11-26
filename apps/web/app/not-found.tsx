import Link from "next/link";

export default function NotFoundPage() {
  return (
    <div className="mx-auto max-w-lg py-16 text-center space-y-4">
      <h1 className="text-2xl font-semibold">Page Not Found</h1>
      <p className="text-sm text-muted-foreground">
        The requested agentVoice page does not exist.
      </p>
      <Link
        href="/"
        className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
      >
        Back to Overview
      </Link>
    </div>
  );
}
