import { useEffect, useState } from "react"
import {
  fetchFormats,
  generatePost,
  generateHashtags,
  generateBio,
  type FormatInfo,
  type PostResult,
  type HashtagsResult,
  type BioResult,
} from "@/lib/content-api"

type Onglet = "posts" | "hashtags" | "bio"

const RESEAU_ICONS: Record<string, string> = {
  linkedin: "ti ti-brand-linkedin",
  instagram: "ti ti-brand-instagram",
  tiktok: "ti ti-brand-tiktok",
  twitter: "ti ti-brand-x",
}

const RESEAU_COLORS: Record<string, string> = {
  linkedin: "text-blue-400 border-blue-400/30 bg-blue-400/10",
  instagram: "text-pink-400 border-pink-400/30 bg-pink-400/10",
  tiktok: "text-cyan-400 border-cyan-400/30 bg-cyan-400/10",
  twitter: "text-gray-300 border-gray-400/30 bg-gray-400/10",
}

function CopyButton({ texte }: { texte: string }) {
  const [copie, setCopie] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(texte)
        setCopie(true)
        setTimeout(() => setCopie(false), 2000)
      }}
      className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-gray-400 hover:text-white transition-colors"
    >
      {copie ? "✓ Copié" : "Copier"}
    </button>
  )
}

export function StudioCapcorePage() {
  const [onglet, setOnglet] = useState<Onglet>("posts")
  const [formats, setFormats] = useState<FormatInfo[]>([])
  const [secteurs, setSecteurs] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  // Champs communs
  const [sujet, setSujet] = useState("")
  const [secteur, setSecteur] = useState("")
  const [reseau, setReseau] = useState("linkedin")

  // Champs Posts
  const [tonPerso, setTonPerso] = useState("")
  const [nomEntreprise, setNomEntreprise] = useState("")
  const [postResult, setPostResult] = useState<PostResult | null>(null)

  // Champs Hashtags
  const [nbHashtags, setNbHashtags] = useState(10)
  const [hashtagsResult, setHashtagsResult] = useState<HashtagsResult | null>(null)

  // Champs Bio
  const [valeurAjoutee, setValeurAjoutee] = useState("")
  const [bioResult, setBioResult] = useState<BioResult | null>(null)

  useEffect(() => {
    fetchFormats().then(data => {
      setFormats(data.formats || [])
      setSecteurs(data.secteurs || [])
    })
  }, [])

  async function handleGenererPost() {
    if (!sujet || !secteur) return
    setLoading(true)
    setPostResult(null)
    try {
      const res = await generatePost({
        sujet, secteur, format_reseau: reseau,
        ton_personnalise: tonPerso,
        nom_entreprise: nomEntreprise,
      })
      setPostResult(res)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenererHashtags() {
    if (!sujet || !secteur) return
    setLoading(true)
    setHashtagsResult(null)
    try {
      const res = await generateHashtags({ sujet, secteur, format_reseau: reseau, nb_hashtags: nbHashtags })
      setHashtagsResult(res)
    } finally {
      setLoading(false)
    }
  }

  async function handleGenererBio() {
    if (!nomEntreprise || !secteur || !valeurAjoutee) return
    setLoading(true)
    setBioResult(null)
    try {
      const res = await generateBio({ nom_entreprise: nomEntreprise, secteur, valeur_ajoutee: valeurAjoutee, format_reseau: reseau })
      setBioResult(res)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {/* En-tête */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <span className="text-amber-400">✦</span> Studio CapCore
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          Génération de contenu marketing — posts, hashtags, bios
        </p>
      </div>

      {/* Onglets */}
      <div className="flex gap-1 bg-white/5 p-1 rounded-xl w-fit">
        {(["posts", "hashtags", "bio"] as Onglet[]).map(o => (
          <button
            key={o}
            type="button"
            onClick={() => setOnglet(o)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
              onglet === o
                ? "bg-amber-400 text-black"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {o === "posts" ? "Posts" : o === "hashtags" ? "Hashtags" : "Bio profil"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ── Colonne gauche — Formulaire ── */}
        <div className="space-y-4">

          {/* Sélecteur réseau */}
          <div>
            <label className="text-xs text-gray-500 mb-2 block uppercase tracking-wider">Réseau social</label>
            <div className="flex gap-2 flex-wrap">
              {formats.map(f => (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setReseau(f.id)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                    reseau === f.id
                      ? RESEAU_COLORS[f.id]
                      : "text-gray-500 border-white/10 bg-white/5 hover:bg-white/10"
                  }`}
                >
                  <i className={RESEAU_ICONS[f.id]} />
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Secteur */}
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Secteur d'activité</label>
            <select
              value={secteur}
              onChange={e => setSecteur(e.target.value)}
              className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-amber-400/50"
            >
              <option value="">Choisir un secteur...</option>
              {secteurs.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Champs spécifiques par onglet */}
          {(onglet === "posts" || onglet === "hashtags") && (
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Sujet du post</label>
              <textarea
                value={sujet}
                onChange={e => setSujet(e.target.value)}
                placeholder="Ex : lancement de notre nouvelle collection printemps..."
                rows={3}
                className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50 resize-none"
              />
            </div>
          )}

          {onglet === "posts" && (
            <>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">
                  Nom de l'entreprise <span className="text-gray-600">(optionnel)</span>
                </label>
                <input
                  type="text"
                  value={nomEntreprise}
                  onChange={e => setNomEntreprise(e.target.value)}
                  placeholder="Ex : Boulangerie Martin"
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">
                  Ton personnalisé <span className="text-gray-600">(optionnel)</span>
                </label>
                <input
                  type="text"
                  value={tonPerso}
                  onChange={e => setTonPerso(e.target.value)}
                  placeholder="Ex : chaleureux et familial"
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50"
                />
              </div>
            </>
          )}

          {onglet === "hashtags" && (
            <div>
              <label className="text-xs text-gray-500 mb-1 block">
                Nombre de hashtags : <span className="text-white">{nbHashtags}</span>
              </label>
              <input
                type="range"
                min={5}
                max={20}
                value={nbHashtags}
                onChange={e => setNbHashtags(Number(e.target.value))}
                className="w-full accent-amber-400"
              />
            </div>
          )}

          {onglet === "bio" && (
            <>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Nom de l'entreprise</label>
                <input
                  type="text"
                  value={nomEntreprise}
                  onChange={e => setNomEntreprise(e.target.value)}
                  placeholder="Ex : Atelier Dupont"
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Valeur ajoutée / promesse</label>
                <input
                  type="text"
                  value={valeurAjoutee}
                  onChange={e => setValeurAjoutee(e.target.value)}
                  placeholder="Ex : meubles sur-mesure fabriqués à la main en 3 semaines"
                  className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-amber-400/50"
                />
              </div>
            </>
          )}

          {/* Bouton générer */}
          <button
            type="button"
            onClick={
              onglet === "posts" ? handleGenererPost :
              onglet === "hashtags" ? handleGenererHashtags :
              handleGenererBio
            }
            disabled={loading}
            className="w-full py-3 bg-amber-400 hover:bg-amber-300 disabled:opacity-50 disabled:cursor-not-allowed text-black font-bold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <i className="ti ti-loader animate-spin" />
                Génération en cours...
              </>
            ) : (
              <>
                <i className="ti ti-sparkles" />
                Générer avec ContentAI
              </>
            )}
          </button>
        </div>

        {/* ── Colonne droite — Résultats ── */}
        <div className="space-y-4">

          {/* Résultat Post */}
          {onglet === "posts" && postResult?.success && (
            <div className="space-y-3">
              {/* Accroche */}
              <div className="bg-amber-400/5 border border-amber-400/20 rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-amber-400 font-medium uppercase tracking-wider">Accroche</span>
                </div>
                <p className="text-white text-sm">{postResult.accroche}</p>
              </div>

              {/* Post complet */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <i className={`${RESEAU_ICONS[postResult.format]} text-sm`} />
                    <span className="text-xs text-gray-400 font-medium">{postResult.label}</span>
                  </div>
                  <CopyButton texte={postResult.post} />
                </div>
                <p className="text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
                  {postResult.post}
                </p>
              </div>

              {/* Conseil */}
              {postResult.conseil && (
                <div className="bg-blue-400/5 border border-blue-400/20 rounded-xl p-3">
                  <span className="text-xs text-blue-400">💡 {postResult.conseil}</span>
                </div>
              )}
            </div>
          )}

          {/* Résultat Hashtags */}
          {onglet === "hashtags" && hashtagsResult?.success && (
            <div className="space-y-3">
              <div className="bg-white/5 border border-white/10 rounded-xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">
                    {hashtagsResult.hashtags.length} hashtags générés
                  </span>
                  <CopyButton texte={hashtagsResult.hashtags.join(" ")} />
                </div>
                <div className="flex flex-wrap gap-2">
                  {hashtagsResult.hashtags.map((h, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => navigator.clipboard.writeText(h)}
                      className="px-2 py-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm text-blue-300 transition-colors"
                      title="Cliquer pour copier"
                    >
                      {h}
                    </button>
                  ))}
                </div>
              </div>
              {hashtagsResult.conseil && (
                <div className="bg-blue-400/5 border border-blue-400/20 rounded-xl p-3">
                  <span className="text-xs text-blue-400">💡 {hashtagsResult.conseil}</span>
                </div>
              )}
            </div>
          )}

          {/* Résultat Bio */}
          {onglet === "bio" && bioResult?.success && (
            <div className="space-y-3">
              <div className="text-xs text-gray-500 flex items-center gap-2">
                <i className={RESEAU_ICONS[bioResult.format]} />
                Limite : {bioResult.limite}
              </div>
              {bioResult.bios.map((bio, i) => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-amber-400 font-medium">{bio.version}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-500">{bio.texte.length} car.</span>
                      <CopyButton texte={bio.texte} />
                    </div>
                  </div>
                  <p className="text-gray-200 text-sm leading-relaxed">{bio.texte}</p>
                </div>
              ))}
            </div>
          )}

          {/* État vide */}
          {((onglet === "posts" && !postResult) ||
            (onglet === "hashtags" && !hashtagsResult) ||
            (onglet === "bio" && !bioResult)) && !loading && (
            <div className="flex flex-col items-center justify-center h-48 text-center border border-dashed border-white/10 rounded-xl">
              <i className="ti ti-sparkles text-3xl text-gray-600 mb-2" />
              <p className="text-gray-500 text-sm">
                Remplis le formulaire et clique sur<br />
                <span className="text-amber-400">Générer avec ContentAI</span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
