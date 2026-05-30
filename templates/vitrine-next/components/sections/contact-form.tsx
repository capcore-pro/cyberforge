"use client";

import { useState } from "react";
import { Loader2, Mail, MapPin, Phone } from "lucide-react";

import type { SiteContent } from "@/lib/site-content";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ContactForm({ content }: { content: SiteContent }) {
  const { contactPage: page } = content;
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    "idle",
  );
  const [errorMsg, setErrorMsg] = useState("");

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("loading");
    setErrorMsg("");

    const form = event.currentTarget;
    const data = new FormData(form);
    const payload = {
      name: String(data.get("name") ?? "").trim(),
      email: String(data.get("email") ?? "").trim(),
      message: String(data.get("message") ?? "").trim(),
    };

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Envoi impossible. Réessayez plus tard.",
        );
      }
      setStatus("success");
      form.reset();
    } catch (err) {
      setStatus("error");
      setErrorMsg(err instanceof Error ? err.message : "Erreur réseau.");
    }
  }

  return (
    <div className="grid gap-10 lg:grid-cols-5">
      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle
            className="font-display text-2xl"
            data-cms="text"
            data-cms-key="contactPage.headline"
            data-cms-label="Titre contact"
          >
            {page.headline}
          </CardTitle>
          <p
            className="text-sm text-muted-foreground"
            data-cms="text"
            data-cms-key="contactPage.subtext"
            data-cms-label="Sous-titre contact"
          >
            {page.subtext}
          </p>
        </CardHeader>
        <CardContent>
          {status === "success" ? (
            <p
              className="rounded-lg border border-primary/30 bg-primary/10 px-4 py-3 text-sm text-primary"
              role="status"
            >
              {page.successMessage}
            </p>
          ) : (
            <form onSubmit={onSubmit} className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="name">{page.fields.name}</Label>
                <Input
                  id="name"
                  name="name"
                  required
                  autoComplete="name"
                  disabled={status === "loading"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">{page.fields.email}</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  disabled={status === "loading"}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="message">{page.fields.message}</Label>
                <Textarea
                  id="message"
                  name="message"
                  required
                  rows={5}
                  disabled={status === "loading"}
                />
              </div>
              {status === "error" ? (
                <p className="text-sm text-destructive" role="alert">
                  {errorMsg}
                </p>
              ) : null}
              <Button type="submit" className="w-full sm:w-auto" disabled={status === "loading"}>
                {status === "loading" ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Envoi…
                  </>
                ) : (
                  page.fields.submit
                )}
              </Button>
            </form>
          )}
        </CardContent>
      </Card>

      <aside className="space-y-4 lg:col-span-2">
        <Card>
          <CardContent className="space-y-5 p-6 text-sm">
            <p className="flex items-center gap-3">
              <Phone className="h-5 w-5 shrink-0 text-primary" />
              <a
                href={`tel:${page.sidebar.phone.replace(/\s/g, "")}`}
                className="hover:text-primary"
              >
                {page.sidebar.phone}
              </a>
            </p>
            <p className="flex items-center gap-3">
              <Mail className="h-5 w-5 shrink-0 text-primary" />
              <a href={`mailto:${page.sidebar.email}`} className="hover:text-primary">
                {page.sidebar.email}
              </a>
            </p>
            <p className="flex items-start gap-3 text-muted-foreground">
              <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
              <span>{page.sidebar.address}</span>
            </p>
            <p className="rounded-md bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              {page.sidebar.hours}
            </p>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}
