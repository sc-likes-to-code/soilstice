import type { Metadata } from "next";
import { Fraunces, IBM_Plex_Mono, Manrope } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { DataModeBanner } from "@/components/layout/data-mode-banner";

const fraunces = Fraunces({ variable: "--font-fraunces", subsets: ["latin"], axes: ["opsz", "SOFT"] });
const manrope = Manrope({ variable: "--font-manrope", subsets: ["latin"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500", "600"] });

export const metadata: Metadata = {
  title: { default: "SOILSTICE — Field resilience intelligence", template: "%s · SOILSTICE" },
  description: "Field-level agricultural intelligence from NASA Earth observation and USDA data: environment, crop history, resilience and explainable rotation options.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${fraunces.variable} ${manrope.variable} ${plexMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <Providers>
          <DataModeBanner />
          {children}
        </Providers>
      </body>
    </html>
  );
}
