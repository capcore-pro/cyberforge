export interface ElementChanges {
  textContent?: string;
  innerHTML?: string;
  src?: string;
  alt?: string;
  style?: Record<string, string>;
  className?: string;
  hidden?: boolean;
}

export class HTMLEditor {
  private html: string;
  private history: string[] = [];

  constructor(html: string) {
    this.html = html;
    this.history.push(html);
  }

  getHTML(): string {
    return this.html;
  }

  undo(): string {
    if (this.history.length <= 1) {
      return this.html;
    }
    this.history.pop();
    this.html = this.history[this.history.length - 1] ?? this.html;
    return this.html;
  }

  private commit(next: string): string {
    this.html = next;
    this.history.push(next);
    if (this.history.length > 50) {
      this.history.shift();
    }
    return this.html;
  }

  private parse(): Document {
    return new DOMParser().parseFromString(this.html, "text/html");
  }

  private serialize(doc: Document): string {
    const serialized = new XMLSerializer().serializeToString(doc);
    if (serialized.includes("<!DOCTYPE") || serialized.includes("<html")) {
      return serialized;
    }
    return `<!DOCTYPE html>${serialized}`;
  }

  private findByXPath(doc: Document, xpath: string): Element | null {
    const parts = xpath.split(" > ").map((p) => p.trim()).filter(Boolean);
    let node: Element | null = doc.body;
    for (const part of parts) {
      if (!node) return null;
      const match = part.match(/^([a-z0-9-]+):nth-child\((\d+)\)$/i);
      if (!match) return null;
      const tag = match[1].toLowerCase();
      const index = Number(match[2]) - 1;
      const child: Element | null = node.children[index] ?? null;
      if (!child || child.tagName.toLowerCase() !== tag) {
        return null;
      }
      node = child;
    }
    return node;
  }

  updateElement(xpath: string, changes: ElementChanges): string {
    const doc = this.parse();
    const el = this.findByXPath(doc, xpath);
    if (!el) {
      return this.html;
    }
    if (changes.textContent !== undefined) {
      el.textContent = changes.textContent;
    }
    if (changes.innerHTML !== undefined) {
      el.innerHTML = changes.innerHTML;
    }
    if (changes.src !== undefined && el instanceof HTMLImageElement) {
      el.src = changes.src;
    }
    if (changes.alt !== undefined && el instanceof HTMLImageElement) {
      el.alt = changes.alt;
    }
    if (changes.className !== undefined) {
      el.className = changes.className;
    }
    if (changes.style) {
      const htmlEl = el as HTMLElement;
      for (const [key, value] of Object.entries(changes.style)) {
        htmlEl.style.setProperty(key, value);
      }
    }
    if (changes.hidden !== undefined) {
      (el as HTMLElement).style.display = changes.hidden ? "none" : "";
    }
    return this.commit(this.serialize(doc));
  }

  replaceImage(xpath: string, newSrc: string, alt?: string): string {
    return this.updateElement(xpath, { src: newSrc, alt });
  }

  moveSection(xpath: string, direction: "up" | "down"): string {
    const doc = this.parse();
    const el = this.findByXPath(doc, xpath);
    if (!el?.parentElement) {
      return this.html;
    }
    const parent = el.parentElement;
    const siblings = Array.from(parent.children);
    const idx = siblings.indexOf(el);
    const swapWith = direction === "up" ? idx - 1 : idx + 1;
    if (swapWith < 0 || swapWith >= siblings.length) {
      return this.html;
    }
    const ref = direction === "up" ? siblings[swapWith] : siblings[swapWith].nextSibling;
    parent.insertBefore(el, ref);
    return this.commit(this.serialize(doc));
  }

  deleteSection(xpath: string): string {
    const doc = this.parse();
    const el = this.findByXPath(doc, xpath);
    el?.remove();
    return this.commit(this.serialize(doc));
  }

  duplicateSection(xpath: string): string {
    const doc = this.parse();
    const el = this.findByXPath(doc, xpath);
    if (!el?.parentElement) {
      return this.html;
    }
    const clone = el.cloneNode(true) as Element;
    el.parentElement.insertBefore(clone, el.nextSibling);
    return this.commit(this.serialize(doc));
  }

  updateGlobalColor(oldColor: string, newColor: string): string {
    const escaped = oldColor.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(escaped, "gi");
    return this.commit(this.html.replace(re, newColor));
  }

  extractSiteColors(): string[] {
    const found = new Set<string>();
    const hexRe = /#(?:[0-9a-f]{3,8})\b/gi;
    const varRe = /--color-[a-z-]+:\s*([^;]+)/gi;
    let m: RegExpExecArray | null;
    while ((m = hexRe.exec(this.html))) {
      found.add(m[0].toLowerCase());
    }
    while ((m = varRe.exec(this.html))) {
      const val = m[1].trim();
      if (val.startsWith("#")) {
        found.add(val.toLowerCase());
      }
    }
    return Array.from(found).slice(0, 12);
  }
}
