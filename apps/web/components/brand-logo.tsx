import { APP_CONFIG } from "@agentvoice/config";

interface BrandLogoProps {
  showSubtitle?: boolean;
  size?: "sm" | "md";
}

export function BrandLogo({ size = "md" }: BrandLogoProps) {
  const heightClass = size === "sm" ? "h-10" : "h-11";

  return (
    <div className="flex items-center">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/logo.png"
        alt={APP_CONFIG.name}
        className={`${heightClass} w-auto shrink-0 object-contain`}
      />
    </div>
  );
}
