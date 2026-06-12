import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { tokens } from "@/lib/tokens";
import {
  Badge,
  Button,
  Card,
  Dropdown,
  Input,
  Modal,
} from "@/components/ui";

const here = path.dirname(fileURLToPath(import.meta.url));

describe("design system tokens", () => {
  it("exports tokens with CSS variables", () => {
    expect(tokens.colors.gold).toBe("var(--cf-gold)");
    expect(tokens.radius.card).toBe("var(--cf-radius-card)");
  });

  it("aligns tailwind cf.main and cf.gold", () => {
    const configPath = path.resolve(here, "../../../tailwind.config.js");
    const source = readFileSync(configPath, "utf8");
    expect(source).toContain('main: "#0d0d0d"');
    expect(source).toContain('gold: "#c9a84c"');
    expect(source).toContain('"gold-legacy": "#d4a843"');
  });
});

describe("Button", () => {
  it("renders all variants", () => {
    for (const variant of ["primary", "ghost", "danger", "success"] as const) {
      const html = renderToStaticMarkup(
        <Button variant={variant}>Action</Button>,
      );
      expect(html).toContain("Action");
    }
  });

  it("renders loading spinner and disables button", () => {
    const html = renderToStaticMarkup(
      <Button loading>Chargement</Button>,
    );
    expect(html).toContain("animate-spin");
    expect(html).toContain("disabled");
  });
});

describe("Input", () => {
  it("renders label and hint", () => {
    const html = renderToStaticMarkup(
      <Input
        label="Email"
        hint="Format valide requis"
        value=""
        onChange={() => {}}
        placeholder="vous@exemple.com"
      />,
    );
    expect(html).toContain("Email");
    expect(html).toContain("Format valide requis");
  });

  it("renders error state", () => {
    const html = renderToStaticMarkup(
      <Input
        label="Email"
        error="Champ invalide"
        value=""
        onChange={() => {}}
      />,
    );
    expect(html).toContain("Champ invalide");
  });

  it("renders password toggle control", () => {
    const html = renderToStaticMarkup(
      <Input
        type="password"
        value="secret"
        onChange={() => {}}
      />,
    );
    expect(html).toContain("ti-eye");
  });
});

describe("Badge", () => {
  it("renders with dot", () => {
    const html = renderToStaticMarkup(
      <Badge variant="teal" dot pulse>
        Actif
      </Badge>,
    );
    expect(html).toContain("Actif");
    expect(html).toContain("animate-pulse");
  });
});

describe("Card", () => {
  it("renders titled card", () => {
    const html = renderToStaticMarkup(
      <Card title="Titre" subtitle="Sous-titre" icon="ti ti-box">
        Contenu
      </Card>,
    );
    expect(html).toContain("Titre");
    expect(html).toContain("Contenu");
  });
});

describe("Modal", () => {
  it("renders when open", () => {
    const html = renderToStaticMarkup(
      <Modal isOpen onClose={() => {}} title="Test modal">
        Corps
      </Modal>,
    );
    expect(html).toContain("Test modal");
    expect(html).toContain("Corps");
  });

  it("renders nothing when closed", () => {
    const html = renderToStaticMarkup(
      <Modal isOpen={false} onClose={() => {}} title="Fermé">
        Corps
      </Modal>,
    );
    expect(html).toBe("");
  });
});

describe("Dropdown", () => {
  it("renders trigger with placeholder", () => {
    const html = renderToStaticMarkup(
      <Dropdown
        options={[
          { value: "a", label: "Option A" },
          { value: "b", label: "Option B" },
        ]}
        value=""
        onChange={() => {}}
        placeholder="Choisir"
      />,
    );
    expect(html).toContain("Choisir");
    expect(html).toContain("ti-chevron-down");
  });
});
