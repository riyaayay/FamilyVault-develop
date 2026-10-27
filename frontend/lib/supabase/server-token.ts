import "server-only";

import { registerServerTokenProvider } from "@/lib/api";
import { createClient } from "./server";

// Imported for its side effect by the dashboard layout: lets lib/api.ts attach
// the signed-in user's token to backend calls made from Server Components.
// cookies() is request-scoped, so one registered reader serves every request.
registerServerTokenProvider(async () => {
  const supabase = await createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? "";
});
