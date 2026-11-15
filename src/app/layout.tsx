import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Manrope } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], axes: ["opsz", "SOFT"] });
const manrope = Manrope({ variable: "--font-manrope", subsets: ["latin"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500", "600"] });

export const metadata: Metadata = {
  title: { default: "SOILSTICE — Field resilience intelligence", template: "%s · SOILSTICE" },
  description: "Field-level agricultural intelligence from NASA Earth observation and USDA data: environment, crop history, resilience and explainable rotation options.",
  icons: {
    icon: [
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/favicon.ico", sizes: "32x32" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
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
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
