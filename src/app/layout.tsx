import type { Metadata, Viewport } from "next";
import { Fraunces, IBM_Plex_Mono, Manrope } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { StructuredData } from "@/components/seo/structured-data";

const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], axes: ["opsz", "SOFT"] });
const manrope = Manrope({ variable: "--font-manrope", subsets: ["latin"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500", "600"] });

export const viewport: Viewport = {
  themeColor: "#0e2617",
  colorScheme: "light dark",
  width: "device-width",
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL("https://soilstice.vercel.app"),
  title: {
    default: "SOILSTICE — Field Resilience Intelligence",
    template: "%s · SOILSTICE",
  },
  description:
    "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
  applicationName: "SOILSTICE",
  authors: [{ name: "SOILSTICE Team", url: "https://soilstice.vercel.app" }],
  creator: "SOILSTICE Team",
  publisher: "SOILSTICE",
  category: "Agriculture & Earth Observation",
  keywords: [
    "SOILSTICE",
    "Field Resilience Intelligence",
    "agricultural intelligence",
    "crop rotation",
    "crop suitability",
    "NASA POWER",
    "USDA SSURGO",
    "USDA Cropland Data Layer",
    "NASA Space Apps Challenge 2026",
    "precision agriculture",
    "Kansas agriculture",
    "Liebig law of the minimum",
    "soil moisture",
    "agrometeorology",
    "soil resilience",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://soilstice.vercel.app",
    siteName: "SOILSTICE",
    title: "SOILSTICE — Field Resilience Intelligence",
    description:
      "SOILSTICE transforms NASA Earth observations, USDA soil surveys and historical crop records into explainable field intelligence for smarter, climate-resilient agricultural decisions.",
    images: [
      {
        url: "/og-image.png",
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
    images: ["/og-image.png"],
    creator: "@soilstice",
    site: "@soilstice",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon-32x32.png", sizes: "32x32", type: "image/png" },
      { url: "/favicon-16x16.png", sizes: "16x16", type: "image/png" },
      { url: "/favicon.ico", sizes: "32x32" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    other: [
      { rel: "mask-icon", url: "/icon.svg", color: "#143320" },
    ],
  },
  manifest: "/manifest.webmanifest",
  verification: {
    google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION || undefined,
    other: process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION
      ? { "msvalidate.01": process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION }
      : undefined,
  },
};

const HIDE_SCROLLBAR_CSS = `
  html, body, * {
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
  }
  ::-webkit-scrollbar {
    display: none !important;
    width: 0px !important;
    height: 0px !important;
    background: transparent !important;
  }
  ::-webkit-scrollbar-track,
  ::-webkit-scrollbar-track-piece,
  ::-webkit-scrollbar-thumb,
  ::-webkit-scrollbar-button,
  ::-webkit-scrollbar-corner {
    display: none !important;
    width: 0px !important;
    height: 0px !important;
    background: transparent !important;
  }
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      data-scroll-behavior="smooth"
      className={`${fraunces.variable} ${manrope.variable} ${plexMono.variable} h-full antialiased`}
    >
      <head>
        <style dangerouslySetInnerHTML={{ __html: HIDE_SCROLLBAR_CSS }} />
      </head>
      <body className="flex min-h-full flex-col">
        <StructuredData />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
