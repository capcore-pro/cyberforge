import type { Metadata } from "next";

import { ServicesDetailSection } from "@/components/sections/services-detail-section";
import { getSiteContent } from "@/lib/site-content";

const content = getSiteContent();

export const metadata: Metadata = {
  title: "Services",
  description: content.servicesPage.intro.description,
};

export default function ServicesPage() {
  return <ServicesDetailSection content={content} />;
}
