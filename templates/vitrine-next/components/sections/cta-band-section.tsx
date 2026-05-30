import Link from "next/link";

import type { SiteContent } from "@/lib/site-content";
import { Button } from "@/components/ui/button";

export function CtaBandSection({ content }: { content: SiteContent }) {
  const cta = content.home.ctaBand;

  return (
    <section className="py-16 md:py-20">
      <div className="container">
        <div className="relative overflow-hidden rounded-2xl border border-primary/30 bg-gradient-to-br from-primary/20 via-card to-card px-6 py-12 text-center shadow-glow md:px-12">
          <div className="relative z-10 mx-auto max-w-2xl space-y-4">
            <h2
              className="font-display text-2xl font-bold tracking-tight md:text-3xl"
              data-cms="text"
              data-cms-key="home.ctaBand.title"
              data-cms-label="Titre bandeau CTA"
            >
              {cta.title}
            </h2>
            <p
              className="text-muted-foreground"
              data-cms="text"
              data-cms-key="home.ctaBand.text"
              data-cms-label="Texte bandeau CTA"
            >
              {cta.text}
            </p>
            <Button asChild size="lg">
              <Link href={cta.buttonHref}>
                <span
                  data-cms="text"
                  data-cms-key="home.ctaBand.buttonLabel"
                  data-cms-label="Bouton bandeau CTA"
                >
                  {cta.buttonLabel}
                </span>
              </Link>
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
