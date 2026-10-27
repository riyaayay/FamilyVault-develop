import { DashboardDock } from "@/components/dashboard/dashboard-dock";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <main className="flex-1 p-6 pb-32">{children}</main>
      <div className="fixed bottom-3 left-0 right-0 z-40 flex justify-center px-3">
        <DashboardDock />
      </div>
    </div>
  );
}