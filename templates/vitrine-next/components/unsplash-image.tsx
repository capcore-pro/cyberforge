import Image from "next/image";

import type { UnsplashImage } from "@/lib/site-content";
import { cn } from "@/lib/utils";

interface UnsplashImageProps {
  image: UnsplashImage;
  fill?: boolean;
  priority?: boolean;
  className?: string;
  sizes?: string;
  cmsKey?: string;
  cmsLabel?: string;
}

export function UnsplashImageBlock({
  image,
  fill = true,
  priority = false,
  className,
  sizes = "(max-width: 768px) 100vw, 50vw",
  cmsKey,
  cmsLabel,
}: UnsplashImageProps) {
  return (
    <figure
      className={cn("relative overflow-hidden", className)}
      {...(cmsKey
        ? {
            "data-cms": "image",
            "data-cms-key": cmsKey,
            "data-cms-label": cmsLabel,
          }
        : {})}
    >
      <Image
        src={image.url}
        alt={image.alt}
        fill={fill}
        priority={priority}
        sizes={sizes}
        className="object-cover"
      />
      {image.photographer ? (
        <figcaption className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent px-3 py-2 text-[10px] text-white/80">
          Photo{" "}
          {image.photographerUrl ? (
            <a
              href={image.photographerUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-white"
            >
              {image.photographer}
            </a>
          ) : (
            image.photographer
          )}{" "}
          / Unsplash
        </figcaption>
      ) : null}
    </figure>
  );
}
