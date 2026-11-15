import type { Metadata } from "next";
import { LandingView } from "@/components/views/landing-view";

export const metadata: Metadata = {
  title: "SOILSTICE — Field Resilience Intelligence",
  description:
    "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: "SOILSTICE — Field Resilience Intelligence",
    description:
      "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
    url: "https://soilstice.vercel.app",
    siteName: "SOILSTICE",
    locale: "en_US",
    type: "website",
    images: [
      {
        url: "/og-image-v2.png",
        width: 1200,
        height: 630,
        alt: "SOILSTICE — Field Resilience Intelligence | Satellite-Powered Agricultural Intelligence",
        type: "image/png",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SOILSTICE — Field Resilience Intelligence",
    description:
      "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
    images: ["/og-image-v2.png"],
    creator: "@soilstice",
    site: "@soilstice",
  },
};

export default function LandingPage() {
  return <LandingView />;
}
