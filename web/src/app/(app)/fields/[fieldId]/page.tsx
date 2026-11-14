import type { Metadata } from "next";
import { FieldOverviewView } from "@/components/views/field-overview-view";

export const metadata: Metadata = { title: "Field overview" };

export default function FieldOverviewPage() {
  return <FieldOverviewView />;
}
