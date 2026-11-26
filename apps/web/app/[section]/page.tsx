import { SIDEBAR_NAV_ITEMS } from "@agentvoice/config";
import { notFound } from "next/navigation";
import { PhasePlaceholder } from "@/components/phase-placeholder";

export default async function ModuleSectionPage({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  const { section } = await params;
  const item = SIDEBAR_NAV_ITEMS.find((nav) => nav.href === `/${section}`);

  if (!item) {
    notFound();
  }

  return (
    <PhasePlaceholder
      title={item.label}
      description={item.description}
      phase={item.phase}
    />
  );
}
