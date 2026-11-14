import type { Metadata } from "next";
import { RotationView } from "@/components/views/rotation-view";

export const metadata: Metadata = { title: "Rotation Lab" };

export default function RotationPage() {
  return <RotationView />;
}
