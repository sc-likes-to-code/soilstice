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
        url: "https://soilstice.vercel.app/og-image-whatsapp-v1.jpg",
        secureUrl: "https://soilstice.vercel.app/og-image-whatsapp-v1.jpg",
        width: 1200,
        height: 630,
        alt: "SOILSTICE — Field Resilience Intelligence | Satellite-Powered Agricultural Intelligence",
        type: "image/jpeg",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "SOILSTICE — Field Resilience Intelligence",
    description:
      "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
    images: ["https://soilstice.vercel.app/og-image-whatsapp-v1.jpg"],
    creator: "@soilstice",
    site: "@soilstice",
  },
};

export default function LandingPage() {
  return <LandingView />;
}
