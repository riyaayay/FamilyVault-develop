"use client";

import { PricingSection } from "@/components/ui/pricing";

const plans = [
  {
    name: "Starter",
    price: "0",
    yearlyPrice: "0",
    period: "month",
    features: [
      "1 household, up to 6 members",
      "Biometric media sorting",
      "Review inbox & timeline",
      "1 GB encrypted vault",
      "Community support",
    ],
    description: "For a single household getting organised.",
    buttonText: "Start free",
    href: "/sign-up",
  },
  {
    name: "Family",
    price: "12",
    yearlyPrice: "9",
    period: "month",
    features: [
      "Everything in Starter",
      "Unlimited members & pets",
      "Living family tree & kinship paths",
      "Time capsules and legacy sharing",
      "100 GB encrypted vault",
    ],
    description: "The everyday plan for growing families.",
    buttonText: "Choose Family",
    href: "/sign-up",
    isPopular: true,
  },
  {
    name: "Clan",
    price: "29",
    yearlyPrice: "23",
    period: "month",
    features: [
      "Everything in Family",
      "Multi-household clan graph",
      "Three-tier privacy controls",
      "Trustee signatures & audit trail",
      "1 TB encrypted vault",
    ],
    description: "For large joint families and estates.",
    buttonText: "Talk to us",
    href: "/sign-up",
  },
];

export function LandingPricing() {
  return (
    <section id="pricing" className="scroll-mt-24">
      <PricingSection
        plans={plans}
        title="Plans for every clan"
        description={"Start with your household and grow into a clan.\nAll plans include biometric sorting and end-to-end encryption."}
      />
    </section>
  );
}
