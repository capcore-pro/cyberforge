/** Services SaaS récurrents — coûts mensuels estimés et URLs de facturation. */

export interface SubscriptionService {
  id: string;
  name: string;
  icon: string;
  monthlyEur: number;
  billingUrl: string;
  note?: string;
}

export const SUBSCRIPTION_SERVICES: SubscriptionService[] = [
  {
    id: "railway",
    name: "Railway",
    icon: "🚂",
    monthlyEur: 20,
    billingUrl: "https://railway.app/account/billing",
    note: "Hébergement backend",
  },
  {
    id: "vercel",
    name: "Vercel",
    icon: "▲",
    monthlyEur: 20,
    billingUrl: "https://vercel.com/account/billing",
    note: "Hébergement frontend",
  },
  {
    id: "supabase",
    name: "Supabase",
    icon: "⚡",
    monthlyEur: 25,
    billingUrl: "https://supabase.com/dashboard/org/_/billing",
    note: "Base de données & auth",
  },
  {
    id: "brevo",
    name: "Brevo",
    icon: "✉",
    monthlyEur: 0,
    billingUrl: "https://app.brevo.com/billing/addon/customize",
    note: "Emails transactionnels",
  },
  {
    id: "replicate",
    name: "Replicate",
    icon: "🤖",
    monthlyEur: 15,
    billingUrl: "https://replicate.com/account/billing",
    note: "Génération d'images IA",
  },
  {
    id: "firecrawl",
    name: "Firecrawl",
    icon: "🔥",
    monthlyEur: 16,
    billingUrl: "https://www.firecrawl.dev/app/billing",
    note: "Scraping web",
  },
  {
    id: "pexels",
    name: "Pexels",
    icon: "📷",
    monthlyEur: 0,
    billingUrl: "https://www.pexels.com/api/",
    note: "Banque d'images (gratuit)",
  },
];

export function subscriptionMonthlyTotal(
  services: SubscriptionService[] = SUBSCRIPTION_SERVICES,
): number {
  return services.reduce((sum, s) => sum + s.monthlyEur, 0);
}
