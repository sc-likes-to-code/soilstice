import type { Metadata } from "next";
import { ReportView } from "@/components/views/report-view";

export const metadata: Metadata = { title: "Field report" };

export default function ReportPage() {
  return <ReportView />;
}
