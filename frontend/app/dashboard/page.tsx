export const dynamic = 'force-dynamic';

import { getFamilyMembers, getPets } from "@/lib/nuclear-family";
import { DashboardBento } from "@/components/dashboard/dashboard-bento";

export default async function DashboardHome() {
  const [members, pets] = await Promise.all([getFamilyMembers(), getPets()]);

  return <DashboardBento memberCount={members.length} petCount={pets.length} />;
}