import Link from "next/link";
import { ArrowUpRight } from "lucide-react";

import type { SiteContent } from "@/lib/site-content";
import { UnsplashImageBlock } from "@/components/unsplash-image";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function ServicesPreviewSection({ content }: { content: SiteContent }) {
  const items = content.home.servicesPreview;

  return (
    <section className="py-16 md:py-24">
      <div className="container space-y-10">
        <div className="max-w-2xl space-y-3">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">
            Nos expertises
          </p>
          <h2 className="font-display text-3xl font-bold tracking-tight md:text-4xl">
            Des solutions pour chaque besoin
          </h2>
          <p className="text-muted-foreground">
            Dépannage, rénovation et chauffage — une équipe locale, réactive et transparente.
          </p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {items.map((service) => (
            <Card
              key={service.title}
              className="group overflow-hidden transition hover:border-primary/40"
            >
              <div className="relative aspect-[4/3] overflow-hidden">
                <UnsplashImageBlock
                  image={service.image}
                  sizes="(max-width: 768px) 100vw, 33vw"
                />
              </div>
              <CardHeader>
                <CardTitle className="text-lg">{service.title}</CardTitle>
                <CardDescription>{service.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Link
                  href={service.href}
                  className="inline-flex items-center gap-1 text-sm font-medium text-primary hover:underline"
                >
                  En savoir plus
                  <ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
