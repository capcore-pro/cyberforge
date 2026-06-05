import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiErrorMessage } from "@/lib/api-errors";
import {
  createClient,
  type ClientRecord,
} from "@/lib/clients-api";

const AVATAR_PALETTE = [
  "bg-amber-500/15 text-amber-200 border-amber-400/25",
  "bg-blue-500/15 text-blue-200 border-blue-400/25",
  "bg-emerald-500/15 text-emerald-200 border-emerald-400/25",
  "bg-violet-500/15 text-violet-200 border-violet-400/25",
  "bg-cyan-500/15 text-cyan-200 border-cyan-400/25",
  "bg-orange-500/15 text-orange-200 border-orange-400/25",
] as const;

function clientInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  }
  return (parts[0]?.slice(0, 2) ?? "?").toUpperCase();
}

function avatarClasses(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash + seed.charCodeAt(i)) % AVATAR_PALETTE.length;
  }
  return AVATAR_PALETTE[hash] ?? AVATAR_PALETTE[0];
}

function clientSubtitle(client: ClientRecord): string {
  if (client.company?.trim()) return client.company.trim();
  return client.kind === "perso" ? "Projet perso" : "Client commercial";
}

interface ClientPickerDropdownProps {
  clients: ClientRecord[];
  loading: boolean;
  value: string | null;
  disabled?: boolean;
  onOpen: () => void;
  onSelect: (clientId: string) => void;
  onClientCreated: (client: ClientRecord) => void;
}

export function ClientPickerDropdown({
  clients,
  loading,
  value,
  disabled = false,
  onOpen,
  onSelect,
  onClientCreated,
}: ClientPickerDropdownProps) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");

  const selected = useMemo(
    () => clients.find((c) => c.id === value) ?? null,
    [clients, value],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return clients;
    return clients.filter((c) => {
      const hay = [c.name, c.company, c.email, c.phone]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [clients, search]);

  const close = useCallback(() => {
    setOpen(false);
    setCreateOpen(false);
    setSearch("");
    setCreateError(null);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) close();
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [close, open]);

  function openDropdown() {
    if (disabled) return;
    onOpen();
    setOpen(true);
  }

  function resetCreateForm() {
    setFirstName("");
    setLastName("");
    setEmail("");
    setPhone("");
    setCreateError(null);
  }

  async function handleCreate() {
    const name = `${firstName.trim()} ${lastName.trim()}`.trim();
    if (!name) {
      setCreateError("Prénom et nom requis.");
      return;
    }
    setCreating(true);
    setCreateError(null);
    const response = await createClient({
      kind: "client",
      name,
      email: email.trim() || null,
      phone: phone.trim() || null,
      active: true,
    });
    setCreating(false);
    if (!response.ok || !response.data) {
      setCreateError(apiErrorMessage(response, "Création impossible."));
      return;
    }
    onClientCreated(response.data);
    onSelect(response.data.id);
    resetCreateForm();
    setCreateOpen(false);
    close();
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => (open ? close() : openDropdown())}
        className={[
          "flex w-full items-center justify-between gap-3 rounded-control border border-white/10 bg-white/5 px-3 py-2.5 text-left backdrop-blur-xl transition-all duration-200",
          "hover:border-[#d4a843]/40 focus:outline-none focus-visible:ring-1 focus-visible:ring-[#d4a843]/50",
          disabled ? "cursor-not-allowed opacity-60" : "",
          open ? "border-[#d4a843]/50 shadow-[0_0_20px_rgba(212,168,67,0.1)]" : "",
        ].join(" ")}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        {selected ? (
          <span className="flex min-w-0 items-center gap-2.5">
            <span
              className={[
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                avatarClasses(selected.name),
              ].join(" ")}
            >
              {clientInitials(selected.name)}
            </span>
            <span className="min-w-0">
              <span className="block truncate text-sm font-medium text-cf-text">
                {selected.company?.trim() || selected.name}
              </span>
              <span className="block truncate text-[11px] text-cf-muted">
                {clientSubtitle(selected)}
              </span>
            </span>
          </span>
        ) : (
          <span className="text-sm text-cf-muted">Sélectionner un client…</span>
        )}
        <span className="shrink-0 text-cf-muted" aria-hidden>
          {open ? "▴" : "▾"}
        </span>
      </button>

      {open ? (
        <div className="absolute z-40 mt-2 w-full overflow-hidden rounded-card border border-white/10 bg-[#0f0f0f]/95 shadow-[0_16px_48px_rgba(0,0,0,0.45)] backdrop-blur-xl">
          <div className="border-b border-white/10 p-2">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher un client…"
              className="w-full rounded-control border border-white/10 bg-white/5 px-3 py-2 text-sm text-cf-text placeholder:text-cf-muted focus:border-[#d4a843]/40 focus:outline-none"
              autoFocus
            />
          </div>

          <ul
            className="max-h-52 overflow-y-auto p-1"
            role="listbox"
            aria-label="Clients"
          >
            {loading ? (
              <li className="px-3 py-2 text-xs text-cf-muted">Chargement…</li>
            ) : filtered.length === 0 ? (
              <li className="px-3 py-2 text-xs text-cf-muted">Aucun client trouvé.</li>
            ) : (
              filtered.map((client) => {
                const active = client.id === value;
                return (
                  <li key={client.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={active}
                      onClick={() => {
                        onSelect(client.id);
                        close();
                      }}
                      className={[
                        "flex w-full items-center gap-2.5 rounded-control px-2.5 py-2 text-left transition-all duration-200",
                        active
                          ? "border border-[#d4a843]/40 bg-[#d4a843]/10"
                          : "border border-transparent hover:bg-white/5",
                      ].join(" ")}
                    >
                      <span
                        className={[
                          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold",
                          avatarClasses(client.name),
                        ].join(" ")}
                      >
                        {clientInitials(client.name)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-cf-text">
                          {client.company?.trim() || client.name}
                        </span>
                        <span className="block truncate text-[11px] text-cf-muted">
                          {clientSubtitle(client)}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })
            )}
          </ul>

          <div className="border-t border-white/10 p-2">
            {!createOpen ? (
              <button
                type="button"
                onClick={() => {
                  resetCreateForm();
                  setCreateOpen(true);
                }}
                className="w-full rounded-control border border-dashed border-[#d4a843]/35 bg-[#d4a843]/5 px-3 py-2 text-sm font-medium text-[#d4a843] transition-all duration-200 hover:border-[#d4a843]/60 hover:bg-[#d4a843]/10"
              >
                + Créer un nouveau client
              </button>
            ) : (
              <div className="space-y-2 rounded-control border border-white/10 bg-white/5 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-cf-muted">
                  Nouveau client
                </p>
                <div className="grid gap-2 sm:grid-cols-2">
                  <input
                    type="text"
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="Prénom"
                    className="rounded-control border border-white/10 bg-[#0a0a0a] px-2.5 py-2 text-sm text-cf-text focus:border-[#d4a843]/40 focus:outline-none"
                  />
                  <input
                    type="text"
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Nom"
                    className="rounded-control border border-white/10 bg-[#0a0a0a] px-2.5 py-2 text-sm text-cf-text focus:border-[#d4a843]/40 focus:outline-none"
                  />
                </div>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email"
                  className="w-full rounded-control border border-white/10 bg-[#0a0a0a] px-2.5 py-2 text-sm text-cf-text focus:border-[#d4a843]/40 focus:outline-none"
                />
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="Téléphone (optionnel)"
                  className="w-full rounded-control border border-white/10 bg-[#0a0a0a] px-2.5 py-2 text-sm text-cf-text focus:border-[#d4a843]/40 focus:outline-none"
                />
                {createError ? (
                  <p className="text-xs text-red-300">{createError}</p>
                ) : null}
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={creating}
                    onClick={() => void handleCreate()}
                    className="flex-1 rounded-control border border-[#d4a843]/50 bg-[#d4a843]/15 px-3 py-2 text-sm font-medium text-[#d4a843] transition-all duration-200 hover:bg-[#d4a843]/25 disabled:opacity-60"
                  >
                    {creating ? "Création…" : "Créer"}
                  </button>
                  <button
                    type="button"
                    disabled={creating}
                    onClick={() => {
                      setCreateOpen(false);
                      setCreateError(null);
                    }}
                    className="rounded-control border border-white/10 px-3 py-2 text-sm text-cf-muted hover:text-cf-text"
                  >
                    Annuler
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
