"use client";

import * as React from "react";
import {
    FileText,
    HeartPulse,
    Syringe,
    ChevronRight,
    Plus,
    X,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type {
    FamilyMember,
    Pet,
    MembershipRole,
    RelationToHead,
    PersonalRecord,
    HealthReminder,
    PetVaccination,
    Visibility,
} from "@/lib/nuclear-family";
import { NUCLEAR_FAMILY_ID } from "@/lib/nuclear-family";

const MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

// Deterministic date formatting (no Intl locale calls) so server and
// client always render identical text — toLocaleDateString can format
// "Sep" vs "Sept" differently between Node's ICU data and the browser's,
// which causes a hydration mismatch.
function formatDate(iso: string) {
    const [year, month, day] = iso.split("-").map(Number);
    return `${day} ${MONTHS[month - 1]} ${year}`;
}

const visibilityLabel: Record<Visibility, string> = {
    JOINT_CLAN: "joint clan",
    NUCLEAR_HOUSEHOLD: "household",
    PRIVATE_STRICT: "private",
};

const visibilityStatus: Record<
    Visibility,
    "joint_clan" | "nuclear_household" | "private_strict"
> = {
    JOINT_CLAN: "joint_clan",
    NUCLEAR_HOUSEHOLD: "nuclear_household",
    PRIVATE_STRICT: "private_strict",
};

// Human-readable label for a member's relation_to_head. This is a stand-in
// for Riya's future Neo4j kinship-title service (protocol Section 11.4),
// which would compute viewer-relative titles (e.g. "Father", "Sister").
// With 3 generations now in the seed data (grandparents/parents/children)
// a simple Head/Spouse/Son/Daughter mapping no longer holds, so this just
// formats the relation_to_head value directly until that service exists.
const relationDisplay: Record<RelationToHead, string> = {
    HEAD: "Head",
    SPOUSE: "Spouse",
    CHILD: "Child",
    PARENT: "Parent",
    SIBLING: "Sibling",
    EXTENDED: "Extended",
};

function relationLabel(member: FamilyMember): string {
    return relationDisplay[member.relationToHead];
}

const ACCENTS = ["chart-1", "chart-2", "chart-3", "chart-4", "chart-5"] as const;

function Avatar({
    initials,
    accent,
    size = "sm",
}: {
    initials: string;
    accent: string;
    size?: "sm" | "md";
}) {
    const dimension = size === "md" ? "size-9 text-sm" : "size-6 text-[0.65rem]";
    return (
        <span
            className={`inline-flex ${dimension} shrink-0 items-center justify-center rounded-full font-semibold text-white`}
            style={{ backgroundColor: `var(--${accent})` }}
        >
            {initials}
        </span>
    );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
    return (
        <button
            onClick={onClick}
            className="flex items-center gap-1 rounded-md border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
            <Plus className="size-3.5" />
            {label}
        </button>
    );
}

function AddMemberForm({
    onSubmit,
    onCancel,
}: {
    onSubmit: (name: string, role: MembershipRole, relationToHead: RelationToHead) => void;
    onCancel: () => void;
}) {
    const [name, setName] = React.useState("");
    const [role, setRole] = React.useState<MembershipRole>("MEMBER");
    const [relationToHead, setRelationToHead] = React.useState<RelationToHead>("CHILD");

    return (
        <form
            onSubmit={(e) => {
                e.preventDefault();
                if (!name.trim()) return;
                onSubmit(name.trim(), role, relationToHead);
            }}
            className="flex flex-wrap items-end gap-3 rounded-md border border-border p-3 mt-3"
        >
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                Name
                <input
                    autoFocus
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Raghav Vance"
                    className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm text-foreground w-48"
                />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                Relation to head
                <select
                    value={relationToHead}
                    onChange={(e) => setRelationToHead(e.target.value as RelationToHead)}
                    className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm text-foreground"
                >
                    <option value="HEAD">Head</option>
                    <option value="SPOUSE">Spouse</option>
                    <option value="CHILD">Child</option>
                    <option value="PARENT">Parent</option>
                    <option value="SIBLING">Sibling</option>
                    <option value="EXTENDED">Extended</option>
                </select>
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                Role
                <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as MembershipRole)}
                    className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm text-foreground"
                >
                    <option value="ADMIN">Admin</option>
                    <option value="MEMBER">Member</option>
                    <option value="CHILD">Child</option>
                    <option value="VIEWER">Viewer</option>
                </select>
            </label>
            <button
                type="submit"
                className="rounded-md bg-foreground text-background px-3 py-1.5 text-sm font-medium"
            >
                Add member
            </button>
            <button
                type="button"
                onClick={onCancel}
                className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground px-2 py-1.5"
            >
                <X className="size-4" /> Cancel
            </button>
        </form>
    );
}

function AddPetForm({
    onSubmit,
    onCancel,
}: {
    onSubmit: (name: string, breed: string) => void;
    onCancel: () => void;
}) {
    const [name, setName] = React.useState("");
    const [breed, setBreed] = React.useState("");

    return (
        <form
            onSubmit={(e) => {
                e.preventDefault();
                if (!name.trim()) return;
                onSubmit(name.trim(), breed.trim());
            }}
            className="flex flex-wrap items-end gap-3 rounded-md border border-border p-3 mt-3"
        >
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                Name
                <input
                    autoFocus
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Barnaby"
                    className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm text-foreground w-40"
                />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
                Breed
                <input
                    value={breed}
                    onChange={(e) => setBreed(e.target.value)}
                    placeholder="e.g. Golden Retriever"
                    className="rounded-md border border-border bg-transparent px-2 py-1.5 text-sm text-foreground w-40"
                />
            </label>
            <button
                type="submit"
                className="rounded-md bg-foreground text-background px-3 py-1.5 text-sm font-medium"
            >
                Add pet
            </button>
            <button
                type="button"
                onClick={onCancel}
                className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground px-2 py-1.5"
            >
                <X className="size-4" /> Cancel
            </button>
        </form>
    );
}

function SelectCard({
    initials,
    accent,
    name,
    label,
    selected,
    onClick,
}: {
    initials: string;
    accent: string;
    name: string;
    label: string;
    selected: boolean;
    onClick: () => void;
}) {
    return (
        <button
            onClick={onClick}
            className={`flex items-center gap-2 rounded-md border px-3 py-2 text-left transition-colors ${selected ? "border-foreground bg-foreground text-background" : "border-border hover:bg-muted"
                }`}
        >
            <Avatar initials={initials} accent={accent} size="md" />
            <span className="flex flex-col leading-tight">
                <span className="text-sm font-medium">{name}</span>
                <span className={`text-xs ${selected ? "text-background/70" : "text-muted-foreground"}`}>
                    {label}
                </span>
            </span>
        </button>
    );
}

function FileSection<T extends { id: string }>({
    path,
    icon: Icon,
    items,
    emptyLabel,
    renderRow,
}: {
    path: string;
    icon: React.ComponentType<{ className?: string }>;
    items: T[];
    emptyLabel: string;
    renderRow: (item: T) => React.ReactNode;
}) {
    return (
        <details open className="group border border-border rounded-lg">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 select-none">
                <ChevronRight className="size-4 text-muted-foreground transition-transform group-open:rotate-90" />
                <Icon className="size-4 text-muted-foreground" />
                <span className="font-mono text-sm text-foreground">{path}</span>
                <span className="text-xs text-muted-foreground">({items.length})</span>
            </summary>
            <div className="border-t border-border divide-y divide-border">
                {items.length === 0 ? (
                    <p className="px-4 py-4 text-sm text-muted-foreground">{emptyLabel}</p>
                ) : (
                    items.map(renderRow)
                )}
            </div>
        </details>
    );
}

function FileRow({
    name,
    date,
    rightBadge,
}: {
    name: string;
    date: string;
    rightBadge: React.ReactNode;
}) {
    return (
        <div className="flex flex-wrap items-center gap-3 px-4 py-3 hover:bg-muted/50">
            <span className="text-sm text-foreground">{name}</span>
            <span className="ml-auto flex items-center gap-3">
                <span className="font-mono text-xs text-muted-foreground">{formatDate(date)}</span>
                {rightBadge}
            </span>
        </div>
    );
}

export function FamilyExplorer({
    members: initialMembers,
    pets: initialPets,
    records,
    reminders,
    vaccinations,
}: {
    members: FamilyMember[];
    pets: Pet[];
    records: PersonalRecord[];
    reminders: HealthReminder[];
    vaccinations: PetVaccination[];
}) {
    const [members, setMembers] = React.useState(initialMembers);
    const [pets, setPets] = React.useState(initialPets);
    const [selectedId, setSelectedId] = React.useState<string>("all");
    const [showAddMember, setShowAddMember] = React.useState(false);
    const [showAddPet, setShowAddPet] = React.useState(false);

    function addMember(name: string, role: MembershipRole, relationToHead: RelationToHead) {
        const id = `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}`;
        setMembers((prev) => [
            ...prev,
            {
                id,
                fullName: name,
                role,
                relationToHead,
                initials: name.slice(0, 2).toUpperCase(),
                accent: ACCENTS[prev.length % ACCENTS.length],
            },
        ]);
        setShowAddMember(false);
    }

    function addPet(name: string, breed: string) {
        const id = `${name.toLowerCase().replace(/\s+/g, "-")}-${Date.now()}`;
        setPets((prev) => [
            ...prev,
            {
                id,
                nuclearFamilyId: NUCLEAR_FAMILY_ID,
                name,
                petType: "OTHER",
                breed: breed || undefined,
                initials: name.slice(0, 2).toUpperCase(),
                accent: ACCENTS[prev.length % ACCENTS.length],
            },
        ]);
        setShowAddPet(false);
    }

    const isPetSelected = pets.some((p) => p.id === selectedId);

    const filteredRecords =
        selectedId === "all"
            ? records.filter((r) => r.visibility !== "PRIVATE_STRICT")
            : records.filter((r) => r.ownerId === selectedId);
    const filteredReminders =
        selectedId === "all" ? reminders : reminders.filter((r) => r.personId === selectedId);
    const filteredVaccinations =
        selectedId === "all"
            ? vaccinations
            : isPetSelected
                ? vaccinations.filter((v) => v.petId === selectedId)
                : [];

    return (
        <div className="space-y-8">
            <div>
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-medium text-foreground">Household</h2>
                    <AddButton label="Add member" onClick={() => setShowAddMember((v) => !v)} />
                </div>
                <div className="flex flex-wrap gap-3">
                    <button
                        onClick={() => setSelectedId("all")}
                        className={`rounded-md border px-3 py-2 text-sm ${selectedId === "all"
                            ? "border-foreground bg-foreground text-background"
                            : "border-border hover:bg-muted"
                            }`}
                    >
                        All members
                    </button>
                    {members.map((member) => (
                        <SelectCard
                            key={member.id}
                            initials={member.initials}
                            accent={member.accent}
                            name={member.fullName}
                            label={relationLabel(member)}
                            selected={selectedId === member.id}
                            onClick={() => setSelectedId(member.id)}
                        />
                    ))}
                </div>
                {showAddMember && <AddMemberForm onSubmit={addMember} onCancel={() => setShowAddMember(false)} />}
            </div>

            <div>
                <div className="flex items-center justify-between mb-3">
                    <h2 className="text-sm font-medium text-foreground">Pets</h2>
                    <AddButton label="Add pet" onClick={() => setShowAddPet((v) => !v)} />
                </div>
                <div className="flex flex-wrap gap-3">
                    {pets.length === 0 ? (
                        <p className="text-sm text-muted-foreground">No pets yet.</p>
                    ) : (
                        pets.map((pet) => (
                            <SelectCard
                                key={pet.id}
                                initials={pet.initials}
                                accent={pet.accent}
                                name={pet.name}
                                label={pet.breed ?? pet.petType}
                                selected={selectedId === pet.id}
                                onClick={() => setSelectedId(pet.id)}
                            />
                        ))
                    )}
                </div>
                {showAddPet && <AddPetForm onSubmit={addPet} onCancel={() => setShowAddPet(false)} />}
            </div>

            <p className="text-xs text-muted-foreground -mt-2">
                {selectedId === "all"
                    ? "Select a family member or pet to see just their records, or add someone new."
                    : "Every household member can still see everyone's non-private records."}
            </p>

            <div className="space-y-4">
                <FileSection
                    path="personal-records/"
                    icon={FileText}
                    items={filteredRecords}
                    emptyLabel="No records for this selection."
                    renderRow={(record: PersonalRecord) => (
                        <FileRow
                            key={record.id}
                            name={record.title}
                            date={record.updatedAt}
                            rightBadge={
                                <Badge status={visibilityStatus[record.visibility]}>
                                    {visibilityLabel[record.visibility]}
                                </Badge>
                            }
                        />
                    )}
                />

                <FileSection
                    path="health-reminders/"
                    icon={HeartPulse}
                    items={filteredReminders}
                    emptyLabel="No health reminders for this selection."
                    renderRow={(reminder: HealthReminder) => (
                        <FileRow
                            key={reminder.id}
                            name={reminder.label}
                            date={reminder.dueDate}
                            rightBadge={<Badge status={reminder.status}>{reminder.status}</Badge>}
                        />
                    )}
                />

                <FileSection
                    path="pet-vaccinations/"
                    icon={Syringe}
                    items={filteredVaccinations}
                    emptyLabel="No vaccination records for this selection."
                    renderRow={(vax: PetVaccination) => (
                        <FileRow
                            key={vax.id}
                            name={vax.vaccine}
                            date={vax.dueDate}
                            rightBadge={<Badge status={vax.status}>{vax.status}</Badge>}
                        />
                    )}
                />
            </div>
        </div>
    );
}