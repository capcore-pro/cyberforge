import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ElementSelector } from "@/components/editor/ElementSelector";

const SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Edit</h1></body></html>";

describe("ElementSelector viewport", () => {
  it("uses 375px width for mobile", () => {
    const html = renderToStaticMarkup(
      <ElementSelector html={SAMPLE_HTML} viewport="mobile" />,
    );
    expect(html).toContain('data-viewport-width="375"');
    expect(html).toContain('data-viewport="mobile"');
  });

  it("uses 768px width for tablet", () => {
    const html = renderToStaticMarkup(
      <ElementSelector html={SAMPLE_HTML} viewport="tablet" />,
    );
    expect(html).toContain('data-viewport-width="768"');
  });

  it("uses full width for desktop", () => {
    const html = renderToStaticMarkup(
      <ElementSelector html={SAMPLE_HTML} viewport="desktop" />,
    );
    expect(html).toContain('data-viewport-width="1280"');
    expect(html).toContain('width:100%');
  });
});
