import { useEffect, useState } from "react"
import {
  fetchFormats,
  fetchCapcoreSubjects,
  generatePost,
  generateHashtags,
  generateBio,
  generateCapcorePost,
  type FormatInfo,
  type PostResult,
  type HashtagsResult,
  type BioResult,
  type CapcoreSubject,
  type CapcorePostResult,
} from "@/lib/content-api"
import {
  fetchVisualConfig,
  fetchPoseGallery,
  savePoseToGallery,
  deletePoseFromGallery,
  generateAvatarPose,
  generateSocialVisual,
  uploadReferenceImage,
  generateCarousel,
  type VisualConfig,
  type AvatarPoseResult,
  type SocialVisualResult,
  type CarouselSlide,
} from "@/lib/visual-api"

type Mode = "client" | "capcore"
type Onglet = "posts" | "hashtags" | "bio"
type OngletCapcore = "posts" | "visuels"

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

const AVATAR_POSES_FALLBACK = [
  { key: "presentation", label: "Présentation" },
  { key: "explication", label: "Explication" },
  { key: "cta", label: "Appel à l'action" },
  { key: "celebration", label: "Célébration" },
  { key: "working", label: "Derrière l'ordi" },
  { key: "showing", label: "Montrant un site" },
]

const ONGLETS_VISUELS = [
  { key: "visuel_post", label: "Visuel Post" },
  { key: "poses_avatar", label: "Poses Avatar" },
  { key: "carrousel", label: "Carrousel" },
] as const

type OngletVisuel = (typeof ONGLETS_VISUELS)[number]["key"]

function CopyButton({ texte, text }: { texte?: string; text?: string }) {
  const content = text ?? texte ?? ""
  const [copie, setCopie] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        navigator.clipboard.writeText(content)
        setCopie(true)
        setTimeout(() => setCopie(false), 2000)
      }}
      className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs text-gray-400 hover:text-white transition-colors"
    >
      {copie ? "✓ Copié" : "Copier"}
    </button>
  )
}

function Lightbox({ url, onClose }: { url: string; onClose: () => void }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div className="relative max-w-4xl max-h-[90vh] w-full mx-4" onClick={e => e.stopPropagation()}>
        <img
          src={url}
          alt="Aperçu"
          className="w-full h-auto rounded-xl object-contain max-h-[85vh]"
        />
        <button
          onClick={onClose}
          className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors text-sm"
        >
          ✕
        </button>
      </div>
    </div>
  )
}

export function StudioCapcorePage() {
  const [mode, setMode] = useState<Mode>("client")
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

  // Mode CapCore
  const [capcoreSubjects, setCapcoreSubjects] = useState<CapcoreSubject[]>([])
  const [capcoreSujet, setCapcoreSujet] = useState<string>("")
  const [capcoreAngle, setCapcoreAngle] = useState<string>("")
  const [capcoreResult, setCapcoreResult] = useState<CapcorePostResult | null>(null)
  const [ongletCapcore, setOngletCapcore] = useState<OngletCapcore>("posts")
  const [ongletVisuel, setOngletVisuel] = useState<OngletVisuel>("visuel_post")

  // Visuels CapCore
  const [visualConfig, setVisualConfig] = useState<VisualConfig | null>(null)
  const [visualFormat, setVisualFormat] = useState<string>("1:1")
  const [visualStyle, setVisualStyle] = useState<string>("professionnel")
  const [visualPose, setVisualPose] = useState<string>("presentation")
  const [visualTexte, setVisualTexte] = useState<string>("")
  const [visualSousTexte, setVisualSousTexte] = useState<string>("CapCore Studio Digital")
  const [visualResult, setVisualResult] = useState<SocialVisualResult | null>(null)
  const [avatarPoseResult, setAvatarPoseResult] = useState<AvatarPoseResult | null>(null)
  const [avatarPoseKey, setAvatarPoseKey] = useState<string>("presentation")
  const [poseGallery, setPoseGallery] = useState<Record<string, string>>({})
  const [loadingVisual, setLoadingVisual] = useState<boolean>(false)
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)
  const [carouselSlides, setCarouselSlides] = useState<CarouselSlide[]>([])
  const [carouselFormat, setCarouselFormat] = useState<string>("1:1")
  const [carouselLoading, setCarouselLoading] = useState(false)
  const [carouselSujet, setCarouselSujet] = useState<string>("")
  const [carouselSujetLabel, setCarouselSujetLabel] = useState<string>("")
  const [referenceUrl, setReferenceUrl] = useState<string | null>(null)
  const [referenceUploading, setReferenceUploading] = useState(false)
  const [referenceError, setReferenceError] = useState<string | null>(null)
  const [carouselError, setCarouselError] = useState<string | null>(null)

  useEffect(() => {
    fetchFormats().then(data => {
      setFormats(data.formats || [])
      setSecteurs(data.secteurs || [])
    })
    fetchCapcoreSubjects().then(subjects => {
      setCapcoreSubjects(subjects)
      if (subjects.length > 0) setCapcoreSujet(subjects[0].key)
    })
    fetchVisualConfig().then(config => {
      setVisualConfig(config)
    })
  }, [])

  // Chargement galerie poses au démarrage
  useEffect(() => {
    fetchPoseGallery()
      .then(poses => {
        const gallery: Record<string, string> = {}
        poses.forEach(p => {
          gallery[p.pose_key] = p.image_url
        })
        setPoseGallery(gallery)
      })
      .catch(() => {
        // Silencieux — galerie vide si erreur réseau
      })
  }, [])

  useEffect(() => {
    if (!lightboxUrl) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightboxUrl(null)
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [lightboxUrl])

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

  const handleGenererCapcore = async () => {
    if (!capcoreSujet || !reseau) return
    setLoading(true)
    setCapcoreResult(null)
    try {
      const result = await generateCapcorePost(capcoreSujet, reseau, capcoreAngle)
      setCapcoreResult(result)
    } finally {
      setLoading(false)
    }
  }

  const handleGenererVisual = async () => {
    if (!visualTexte) return
    setLoadingVisual(true)
    setVisualResult(null)
    const result = await generateSocialVisual({
      texte_principal: visualTexte,
      sous_texte: visualSousTexte,
      format_key: visualFormat,
      style: visualStyle,
      pose_key: visualPose,
      sujet_context: capcoreSujet,
      ...(referenceUrl ? { image_prompt: referenceUrl } : {}),
    })
    setVisualResult(result)
    setLoadingVisual(false)
  }

  const handleGenererAvatarPose = async () => {
    setLoadingVisual(true)
    setAvatarPoseResult(null)
    const result = await generateAvatarPose(avatarPoseKey, "1:1")
    setAvatarPoseResult(result)
    if (result.success && result.image_url) {
      setPoseGallery(prev => ({
        ...prev,
        [avatarPoseKey]: result.image_url!,
      }))
      // Sauvegarde en background — non bloquant
      savePoseToGallery({
        pose_key: avatarPoseKey,
        image_url: result.image_url,
      }).catch(err => console.warn("Sauvegarde pose échouée silencieusement:", err))
    }
    setLoadingVisual(false)
  }

  const handleUploadReference = async (file: File) => {
    setReferenceUploading(true)
    setReferenceError(null)
    try {
      const result = await uploadReferenceImage(file)
      setReferenceUrl(result.reference_url)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur upload image référence"
      setReferenceError(message)
      console.error("Erreur upload référence:", err)
    } finally {
      setReferenceUploading(false)
    }
  }

  const handleGenererCarousel = async () => {
    if (!carouselSujet) return
    setCarouselLoading(true)
    setCarouselSlides([])
    setCarouselError(null)
    try {
      const result = await generateCarousel({
        sujet_type: carouselSujet,
        sujet_label: carouselSujetLabel,
        format_reseau: carouselFormat,
      })
      setCarouselSlides(result.slides)
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur génération carrousel"
      setCarouselError(message)
      console.error("Erreur génération carrousel:", err)
    } finally {
      setCarouselLoading(false)
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

      {/* Toggle Mode */}
      <div className="flex items-center gap-2 mb-6">
        <button
          type="button"
          onClick={() => setMode("client")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "client"
              ? "bg-amber-400 text-black"
              : "bg-white/5 text-white/60 hover:text-white"
          }`}
        >
          Mode Client
        </button>
        <button
          type="button"
          onClick={() => setMode("capcore")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mode === "capcore"
              ? "bg-cyan-400 text-black"
              : "bg-white/5 text-white/60 hover:text-white"
          }`}
        >
          ✦ Mode CapCore
        </button>
        {mode === "capcore" && (
          <span className="text-xs text-white/30 ml-2">
            Contenu pour promouvoir CapCore Studio Digital
          </span>
        )}
      </div>

      {/* MODE CLIENT */}
      {mode === "client" && (
        <>
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
            <div className="space-y-4">
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

            <div className="space-y-4">
              {onglet === "posts" && postResult?.success && (
                <div className="space-y-3">
                  <div className="bg-amber-400/5 border border-amber-400/20 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-amber-400 font-medium uppercase tracking-wider">Accroche</span>
                    </div>
                    <p className="text-white text-sm">{postResult.accroche}</p>
                  </div>

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

                  {postResult.conseil && (
                    <div className="bg-blue-400/5 border border-blue-400/20 rounded-xl p-3">
                      <span className="text-xs text-blue-400">💡 {postResult.conseil}</span>
                    </div>
                  )}
                </div>
              )}

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
        </>
      )}

      {/* MODE CAPCORE */}
      {mode === "capcore" && (
        <>
          <div className="flex gap-2 mb-6">
            <button
              type="button"
              onClick={() => setOngletCapcore("posts")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                ongletCapcore === "posts"
                  ? "bg-cyan-400 text-black"
                  : "bg-white/5 text-white/60 hover:text-white"
              }`}
            >
              Posts
            </button>
            <button
              type="button"
              onClick={() => setOngletCapcore("visuels")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                ongletCapcore === "visuels"
                  ? "bg-cyan-400 text-black"
                  : "bg-white/5 text-white/60 hover:text-white"
              }`}
            >
              ✦ Visuels FLUX
            </button>
          </div>

          {ongletCapcore === "posts" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Réseau social</label>
                  <div className="flex gap-2 flex-wrap">
                    {formats.map(f => (
                      <button
                        key={f.id}
                        type="button"
                        onClick={() => setReseau(f.id)}
                        className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                          reseau === f.id
                            ? "bg-cyan-400 text-black font-medium"
                            : "bg-white/5 text-white/60 hover:text-white"
                        }`}
                      >
                        <i className={`${RESEAU_ICONS[f.id]} mr-1`} />
                        {f.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Sujet</label>
                  <select
                    value={capcoreSujet}
                    onChange={e => setCapcoreSujet(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-400"
                  >
                    {capcoreSubjects.map(s => (
                      <option key={s.key} value={s.key} className="bg-[#0f0f13]">
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">
                    Angle <span className="text-white/30">(optionnel)</span>
                  </label>
                  <input
                    type="text"
                    value={capcoreAngle}
                    onChange={e => setCapcoreAngle(e.target.value)}
                    placeholder="ex : mettre en avant le gain de temps..."
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-cyan-400"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => void handleGenererCapcore()}
                  disabled={loading || !capcoreSujet}
                  className="w-full py-2.5 rounded-lg bg-cyan-400 text-black font-medium text-sm hover:bg-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? "Génération en cours..." : "✦ Générer avec ContentAI"}
                </button>
              </div>

              <div className="space-y-4">
                {capcoreResult?.success && (
                  <>
                    {capcoreResult.post && (
                      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-cyan-400 font-medium uppercase tracking-wide">Post</span>
                          <CopyButton text={capcoreResult.post} />
                        </div>
                        <p className="text-white/90 text-sm whitespace-pre-wrap leading-relaxed">
                          {capcoreResult.post}
                        </p>
                      </div>
                    )}
                    {capcoreResult.accroche && (
                      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-amber-400 font-medium uppercase tracking-wide">Accroche</span>
                          <CopyButton text={capcoreResult.accroche} />
                        </div>
                        <p className="text-white/80 text-sm italic">{capcoreResult.accroche}</p>
                      </div>
                    )}
                    {capcoreResult.hashtags && capcoreResult.hashtags.length > 0 && (
                      <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <span className="text-xs text-white/40 font-medium uppercase tracking-wide block mb-2">Hashtags</span>
                        <div className="flex flex-wrap gap-2">
                          {capcoreResult.hashtags.map((tag, i) => (
                            <button
                              key={i}
                              type="button"
                              onClick={() => navigator.clipboard.writeText(tag)}
                              className="px-2 py-1 bg-cyan-400/10 text-cyan-400 rounded text-xs hover:bg-cyan-400/20 transition-colors"
                            >
                              {tag.startsWith("#") ? tag : `#${tag}`}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                    {capcoreResult.conseil && (
                      <div className="bg-white/5 rounded-xl p-3 border border-white/5">
                        <p className="text-white/40 text-xs">💡 {capcoreResult.conseil}</p>
                      </div>
                    )}
                  </>
                )}
                {capcoreResult && !capcoreResult.success && (
                  <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/20">
                    <p className="text-red-400 text-sm">{capcoreResult.error}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {ongletCapcore === "visuels" && (
            <div className="space-y-6">
              <div className="flex gap-2 flex-wrap">
                {ONGLETS_VISUELS.map(tab => (
                  <button
                    key={tab.key}
                    type="button"
                    onClick={() => setOngletVisuel(tab.key)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      ongletVisuel === tab.key
                        ? "bg-cyan-400/20 border border-cyan-400 text-cyan-400"
                        : "bg-white/5 text-white/60 hover:text-white border border-white/10"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {ongletVisuel === "visuel_post" && (
              <div className="border border-white/10 rounded-xl p-5">
                <h3 className="text-sm font-medium text-white/80 mb-4">
                  ✦ Visuel post réseaux sociaux
                </h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm text-white/60 mb-2">Texte principal</label>
                      <input
                        type="text"
                        value={visualTexte}
                        onChange={e => setVisualTexte(e.target.value)}
                        placeholder="ex : Votre site en 30 minutes"
                        maxLength={80}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-cyan-400"
                      />
                      <span className="text-xs text-white/20 mt-1 block text-right">
                        {visualTexte.length}/80
                      </span>
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-2">Sous-texte</label>
                      <input
                        type="text"
                        value={visualSousTexte}
                        onChange={e => setVisualSousTexte(e.target.value)}
                        placeholder="CapCore Studio Digital"
                        maxLength={60}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-cyan-400"
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-2">Format</label>
                      <div className="flex gap-2 flex-wrap">
                        {(visualConfig?.formats || [
                          { key: "1:1", label: "Instagram Feed" },
                          { key: "9:16", label: "Stories / TikTok" },
                          { key: "16:9", label: "LinkedIn" },
                        ]).map(f => (
                          <button
                            key={f.key}
                            type="button"
                            onClick={() => setVisualFormat(f.key)}
                            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                              visualFormat === f.key
                                ? "bg-cyan-400 text-black font-medium"
                                : "bg-white/5 text-white/60 hover:text-white"
                            }`}
                          >
                            {f.key} — {f.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-2">Pose avatar</label>
                      <select
                        value={visualPose}
                        onChange={e => setVisualPose(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-400"
                      >
                        {(visualConfig?.poses || AVATAR_POSES_FALLBACK).map(p => (
                          <option key={p.key} value={p.key} className="bg-[#0f0f13]">
                            {p.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-2">Style</label>
                      <div className="flex gap-2 flex-wrap">
                        {(visualConfig?.styles || [
                          { key: "professionnel", label: "Professionnel" },
                          { key: "moderne", label: "Moderne" },
                          { key: "minimaliste", label: "Minimaliste" },
                        ]).map(s => (
                          <button
                            key={s.key}
                            type="button"
                            onClick={() => setVisualStyle(s.key)}
                            className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                              visualStyle === s.key
                                ? "bg-cyan-400 text-black font-medium"
                                : "bg-white/5 text-white/60 hover:text-white"
                            }`}
                          >
                            {s.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm text-white/60 mb-2">
                        Image de référence <span className="text-white/30">(optionnel)</span>
                      </label>
                      <div
                        className="border border-dashed border-white/20 rounded-lg p-4 text-center cursor-pointer hover:border-white/40 transition-colors"
                        onClick={() => document.getElementById("ref-upload")?.click()}
                      >
                        {referenceUrl ? (
                          <div className="flex items-center gap-2 justify-center">
                            <img src={referenceUrl} className="w-10 h-10 object-cover rounded" alt="ref" />
                            <span className="text-xs text-green-400">✓ Image chargée</span>
                            <button
                              type="button"
                              onClick={e => { e.stopPropagation(); setReferenceUrl(null); setReferenceError(null) }}
                              className="text-xs text-white/40 hover:text-white/60"
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs text-white/40">
                            {referenceUploading ? "⏳ Upload..." : "+ Ajouter une image de référence"}
                          </span>
                        )}
                      </div>
                      <input
                        id="ref-upload"
                        type="file"
                        accept="image/png,image/jpeg,image/webp"
                        className="hidden"
                        onChange={e => {
                          const file = e.target.files?.[0]
                          if (file) void handleUploadReference(file)
                        }}
                      />
                      {referenceError && (
                        <div className="mt-2 bg-red-500/10 rounded-xl p-3 border border-red-500/20">
                          <p className="text-red-400 text-sm">{referenceError}</p>
                        </div>
                      )}
                    </div>

                    <button
                      type="button"
                      onClick={() => void handleGenererVisual()}
                      disabled={loadingVisual || !visualTexte}
                      className="w-full py-2.5 rounded-lg bg-cyan-400 text-black font-medium text-sm hover:bg-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {loadingVisual ? "Génération FLUX en cours (~20s)..." : "✦ Générer le visuel"}
                    </button>
                  </div>

                  <div className="flex items-center justify-center">
                    {visualResult?.success && visualResult.image_url ? (
                      <div className="space-y-3 w-full">
                        <img
                          src={visualResult.image_url}
                          alt="Visuel généré"
                          onClick={() => setLightboxUrl(visualResult.image_url!)}
                          className="w-full rounded-xl border border-white/10 object-cover cursor-zoom-in hover:opacity-90 transition-opacity"
                        />
                        <div className="flex gap-2">
                          <a
                            href={visualResult.image_url}
                            download
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex-1 py-2 rounded-lg bg-white/5 text-white/70 text-xs text-center hover:bg-white/10 transition-colors"
                          >
                            ↓ Télécharger
                          </a>
                          <button
                            type="button"
                            onClick={() => navigator.clipboard.writeText(visualResult.image_url!)}
                            className="flex-1 py-2 rounded-lg bg-white/5 text-white/70 text-xs hover:bg-white/10 transition-colors"
                          >
                            Copier l'URL
                          </button>
                        </div>
                      </div>
                    ) : visualResult && !visualResult.success ? (
                      <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/20 w-full">
                        <p className="text-red-400 text-sm">{visualResult.error}</p>
                      </div>
                    ) : (
                      <div className="w-full aspect-square rounded-xl border border-white/5 bg-white/5 flex items-center justify-center">
                        <p className="text-white/20 text-sm">Le visuel apparaîtra ici</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              )}

              {ongletVisuel === "poses_avatar" && (
              <div className="border border-white/10 rounded-xl p-5">
                <h3 className="text-sm font-medium text-white/80 mb-1">
                  Avatar CapCore — Poses
                </h3>
                <p className="text-xs text-white/30 mb-4">
                  Génère chaque pose une fois et réutilise-la dans tes visuels.
                </p>

                {/* Grille poses */}
                <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
                  {(visualConfig?.poses || AVATAR_POSES_FALLBACK).map(p => {
                    const stored = poseGallery[p.key]
                    return (
                      <div
                        key={p.key}
                        onClick={() => setAvatarPoseKey(p.key)}
                        className={`rounded-xl border transition-colors cursor-pointer overflow-hidden ${
                          avatarPoseKey === p.key
                            ? "border-cyan-400"
                            : "border-white/10"
                        }`}
                      >
                        {stored ? (
                          <div className="relative group">
                            <img
                              src={stored}
                              alt={p.label}
                              className="w-full aspect-square object-cover"
                            />
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                              <button
                                type="button"
                                onClick={e => { e.stopPropagation(); setLightboxUrl(stored) }}
                                className="px-2 py-1 bg-white/20 text-white text-xs rounded-lg hover:bg-white/30"
                              >
                                Voir
                              </button>
                              <a
                                href={stored}
                                download
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={e => e.stopPropagation()}
                                className="px-2 py-1 bg-cyan-400/80 text-black text-xs rounded-lg hover:bg-cyan-400"
                              >
                                ↓
                              </a>
                              <button
                                type="button"
                                onClick={async e => {
                                  e.stopPropagation()
                                  await deletePoseFromGallery(p.key)
                                  setPoseGallery(prev => {
                                    const next = { ...prev }
                                    delete next[p.key]
                                    return next
                                  })
                                }}
                                className="p-1.5 rounded bg-red-500/80 hover:bg-red-500 text-white text-xs"
                                title="Supprimer"
                              >
                                🗑️
                              </button>
                            </div>
                            <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1">
                              <p className="text-white text-xs truncate">{p.label}</p>
                            </div>
                          </div>
                        ) : (
                          <div className="aspect-square bg-white/3 flex flex-col items-center justify-center gap-1 p-2">
                            <span className="text-2xl opacity-20">👤</span>
                            <p className="text-white/40 text-xs text-center">{p.label}</p>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Bouton générer pose sélectionnée */}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => void handleGenererAvatarPose()}
                    disabled={loadingVisual}
                    className="px-4 py-2 rounded-lg bg-white/5 text-white/70 text-sm hover:bg-white/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {loadingVisual
                      ? "Génération..."
                      : `Générer — ${(visualConfig?.poses || AVATAR_POSES_FALLBACK).find(p => p.key === avatarPoseKey)?.label || avatarPoseKey}`
                    }
                  </button>
                  {avatarPoseResult && !avatarPoseResult.success && (
                    <p className="text-red-400 text-xs">{avatarPoseResult.error}</p>
                  )}
                </div>
              </div>
              )}

              {ongletVisuel === "carrousel" && (
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm text-white/60 mb-2">Sujet du carrousel</label>
                    <select
                      value={carouselSujet}
                      onChange={e => {
                        const opt = capcoreSubjects.find(s => s.key === e.target.value)
                        setCarouselSujet(e.target.value)
                        setCarouselSujetLabel(opt?.label || "")
                      }}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-400"
                    >
                      <option value="" className="bg-[#0f0f13]">-- Choisir un sujet --</option>
                      {capcoreSubjects.map(s => (
                        <option key={s.key} value={s.key} className="bg-[#0f0f13]">
                          {s.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm text-white/60 mb-2">Format</label>
                    <div className="flex gap-2">
                      {["1:1", "1:1_facebook", "9:16", "16:9"].map(fmt => (
                        <button
                          key={fmt}
                          type="button"
                          onClick={() => setCarouselFormat(fmt)}
                          className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                            carouselFormat === fmt
                              ? "bg-cyan-400/20 border-cyan-400 text-cyan-400"
                              : "bg-white/5 border-white/10 text-white/60 hover:border-white/30"
                          }`}
                        >
                          {fmt}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => void handleGenererCarousel()}
                    disabled={!carouselSujet || carouselLoading}
                    className="w-full py-3 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:opacity-40 disabled:cursor-not-allowed text-black font-semibold transition-colors"
                  >
                    {carouselLoading ? "⏳ Génération en cours (5 visuels)..." : "✦ Générer le carrousel"}
                  </button>

                  {carouselError && (
                    <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/20">
                      <p className="text-red-400 text-sm">{carouselError}</p>
                    </div>
                  )}

                  {carouselSlides.length > 0 && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white/60">{carouselSlides.length} slides générées</span>
                        <button
                          type="button"
                          onClick={() => {
                            carouselSlides.forEach((slide, i) => {
                              const a = document.createElement("a")
                              a.href = slide.image_url
                              a.download = `carrousel_slide_${i + 1}_${slide.role}.png`
                              a.click()
                            })
                          }}
                          className="text-xs px-3 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white/80 transition-colors"
                        >
                          ↓ Tout télécharger
                        </button>
                      </div>

                      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
                        {carouselSlides.map(slide => (
                          <div key={slide.slide_index} className="relative group">
                            <div className="absolute top-2 left-2 z-10 flex gap-1">
                              <span className="bg-cyan-500 text-black text-xs font-bold px-1.5 py-0.5 rounded">
                                {slide.slide_index}/5
                              </span>
                              <span className="bg-black/60 text-white/80 text-xs px-1.5 py-0.5 rounded capitalize">
                                {slide.role.replace("_", " ")}
                              </span>
                            </div>

                            <img
                              src={slide.image_url}
                              alt={`Slide ${slide.slide_index}`}
                              className="w-full aspect-square object-cover rounded-lg cursor-zoom-in"
                              onClick={() => setLightboxUrl(slide.image_url)}
                            />

                            <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2">
                              <button
                                type="button"
                                onClick={() => setLightboxUrl(slide.image_url)}
                                className="px-3 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white text-xs font-medium"
                              >
                                Voir
                              </button>
                              <a
                                href={slide.image_url}
                                download={`carrousel_slide_${slide.slide_index}.png`}
                                className="px-3 py-1.5 rounded-lg bg-white/20 hover:bg-white/30 text-white text-xs font-medium"
                              >
                                ↓
                              </a>
                            </div>

                            <p className="mt-1 text-xs text-white/50 truncate">{slide.titre}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}

      {lightboxUrl && <Lightbox url={lightboxUrl} onClose={() => setLightboxUrl(null)} />}
    </div>
  )
}
