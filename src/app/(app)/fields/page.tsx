import type { Metadata } from "next";
import { FieldExplorerView } from "@/components/views/field-explorer-view";

export const metadata: Metadata = { title: "Field Explorer" };

export default function FieldsPage() {
  return <FieldExplorerView />;
}
