import { Suspense, type ReactNode } from "react";
import { FieldLayoutClient, FieldLayoutSkeleton } from "@/components/layout/field-layout";

/** Field-scoped tabs. The dynamic param is read in a client component inside Suspense (Cache Components rule). */
export default function FieldLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<FieldLayoutSkeleton />}>
      <FieldLayoutClient>{children}</FieldLayoutClient>
    </Suspense>
  );
}
