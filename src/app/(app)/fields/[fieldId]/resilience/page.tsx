import type { Metadata } from "next";
import { ResilienceView } from "@/components/views/resilience-view";

export const metadata: Metadata = { title: "Resilience Analysis" };

export default function ResiliencePage() {
  return <ResilienceView />;
}
