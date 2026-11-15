import type { Metadata } from "next";
import { EvidenceView } from "@/components/views/evidence-view";

export const metadata: Metadata = {
  title: "Evidence & Data Provenance",
  description:
    "Scientific data registry for SOILSTICE: NASA POWER agrometeorology, USDA NRCS SSURGO soil surveys, USDA NASS Cropland Data Layer 20-year history, and NASA SRTM topography.",
  alternates: {
    canonical: "/evidence",
  },
  openGraph: {
    title: "Evidence & Data Provenance · SOILSTICE",
    description:
      "Scientific data registry for SOILSTICE: NASA POWER agrometeorology, USDA NRCS SSURGO soil surveys, USDA NASS Cropland Data Layer 20-year history, and NASA SRTM topography.",
    url: "https://soilstice.vercel.app/evidence",
  },
};

export default function EvidencePage() {
  return <EvidenceView />;
}
