import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import type { SiteContent } from "@/lib/site-content";
import { UnsplashImageBlock } from "@/components/unsplash-image";
import { Button } from "@/components/ui/button";

export function HeroSection({ content }: { content: SiteContent }) {
  const { hero } = content.home;

  return (
    <section className="relative overflow-hidden">
      <div className="absolute inset-0">
        <UnsplashImageBlock
          image={hero.image}
          priority
          cmsKey="home.hero.image.url"
          cmsLabel="Image hero"
          className="h-full min-h-[520px] md:min-h-[640px]"
          sizes="100vw"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-background via-background/90 to-background/40 md:via-background/85 md:to-background/20" />
      </div>

      <div className="container relative flex min-h-[520px] flex-col justify-center py-16 md:min-h-[640px] md:py-24">
        <div className="max-w-2xl space-y-6">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <ShieldCheck className="h-3.5 w-3.5" />
            Artisan certifié · Rouen & agglo
          </div>
          <h1
            className="font-display text-4xl font-bold tracking-tight text-balance sm:text-5xl lg:text-6xl"
            data-cms="text"
            data-cms-key="home.hero.title"
            data-cms-label="Titre hero"
          >
            {hero.title}
          </h1>
          <p
            className="text-lg text-muted-foreground text-pretty sm:text-xl"
            data-cms="text"
            data-cms-key="home.hero.subtitle"
            data-cms-label="Sous-titre hero"
          >
            {hero.subtitle}
          </p>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <Button asChild size="lg">
              <Link href={hero.ctaPrimary.href}>
                <span
                  data-cms="text"
                  data-cms-key="home.hero.ctaPrimary.label"
                  data-cms-label="Bouton principal"
                >
                  {hero.ctaPrimary.label}
                </span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            {hero.ctaSecondary ? (
              <Button asChild variant="outline" size="lg">
                <Link href={hero.ctaSecondary.href}>{hero.ctaSecondary.label}</Link>
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}
