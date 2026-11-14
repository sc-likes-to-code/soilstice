import type { Metadata } from "next";
import { EnvironmentView } from "@/components/views/environment-view";

export const metadata: Metadata = { title: "Environmental Intelligence" };

export default function EnvironmentPage() {
  return <EnvironmentView />;
}
