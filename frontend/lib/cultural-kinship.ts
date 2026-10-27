import { authHeaders } from "./api";

export type CulturalKinshipResponse = {
  term: string;
  english: string;
  generational_depth: number;
  gotra?: string;
  path_node_ids: string[];
};

const GRAPH_URL = process.env.NEXT_PUBLIC_GRAPH_API_URL || "http://localhost:8001";

export const CANONICAL_MEMBERS = {
  arthur: "00000000-0000-0000-0000-000000000001",
  eleanor: "00000000-0000-0000-0000-000000000002",
  david: "00000000-0000-0000-0000-000000000003",
  sarah: "00000000-0000-0000-0000-000000000004",
  michael: "00000000-0000-0000-0000-000000000005",
  clara: "00000000-0000-0000-0000-000000000006",
  robert: "00000000-0000-0000-0000-000000000007",
  lucas: "00000000-0000-0000-0000-000000000008",
  sophia: "00000000-0000-0000-0000-000000000009",
  emma: "00000000-0000-0000-0000-000000000010",
} as const;

const MOCK_KINSHIPS: Record<string, CulturalKinshipResponse> = {
  [`${CANONICAL_MEMBERS.lucas}_${CANONICAL_MEMBERS.robert}`]: {
    term: "Chacha",
    english: "Paternal Uncle",
    generational_depth: 1,
    gotra: "Vance-Kashyap",
    path_node_ids: [CANONICAL_MEMBERS.lucas, CANONICAL_MEMBERS.david, CANONICAL_MEMBERS.arthur, CANONICAL_MEMBERS.robert],
  },
  [`${CANONICAL_MEMBERS.robert}_${CANONICAL_MEMBERS.lucas}`]: {
    term: "Bhatija",
    english: "Paternal Nephew",
    generational_depth: 1,
    gotra: "Vance-Kashyap",
    path_node_ids: [CANONICAL_MEMBERS.robert, CANONICAL_MEMBERS.arthur, CANONICAL_MEMBERS.david, CANONICAL_MEMBERS.lucas],
  },
  [`${CANONICAL_MEMBERS.lucas}_${CANONICAL_MEMBERS.arthur}`]: {
    term: "Dada",
    english: "Paternal Grandfather",
    generational_depth: 2,
    gotra: "Vance-Kashyap",
    path_node_ids: [CANONICAL_MEMBERS.lucas, CANONICAL_MEMBERS.david, CANONICAL_MEMBERS.arthur],
  },
  [`${CANONICAL_MEMBERS.lucas}_${CANONICAL_MEMBERS.eleanor}`]: {
    term: "Dadi",
    english: "Paternal Grandmother",
    generational_depth: 2,
    gotra: "Vance-Kashyap",
    path_node_ids: [CANONICAL_MEMBERS.lucas, CANONICAL_MEMBERS.david, CANONICAL_MEMBERS.eleanor],
  },
  [`${CANONICAL_MEMBERS.sophia}_${CANONICAL_MEMBERS.emma}`]: {
    term: "Chachera Behen",
    english: "Paternal Cousin",
    generational_depth: 0,
    gotra: "Vance-Kashyap",
    path_node_ids: [CANONICAL_MEMBERS.sophia, CANONICAL_MEMBERS.david, CANONICAL_MEMBERS.arthur, CANONICAL_MEMBERS.michael, CANONICAL_MEMBERS.emma],
  },
};

export async function fetchCulturalKinship(
  personAId: string,
  personBId: string
): Promise<CulturalKinshipResponse> {
  const endpoint = `${GRAPH_URL}/api/graph/kinship/cultural/${personAId}/${personBId}`;

  try {
    const res = await fetch(endpoint, {
      signal: AbortSignal.timeout(2000),
      cache: "no-store",
      headers: await authHeaders(),
    });
    if (res.ok) {
      return (await res.json()) as CulturalKinshipResponse;
    }
  } catch {
    // Fallback to local test vectors
  }

  const directKey = `${personAId}_${personBId}`;
  const reverseKey = `${personBId}_${personAId}`;

  if (MOCK_KINSHIPS[directKey]) {
    return MOCK_KINSHIPS[directKey];
  }

  if (MOCK_KINSHIPS[reverseKey]) {
    const rev = MOCK_KINSHIPS[reverseKey];
    return {
      term: rev.term,
      english: rev.english,
      generational_depth: rev.generational_depth,
      gotra: rev.gotra,
      path_node_ids: [...rev.path_node_ids].reverse(),
    };
  }

  return {
    term: "Ristedaar",
    english: "Family Kin",
    generational_depth: 1,
    path_node_ids: [personAId, personBId],
  };
}
