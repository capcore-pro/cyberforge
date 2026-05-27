import { CtaBandSection } from "@/components/sections/cta-band-section";
import { HeroSection } from "@/components/sections/hero-section";
import { ServicesPreviewSection } from "@/components/sections/services-preview-section";
import { TestimonialsSection } from "@/components/sections/testimonials-section";
import { getSiteContent } from "@/lib/site-content";

export default function HomePage() {
  const content = getSiteContent();

  return (
    <>
      <HeroSection content={content} />
      <ServicesPreviewSection content={content} />
      <TestimonialsSection content={content} />
      <CtaBandSection content={content} />
    </>
  );
}
