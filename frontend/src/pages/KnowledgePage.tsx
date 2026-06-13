import { useCallback, useEffect, useMemo, useState } from "react";
import { KnowledgeGraphView } from "@/components/knowledge/KnowledgeGraphView";
import { GLASS_SECTION } from "@/components/accounting/accounting-theme";
import { TAB_ACTIVE, TAB_BASE } from "@/components/settings/settings-theme";
import { Badge, Button, Card, Input } from "@/components/ui";
import { formatRelativeDate } from "@/lib/client-page-utils";
import {
  chunkScoreValue,
  deleteDocument,
  fetchDocuments,
  ingestFile,
  ingestText,
  isKnowledgeFileAllowed,
  KNOWLEDGE_ALLOWED_EXTENSIONS,
  scoreBadgeVariant,
  searchKnowledgeSafe,
  sourceTypeBadgeVariant,
  titleFromFilename,
  truncateChunkContent,
  type KnowledgeChunk,
  type KnowledgeDocument,
} from "@/lib/knowledge-api";

type KnowledgeTab = "documents" | "add" | "search" | "graph";
type AddSubTab = "text" | "file";

const MAIN_TABS: { id: KnowledgeTab; label: string }[] = [
  { id: "documents", label: "Documents" },
  { id: "add", label: "Ajouter" },
  { id: "search", label: "Rechercher" },
  { id: "graph", label: "Graphe" },
];

const ADD_TABS: { id: AddSubTab; label: string }[] = [
  { id: "text", label: "Texte" },
  { id: "file", label: "Fichier" },
];

const TEXTAREA_CLASS =
  "w-full rounded-[var(--cf-radius-control)] border border-white/10 bg-white/[0.03] px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:border-[#d4a843] focus:outline-none transition-colors";

export function KnowledgePage() {
  const [tab, setTab] = useState<KnowledgeTab>("documents");
  const [addTab, setAddTab] = useState<AddSubTab>("text");

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const [textTitle, setTextTitle] = useState("");
  const [textContent, setTextContent] = useState("");
  const [textBusy, setTextBusy] = useState(false);
  const [textFeedback, setTextFeedback] = useState<string | null>(null);
  const [textError, setTextError] = useState<string | null>(null);

  const [fileTitle, setFileTitle] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileDrag, setFileDrag] = useState(false);
  const [fileBusy, setFileBusy] = useState(false);
  const [fileProgress, setFileProgress] = useState(0);
  const [fileFeedback, setFileFeedback] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<KnowledgeChunk[]>([]);
  const [searchBusy, setSearchBusy] = useState(false);
  const [searchRan, setSearchRan] = useState(false);

  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    setDocsError(null);
    try {
      const rows = await fetchDocuments();
      setDocuments(rows);
    } catch (err) {
      setDocsError(
        err instanceof Error ? err.message : "Chargement impossible.",
      );
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const docCountLabel = useMemo(() => {
    const n = documents.length;
    return `${n} document${n > 1 ? "s" : ""} indexé${n > 1 ? "s" : ""}`;
  }, [documents.length]);

  function openAddTab(sub: AddSubTab = "text") {
    setTab("add");
    setAddTab(sub);
  }

  function applySelectedFile(file: File | null) {
    if (!file) return;
    if (!isKnowledgeFileAllowed(file)) {
      setFileError("Formats acceptés : .txt, .md, .pdf");
      setSelectedFile(null);
      return;
    }
    setFileError(null);
    setSelectedFile(file);
    if (!fileTitle.trim()) {
      setFileTitle(titleFromFilename(file.name));
    }
  }

  async function handleIngestText() {
    const title = textTitle.trim();
    const content = textContent.trim();
    if (!title) {
      setTextError("Titre requis.");
      return;
    }
    if (content.length < 100) {
      setTextError("Le contenu doit contenir au moins 100 caractères.");
      return;
    }
    setTextBusy(true);
    setTextError(null);
    setTextFeedback(null);
    try {
      const result = await ingestText(title, content);
      setTextFeedback(
        `✓ Indexé — ${result.chunks_count} chunk${result.chunks_count > 1 ? "s" : ""} créé${result.chunks_count > 1 ? "s" : ""}`,
      );
      setTextTitle("");
      setTextContent("");
      void loadDocuments();
    } catch (err) {
      setTextError(
        err instanceof Error ? err.message : "Indexation impossible.",
      );
    } finally {
      setTextBusy(false);
    }
  }

  async function handleIngestFile() {
    if (!selectedFile) {
      setFileError("Sélectionnez un fichier.");
      return;
    }
    const title = fileTitle.trim() || titleFromFilename(selectedFile.name);
    setFileBusy(true);
    setFileError(null);
    setFileFeedback(null);
    setFileProgress(0);
    try {
      const result = await ingestFile(
        selectedFile,
        title,
        undefined,
        setFileProgress,
      );
      setFileFeedback(`✓ ${result.chunks_count} chunks indexés`);
      setSelectedFile(null);
      setFileTitle("");
      setFileProgress(0);
      void loadDocuments();
    } catch (err) {
      setFileError(err instanceof Error ? err.message : "Upload impossible.");
      setFileProgress(0);
    } finally {
      setFileBusy(false);
    }
  }

  async function handleDeleteDocument(doc: KnowledgeDocument) {
    if (!window.confirm(`Supprimer « ${doc.title} » et ses chunks ?`)) return;
    setDeletingId(doc.id);
    setDocsError(null);
    try {
      await deleteDocument(doc.id);
      setDocuments((prev) => prev.filter((item) => item.id !== doc.id));
    } catch (err) {
      setDocsError(
        err instanceof Error ? err.message : "Suppression impossible.",
      );
    } finally {
      setDeletingId(null);
    }
  }

  async function handleSearch() {
    const query = searchQuery.trim();
    if (!query) return;
    setSearchBusy(true);
    setSearchRan(true);
    const res = await searchKnowledgeSafe(query);
    setSearchBusy(false);
    if (!res.ok) {
      setSearchResults([]);
      return;
    }
    setSearchResults(res.data ?? []);
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#d4a843]/80">
            <i className="ti ti-brain text-base" aria-hidden />
            RAG & contexte IA
          </p>
          <h1 className="flex items-center gap-2 text-2xl font-semibold text-white">
            <i className="ti ti-brain text-[#d4a843]" aria-hidden />
            Base de connaissance
          </h1>
          <p className="mt-2 text-sm text-white/50">
            Indexez vos documents et interrogez la base pour enrichir les prompts.
          </p>
        </div>
        {tab === "documents" ? (
          <Badge variant="gold" size="md">
            {docCountLabel}
          </Badge>
        ) : null}
      </header>

      <nav className="flex flex-wrap gap-1">
        {MAIN_TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setTab(item.id)}
            className={`${TAB_BASE} rounded-control ${tab === item.id ? TAB_ACTIVE : ""}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {tab === "documents" ? (
        <section className="space-y-4">
          {docsError ? (
            <p className="rounded-lg border border-red-500/30 bg-red-950/20 px-4 py-3 text-sm text-red-300">
              {docsError}
            </p>
          ) : null}

          {loadingDocs ? (
            <p className="animate-pulse py-12 text-center text-sm text-white/50">
              Chargement des documents…
            </p>
          ) : documents.length === 0 ? (
            <div
              className={`${GLASS_SECTION} flex min-h-[280px] flex-col items-center justify-center gap-4 text-center`}
            >
              <i
                className="ti ti-brain text-4xl text-white/20"
                aria-hidden
              />
              <p className="text-sm text-white/50">
                Aucun document indexé pour l&apos;instant.
              </p>
              <Button variant="primary" onClick={() => openAddTab("text")}>
                Ajouter →
              </Button>
            </div>
          ) : (
            <ul className="space-y-3">
              {documents.map((doc) => (
                <li key={doc.id}>
                  <Card
                    className="border-white/10 bg-white/[0.03] backdrop-blur-xl"
                    actions={
                      <Button
                        variant="danger"
                        size="sm"
                        loading={deletingId === doc.id}
                        onClick={() => void handleDeleteDocument(doc)}
                      >
                        Supprimer
                      </Button>
                    }
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-sm font-medium text-white">
                        {doc.title}
                      </h3>
                      <Badge variant={sourceTypeBadgeVariant(doc.source_type)}>
                        {doc.source_type}
                      </Badge>
                    </div>
                    <p className="mt-2 text-xs text-white/40">
                      {formatRelativeDate(doc.created_at)}
                      {doc.status ? ` · ${doc.status}` : ""}
                    </p>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}

      {tab === "add" ? (
        <section className="space-y-6">
          <nav className="flex flex-wrap gap-1">
            {ADD_TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setAddTab(item.id)}
                className={`${TAB_BASE} rounded-control ${addTab === item.id ? TAB_ACTIVE : ""}`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {addTab === "text" ? (
            <div className={`${GLASS_SECTION} space-y-4`}>
              <Input
                label="Titre"
                value={textTitle}
                onChange={setTextTitle}
                placeholder="Ex : Charte éditoriale CapCore"
              />
              <label className="block space-y-1">
                <span className="text-xs uppercase tracking-widest text-white/50">
                  Contenu
                </span>
                <textarea
                  value={textContent}
                  onChange={(e) => setTextContent(e.target.value)}
                  rows={10}
                  placeholder="Collez le texte à indexer (minimum 100 caractères)…"
                  className={TEXTAREA_CLASS}
                />
              </label>
              {textError ? (
                <p className="text-sm text-red-300">{textError}</p>
              ) : null}
              {textFeedback ? (
                <p className="text-sm text-teal-400">{textFeedback}</p>
              ) : null}
              <Button
                variant="primary"
                loading={textBusy}
                onClick={() => void handleIngestText()}
              >
                Indexer
              </Button>
            </div>
          ) : null}

          {addTab === "file" ? (
            <div className={`${GLASS_SECTION} space-y-4`}>
              <div
                className={`flex min-h-[180px] flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 transition ${
                  fileDrag
                    ? "border-[#d4a843] bg-[#d4a843]/10"
                    : "border-white/10 bg-white/[0.03]"
                }`}
                onDragOver={(e) => {
                  e.preventDefault();
                  setFileDrag(true);
                }}
                onDragLeave={() => setFileDrag(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setFileDrag(false);
                  const file = e.dataTransfer.files?.[0] ?? null;
                  applySelectedFile(file);
                }}
              >
                <i
                  className="ti ti-upload mb-2 text-2xl text-white/30"
                  aria-hidden
                />
                <p className="text-sm text-white/50">
                  Glissez un fichier ici (.txt, .md, .pdf — max 20 Mo)
                </p>
                {selectedFile ? (
                  <p className="mt-2 text-xs text-[#d4a843]">
                    {selectedFile.name} (
                    {Math.round(selectedFile.size / 1024)} Ko)
                  </p>
                ) : null}
                <label className="mt-3 cursor-pointer">
                  <span className="rounded-control border border-white/15 bg-white/5 px-4 py-2 text-xs text-white/70 transition hover:border-white/30 hover:text-white">
                    Parcourir…
                  </span>
                  <input
                    type="file"
                    className="sr-only"
                    accept={KNOWLEDGE_ALLOWED_EXTENSIONS.join(",")}
                    disabled={fileBusy}
                    onChange={(e) => {
                      const file = e.target.files?.[0] ?? null;
                      applySelectedFile(file);
                      e.target.value = "";
                    }}
                  />
                </label>
              </div>

              <Input
                label="Titre"
                value={fileTitle}
                onChange={setFileTitle}
                placeholder="Auto-rempli depuis le nom du fichier"
              />

              {fileProgress > 0 && fileBusy ? (
                <div className="space-y-1">
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-[#d4a843] transition-all duration-200"
                      style={{ width: `${fileProgress}%` }}
                    />
                  </div>
                  <p className="text-xs text-white/40">{fileProgress}%</p>
                </div>
              ) : null}

              {fileError ? (
                <p className="text-sm text-red-300">{fileError}</p>
              ) : null}
              {fileFeedback ? (
                <p className="text-sm text-teal-400">{fileFeedback}</p>
              ) : null}

              <Button
                variant="primary"
                loading={fileBusy}
                onClick={() => void handleIngestFile()}
              >
                Uploader et indexer
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}

      {tab === "search" ? (
        <section className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[240px] flex-1">
              <Input
                label="Recherche"
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder="Rechercher dans la base…"
                icon="ti ti-search"
              />
            </div>
            <Button
              variant="primary"
              loading={searchBusy}
              onClick={() => void handleSearch()}
            >
              Rechercher
            </Button>
          </div>

          {!searchRan ? (
            <p className="py-12 text-center text-sm text-white/40">
              Lancez une recherche pour explorer la base indexée.
            </p>
          ) : searchBusy ? (
            <p className="animate-pulse py-12 text-center text-sm text-white/50">
              Recherche en cours…
            </p>
          ) : searchResults.length === 0 ? (
            <p className="py-12 text-center text-sm text-white/40">
              Aucun résultat pour cette requête.
            </p>
          ) : (
            <ul className="space-y-3">
              {searchResults.map((chunk) => {
                const score = chunkScoreValue(chunk);
                return (
                  <li key={chunk.chunk_id || `${chunk.document_id}-${chunk.content.slice(0, 24)}`}>
                    <Card className="border-white/10 bg-white/[0.03] backdrop-blur-xl">
                      <p className="text-xs text-white/60">
                        {chunk.document_title || "Document"}
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-white/80">
                        {truncateChunkContent(chunk.content)}
                      </p>
                      {score != null ? (
                        <div className="mt-3">
                          <Badge variant={scoreBadgeVariant(score)}>
                            score {score.toFixed(2)}
                          </Badge>
                        </div>
                      ) : null}
                    </Card>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      ) : null}

      {tab === "graph" ? (
        <section>
          <KnowledgeGraphView />
        </section>
      ) : null}
    </div>
  );
}
