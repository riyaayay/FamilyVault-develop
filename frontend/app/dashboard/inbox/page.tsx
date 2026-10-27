import { getFamilyMembers } from "@/lib/nuclear-family";
import { getInbox, getKinshipLabel } from "@/lib/media-inbox";
import type { InboxItem } from "@/lib/media-inbox";
import { InboxGrid } from "@/components/inbox/inbox-grid";

export const dynamic = "force-dynamic";

export default async function InboxPage() {
    const inbox = await getInbox();
    const members = await getFamilyMembers();

    // how each contributor is related to the viewer, for the kinship pill
    const items: InboxItem[] = [];
    for (const raw of inbox) {
        const kinship = await getKinshipLabel(raw.uploadedBy, raw.kinship);
        items.push({ ...raw, kinship });
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-xl font-semibold text-foreground">Media inbox</h1>
                <p className="text-sm text-muted-foreground">
                    Photos, audio and video that need a decision before they reach the
                    family timeline.
                </p>
            </div>
            <InboxGrid initialItems={items} members={members} />
        </div>
    );
}