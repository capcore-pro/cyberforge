import siteJson from "@/content/site.json";

export interface UnsplashImage {
  url: string;
  alt: string;
  photographer?: string;
  photographerUrl?: string;
}

export interface NavItem {
  label: string;
  href: string;
}

export interface ServiceCard {
  title: string;
  description: string;
  href: string;
  image: UnsplashImage;
}

export interface Testimonial {
  quote: string;
  author: string;
  role: string;
  rating: number;
}

export interface ServiceSection {
  id: string;
  title: string;
  description: string;
  bullets?: string[];
  image: UnsplashImage;
}

export interface SiteContent {
  meta: {
    businessName: string;
    tagline: string;
    locale: string;
    primaryColor: string;
    logoUrl?: string | null;
  };
  navigation: NavItem[];
  home: {
    hero: {
      title: string;
      subtitle: string;
      ctaPrimary: { label: string; href: string };
      ctaSecondary?: { label: string; href: string };
      image: UnsplashImage;
    };
    servicesPreview: ServiceCard[];
    testimonials: Testimonial[];
    ctaBand: {
      title: string;
      text: string;
      buttonLabel: string;
      buttonHref: string;
    };
  };
  servicesPage: {
    intro: { title: string; description: string };
    sections: ServiceSection[];
  };
  contactPage: {
    headline: string;
    subtext: string;
    fields: {
      name: string;
      email: string;
      message: string;
      submit: string;
    };
    successMessage: string;
    sidebar: {
      phone: string;
      email: string;
      hours: string;
      address: string;
    };
  };
  footer: {
    description: string;
    phone?: string;
    email?: string;
    address?: string;
    socialLinks?: { label: string; href: string }[];
    legalNote: string;
  };
}

export function getSiteContent(): SiteContent {
  return siteJson as SiteContent;
}
