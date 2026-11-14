import type { Metadata } from "next";
import { EvidenceView } from "@/components/views/evidence-view";

export const metadata: Metadata = { title: "Evidence & data sources" };

export default function EvidencePage() {
  return <EvidenceView />;
}
