export const dynamic = 'force-dynamic';

import "@/lib/supabase/server-token";
import { FamilyExplorer } from "@/components/family/family-explorer";
import {
  getFamilyMembers,
  getPets,
  getPersonalRecords,
  getHealthReminders,
  getPetVaccinations,
} from "@/lib/nuclear-family";
import { MediaUploadWidget } from "@/components/family/media-upload";

export default async function NuclearFamilyPage() {
  const [members, pets, records, reminders, vaccinations] = await Promise.all([
    getFamilyMembers(),
    getPets(),
    getPersonalRecords(),
    getHealthReminders(),
    getPetVaccinations(),
  ]);

  return (
    <div className="space-y-6">
      <div>
        <p className="font-mono text-sm text-muted-foreground">
          FamilyVault / Vance Household
        </p>
        <h1 className="text-2xl font-semibold mt-1">Nuclear Family</h1>
        <p className="text-sm text-muted-foreground">
          {members.length} members · {pets.length} pet
          {pets.length === 1 ? "" : "s"} — personal records, health
          reminders, and vaccination timelines.
        </p>
      </div>

      <FamilyExplorer
        members={members}
        pets={pets}
        records={records}
        reminders={reminders}
        vaccinations={vaccinations}
      />

      <MediaUploadWidget />
    </div>
  );
}
