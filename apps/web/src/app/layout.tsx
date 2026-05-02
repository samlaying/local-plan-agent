import "./globals.css";
import { WorkbenchProvider } from "@/features/planner/contexts/WorkbenchContext";
import { ErrorBoundary } from "@/components/ErrorBoundary";

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
            {children}
          </WorkbenchProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
