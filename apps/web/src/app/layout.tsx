import "./globals.css";
import { WorkbenchProvider } from "@/features/planner/contexts/WorkbenchContext";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AppShell } from "@/components/layout";

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body>
        <ErrorBoundary>
          <WorkbenchProvider>
            <AppShell>{children}</AppShell>
          </WorkbenchProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
