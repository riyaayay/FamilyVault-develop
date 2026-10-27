import "@/lib/supabase/server-token";
import { DashboardDock } from "@/components/dashboard/dashboard-dock";
import { SosButton } from "@/components/emergency/sos-button";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <SosButton />
      {/* pt-16 keeps page headers clear of the fixed SOS control */}
      <main className="flex-1 p-6 pt-16 pb-32">{children}</main>
      <div className="fixed bottom-3 left-0 right-0 z-40 flex justify-center px-3">
        <DashboardDock />
      </div>
    </div>
  );
}