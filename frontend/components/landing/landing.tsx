"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { OrbGallery } from "@/components/landing/orb-gallery";
import { LandingIntro } from "@/components/landing/intro-animation";
import { LandingPricing } from "@/components/landing/pricing";
import { Footer } from "@/components/landing/footer";

export function Landing() {
  const router = useRouter();

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const { data } = await createClient().auth.getSession();
        if (mounted && data.session) router.replace("/dashboard");
      } catch {
        // Supabase unconfigured / offline — stay on the landing page.
      }
    })();
    return () => {
      mounted = false;
    };
  }, [router]);

  return (
    <div className="min-h-screen w-full bg-background overflow-x-clip overflow-y-visible">
      <OrbGallery />
      <LandingIntro />
      <LandingPricing />
      <Footer />
    </div>
  );
}