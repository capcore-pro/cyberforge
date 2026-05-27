import type { Metadata } from "next";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";

import { SiteFooter } from "@/components/layout/site-footer";
import { SiteHeader } from "@/components/layout/site-header";
import { hexToHslChannels } from "@/lib/brand";
import { getSiteContent } from "@/lib/site-content";

import "./globals.css";

const fontSans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const fontDisplay = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const content = getSiteContent();

export const metadata: Metadata = {
  title: {
    default: content.meta.businessName,
    template: `%s · ${content.meta.businessName}`,
  },
  description: content.meta.tagline,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const primary = hexToHslChannels(content.meta.primaryColor);

  return (
    <html lang={content.meta.locale} className="dark">
      <body
        className={`${fontSans.variable} ${fontDisplay.variable} min-h-screen font-sans antialiased`}
        style={
          {
            "--primary": primary,
            "--ring": primary,
          } as React.CSSProperties
        }
      >
        <div className="flex min-h-screen flex-col">
          <SiteHeader content={content} />
          <main className="flex-1">{children}</main>
          <SiteFooter content={content} />
        </div>
      </body>
    </html>
  );
}
