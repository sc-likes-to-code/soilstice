import type { Metadata } from "next";
import { FieldExplorerView } from "@/components/views/field-explorer-view";

export const metadata: Metadata = {
  title: "Field Explorer",
  description:
    "Interactive geospatial parcel roster, multi-depth soil indices, and resilience rankings across Reno County, Kansas.",
  alternates: {
    canonical: "/fields",
  },
  openGraph: {
    title: "Field Explorer · SOILSTICE",
    description:
      "Interactive geospatial parcel roster, multi-depth soil indices, and resilience rankings across Reno County, Kansas.",
    url: "https://soilstice.vercel.app/fields",
  },
};

export default function FieldsPage() {
  return <FieldExplorerView />;
}
