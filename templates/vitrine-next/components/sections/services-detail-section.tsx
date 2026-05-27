import { CheckCircle2 } from "lucide-react";

import type { SiteContent } from "@/lib/site-content";
import { UnsplashImageBlock } from "@/components/unsplash-image";
import { cn } from "@/lib/utils";

export function ServicesDetailSection({ content }: { content: SiteContent }) {
  const { intro, sections } = content.servicesPage;

  return (
    <div className="space-y-16 md:space-y-24">
      <header className="container max-w-3xl space-y-4 pt-8 md:pt-12">
        <p className="text-sm font-semibold uppercase tracking-wider text-primary">
          Services
        </p>
        <h1 className="font-display text-3xl font-bold tracking-tight md:text-5xl">
          {intro.title}
        </h1>
        <p className="text-lg text-muted-foreground">{intro.description}</p>
      </header>

      {sections.map((section, index) => {
        const reversed = index % 2 === 1;

        return (
          <section
            key={section.id}
            id={section.id}
            className="scroll-mt-24 border-t border-border/50 py-12 md:py-16"
          >
            <div className="container grid items-center gap-10 lg:grid-cols-2 lg:gap-14">
              <div
                className={cn(
                  "relative aspect-[4/3] overflow-hidden rounded-2xl border border-border/60",
                  reversed && "lg:order-2",
                )}
              >
                <UnsplashImageBlock
                  image={section.image}
                  sizes="(max-width: 1024px) 100vw, 50vw"
                />
              </div>
              <div className={cn("space-y-5", reversed && "lg:order-1")}>
                <h2 className="font-display text-2xl font-bold tracking-tight md:text-3xl">
                  {section.title}
                </h2>
                <p className="text-muted-foreground leading-relaxed">
                  {section.description}
                </p>
                {section.bullets?.length ? (
                  <ul className="space-y-2">
                    {section.bullets.map((bullet) => (
                      <li
                        key={bullet}
                        className="flex items-start gap-2 text-sm text-muted-foreground"
                      >
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </div>
          </section>
        );
      })}
    </div>
  );
}
