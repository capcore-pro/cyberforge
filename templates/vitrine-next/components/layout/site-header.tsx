"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, Phone, Wrench } from "lucide-react";

import type { NavItem, SiteContent } from "@/lib/site-content";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

interface SiteHeaderProps {
  content: SiteContent;
}

function NavLinks({
  items,
  pathname,
  onNavigate,
}: {
  items: NavItem[];
  pathname: string;
  onNavigate?: () => void;
}) {
  return (
    <nav className="flex flex-col gap-1 md:flex-row md:items-center md:gap-1">
      {items.map((item) => {
        const active =
          item.href === "/"
            ? pathname === "/"
            : pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

export function SiteHeader({ content }: SiteHeaderProps) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const { meta, navigation, footer } = content;

  return (
    <header className="sticky top-0 z-40 border-b border-border/60 bg-background/85 backdrop-blur-md">
      <div className="container flex h-16 items-center justify-between gap-4">
        <Link href="/" className="flex min-w-0 items-center gap-2">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <Wrench className="h-5 w-5" aria-hidden />
          </span>
          <span className="min-w-0">
            <span className="block truncate font-display text-sm font-semibold tracking-tight md:text-base">
              <span
                data-cms="text"
                data-cms-key="meta.businessName"
                data-cms-label="Nom entreprise"
              >
                {meta.businessName}
              </span>
            </span>
            <span className="hidden truncate text-xs text-muted-foreground sm:block">
              <span data-cms="text" data-cms-key="meta.tagline" data-cms-label="Accroche">
                {meta.tagline}
              </span>
            </span>
          </span>
        </Link>

        <div className="hidden items-center gap-6 md:flex">
          <NavLinks items={navigation} pathname={pathname} />
          <Button asChild size="sm">
            <Link href="/contact">Devis gratuit</Link>
          </Button>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          {footer.phone ? (
            <Button asChild variant="outline" size="icon" className="shrink-0">
              <a href={`tel:${footer.phone.replace(/\s/g, "")}`}>
                <Phone className="h-4 w-4" />
                <span className="sr-only">Appeler</span>
              </a>
            </Button>
          ) : null}
          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" size="icon" aria-label="Menu">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="flex flex-col">
              <SheetHeader>
                <SheetTitle>{meta.businessName}</SheetTitle>
              </SheetHeader>
              <div className="mt-6 flex flex-1 flex-col gap-6">
                <NavLinks
                  items={navigation}
                  pathname={pathname}
                  onNavigate={() => setMenuOpen(false)}
                />
                <Button asChild className="mt-auto w-full">
                  <Link href="/contact">Demander un devis</Link>
                </Button>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
