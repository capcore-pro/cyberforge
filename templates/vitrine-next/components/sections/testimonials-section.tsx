import { Star } from "lucide-react";

import type { SiteContent } from "@/lib/site-content";
import { Card, CardContent } from "@/components/ui/card";

export function TestimonialsSection({ content }: { content: SiteContent }) {
  const items = content.home.testimonials;

  return (
    <section className="border-y border-border/60 bg-card/30 py-16 md:py-24">
      <div className="container space-y-10">
        <div className="text-center">
          <p className="text-sm font-semibold uppercase tracking-wider text-primary">
            Témoignages
          </p>
          <h2 className="mt-2 font-display text-3xl font-bold tracking-tight md:text-4xl">
            Ils nous font confiance
          </h2>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {items.map((item) => (
            <Card key={item.author} className="border-border/70 bg-background/50">
              <CardContent className="space-y-4 p-6">
                <div className="flex gap-0.5 text-primary" aria-hidden>
                  {Array.from({ length: item.rating }).map((_, i) => (
                    <Star key={i} className="h-4 w-4 fill-current" />
                  ))}
                </div>
                <blockquote className="text-sm leading-relaxed text-muted-foreground">
                  &ldquo;{item.quote}&rdquo;
                </blockquote>
                <footer>
                  <p className="font-medium">{item.author}</p>
                  <p className="text-xs text-muted-foreground">{item.role}</p>
                </footer>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
