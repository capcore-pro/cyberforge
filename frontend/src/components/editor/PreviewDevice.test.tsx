import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { PreviewDevice } from "@/components/editor/PreviewDevice";
import {
  PREVIEW_DEVICE_SPECS,
  computePreviewDeviceScale,
  previewDeviceFrameRadius,
} from "@/lib/preview-devices";

const SAMPLE_HTML = "<!DOCTYPE html><html><body><h1>Preview</h1></body></html>";

describe("preview device specs", () => {
  it("defines mobile dimensions", () => {
    expect(PREVIEW_DEVICE_SPECS.mobile.width).toBe(375);
    expect(PREVIEW_DEVICE_SPECS.mobile.height).toBe(812);
  });

  it("defines desktop dimensions", () => {
    expect(PREVIEW_DEVICE_SPECS.desktop.width).toBe(1280);
    expect(PREVIEW_DEVICE_SPECS.desktop.height).toBe(800);
  });

  it("computes scale to fit container", () => {
    const scale = computePreviewDeviceScale("mobile", 400, 900);
    expect(scale).toBeLessThanOrEqual(1);
    expect(scale).toBeGreaterThan(0);
  });
});

describe("PreviewDevice", () => {
  it("renders mobile frame with 375px width and 40px radius", () => {
    const html = renderToStaticMarkup(
      <PreviewDevice html={SAMPLE_HTML} device="mobile" />,
    );
    expect(html).toContain('data-device-width="375"');
    expect(html).toContain('data-frame-radius="40"');
    expect(html).toContain('data-testid="preview-device-notch"');
    expect(previewDeviceFrameRadius("mobile")).toBe(40);
  });

  it("renders desktop frame with title bar and 1280px width", () => {
    const html = renderToStaticMarkup(
      <PreviewDevice html={SAMPLE_HTML} device="desktop" />,
    );
    expect(html).toContain('data-device-width="1280"');
    expect(html).toContain('data-testid="preview-desktop-titlebar"');
    expect(html).toContain("bg-red-500");
    expect(html).toContain("bg-yellow-400");
    expect(html).toContain("bg-green-500");
  });
});
