"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { PreferencesProvider } from "@/hooks/preferences";
import { isApiError } from "@/services";

export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60_000,
            refetchOnWindowFocus: false,
            // Retry only errors the contract marks retryable (API_CONTRACTS §4).
            retry: (count, err) => (isApiError(err) ? err.retryable && count < 1 : count < 1),
          },
        },
      }),
  );
  return (
    <QueryClientProvider client={client}>
      <PreferencesProvider>{children}</PreferencesProvider>
    </QueryClientProvider>
  );
}
