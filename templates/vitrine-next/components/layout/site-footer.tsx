import Link from "next/link";
import { Mail, MapPin, Phone } from "lucide-react";

import type { SiteContent } from "@/lib/site-content";

interface SiteFooterProps {
  content: SiteContent;
}

export function SiteFooter({ content }: SiteFooterProps) {
  const { meta, navigation, footer } = content;

  return (
    <footer className="border-t border-border/60 bg-card/40">
      <div className="container grid gap-10 py-12 md:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-3 lg:col-span-2">
          <p
            className="font-display text-lg font-semibold"
            data-cms="text"
            data-cms-key="meta.businessName"
            data-cms-label="Nom entreprise"
          >
            {meta.businessName}
          </p>
          <p
            className="max-w-md text-sm text-muted-foreground"
            data-cms="text"
            data-cms-key="footer.description"
            data-cms-label="Description footer"
          >
            {footer.description}
          </p>
        </div>

        <div>
          <p className="mb-3 text-sm font-semibold">Navigation</p>
          <ul className="space-y-2 text-sm text-muted-foreground">
            {navigation.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="hover:text-primary">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-3 text-sm text-muted-foreground">
          <p className="font-semibold text-foreground">Contact</p>
          {footer.phone ? (
            <p className="flex items-center gap-2">
              <Phone className="h-4 w-4 shrink-0 text-primary" />
              <a href={`tel:${footer.phone.replace(/\s/g, "")}`} className="hover:text-primary">
                <span data-cms="text" data-cms-key="footer.phone" data-cms-label="Téléphone">
                  {footer.phone}
                </span>
              </a>
            </p>
          ) : null}
          {footer.email ? (
            <p className="flex items-center gap-2">
              <Mail className="h-4 w-4 shrink-0 text-primary" />
              <a href={`mailto:${footer.email}`} className="hover:text-primary">
                <span data-cms="text" data-cms-key="footer.email" data-cms-label="Email">
                  {footer.email}
                </span>
              </a>
            </p>
          ) : null}
          {footer.address ? (
            <p className="flex items-start gap-2">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
              <span data-cms="text" data-cms-key="footer.address" data-cms-label="Adresse">
                {footer.address}
              </span>
            </p>
          ) : null}
        </div>
      </div>

      <div className="border-t border-border/60">
        <div className="container flex flex-col gap-3 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <p data-cms="text" data-cms-key="footer.legalNote" data-cms-label="Mention légale">
            {footer.legalNote}
          </p>
          {footer.socialLinks?.length ? (
            <div className="flex flex-wrap gap-4">
              {footer.socialLinks.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-primary"
                >
                  {link.label}
                </a>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </footer>
  );
}
