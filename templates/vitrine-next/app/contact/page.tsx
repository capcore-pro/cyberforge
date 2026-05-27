import type { Metadata } from "next";

import { ContactForm } from "@/components/sections/contact-form";
import { getSiteContent } from "@/lib/site-content";

const content = getSiteContent();

export const metadata: Metadata = {
  title: "Contact",
  description: content.contactPage.subtext,
};

export default function ContactPage() {
  return (
    <section className="container py-12 md:py-16">
      <ContactForm content={content} />
    </section>
  );
}
