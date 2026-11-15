import type { Metadata } from "next";
import { DashboardView } from "@/components/views/dashboard-view";

export const metadata: Metadata = {
  title: "Farm Dashboard",
  description:
    "Farm overview, field attention ranking, and multi-source data coverage for Kansas agricultural parcels.",
  alternates: {
    canonical: "/dashboard",
  },
  openGraph: {
    title: "Farm Dashboard · SOILSTICE",
    description:
      "Farm overview, field attention ranking, and multi-source data coverage for Kansas agricultural parcels.",
    url: "https://soilstice.vercel.app/dashboard",
  },
};

export default function DashboardPage() {
  return <DashboardView />;
}
