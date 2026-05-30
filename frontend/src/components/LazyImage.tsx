import { memo, useEffect, useRef, useState } from "react";

export interface LazyImageProps {
  src: string;
  alt: string;
  className?: string;
  onError?: () => void;
}

/**
 * Image chargée uniquement lorsqu'elle entre (ou approche) du viewport.
 */
export const LazyImage = memo(function LazyImage({
  src,
  alt,
  className = "",
  onError,
}: LazyImageProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = rootRef.current;
    if (!node) return;

    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { rootMargin: "240px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={rootRef} className={`h-full w-full ${className}`}>
      {visible ? (
        <img
          src={src}
          alt={alt}
          className="h-full w-full object-cover"
          loading="lazy"
          decoding="async"
          onError={onError}
        />
      ) : (
        <div className="h-full w-full animate-pulse bg-cyber-bg/60" aria-hidden />
      )}
    </div>
  );
});
