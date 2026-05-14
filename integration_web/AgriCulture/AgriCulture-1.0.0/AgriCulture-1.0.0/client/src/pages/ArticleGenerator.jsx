import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Cpu,
  Database,
  Download,
  FileCode2,
  FileJson,
  FileText,
  FlaskConical,
  Info,
  Layers,
  Loader2,
  Microscope,
  Network,
  PenTool,
  Search,
  Server,
  Sparkles,
} from 'lucide-react'
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  WRITING_API_BASE,
  checkWritingHealth,
  generateWritingDemo,
  generateWritingReport,
  getLatestWritingResults,
} from '../services/writingApi'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend)

const OVERVIEW_CARDS = [
  {
    title: 'Multi-Agent Drafting',
    icon: Sparkles,
    text: 'Planner, evidence, literature, DNA, writer, and critic agents collaborate to build the manuscript.',
  },
  {
    title: 'Evidence Retrieval',
    icon: Search,
    text: 'PubMed, NCBI, UniProt, and vector-store context are merged into a reproducible writing workflow.',
  },
  {
    title: 'DNA Analytics',
    icon: Microscope,
    text: 'Optional sequence analysis surfaces GC profile, ORFs, motifs, translation, and embedding metadata.',
  },
  {
    title: 'Export Pipeline',
    icon: FileText,
    text: 'Every run can produce JSON, TeX, PDF, figures, warnings, and fallback provenance for the group frontend.',
  },
]

const PIPELINE_STEPS = ['Topic', 'Evidence', 'Literature', 'DNA Analysis', 'Writer', 'Critic', 'Export']

const PREVIEW_ORDER = ['abstract', 'introduction', 'methods', 'results', 'discussion', 'conclusion']

const emptyForm = {
  topic: 'Drought resistance genes in maize',
  dna_sequence: 'ATGCGTACGTAGCTAGCTAGCTAG',
  max_revision_rounds: 2,
}

const sectionLabel = (value) => value.charAt(0).toUpperCase() + value.slice(1)

const metricValue = (value, suffix = '') => {
  if (value === null || value === undefined || value === '') return 'N/A'
  return `${value}${suffix}`
}

const shortText = (value, fallback = 'No preview available yet.') => {
  const text = String(value || '').trim()
  return text || fallback
}

const latestFigureUrls = (payload) => payload?.asset_urls?.figures || []

const backendAssetUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${WRITING_API_BASE}${url}`
}

const outputLinks = (payload) => {
  if (!payload?.asset_urls) return []
  return [
    { label: 'PDF', href: backendAssetUrl(payload.asset_urls.pdf), icon: Download },
    { label: 'TeX', href: backendAssetUrl(payload.asset_urls.tex), icon: FileCode2 },
    { label: 'JSON', href: backendAssetUrl(payload.asset_urls.json_url), icon: FileJson },
  ].filter((item) => item.href)
}

const serviceModeMessage = (service, status) => {
  if (service === 'pdflatex' && status?.used_fallback) {
    return 'pdflatex is not installed, so the backend generated a downloadable PDF with the built-in ReportLab fallback.'
  }
  if (service === 'dnabert' && status?.used_fallback) {
    return 'DNABERT weights are not loaded, so this run used the deterministic local embedding path.'
  }
  return status?.message || 'No status message.'
}

const serviceModeLabel = (service, status) => {
  if (!status?.used_fallback) return 'Live'
  if (service === 'pdflatex') return 'Fallback PDF'
  if (service === 'dnabert') return 'Local embedding'
  return 'Fallback'
}

const chartBaseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: {
        color: '#64748b',
        boxWidth: 10,
        font: { size: 11, weight: 'bold' },
      },
    },
    tooltip: {
      backgroundColor: '#0f172a',
      padding: 14,
      cornerRadius: 12,
    },
  },
}

const ArticleGenerator = () => {
  const [form, setForm] = useState(emptyForm)
  const [backendOnline, setBackendOnline] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingLatest, setLoadingLatest] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const initialize = async () => {
      try {
        await checkWritingHealth()
        setBackendOnline(true)
        setError('')
      } catch {
        setBackendOnline(false)
        setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
      }
    }

    initialize()
  }, [])

  const summary = result?.summary
  const report = result?.report || {}
  const paper = report.paper || {}
  const literature = report.literature || {}
  const dna = report.dna_analysis || {}
  const figureUrls = latestFigureUrls(result)
  const links = outputLinks(result)

  const summaryMetrics = useMemo(
    () => [
      { label: 'Literature records', value: summary?.literature_count },
      { label: 'Evidence entries', value: summary?.evidence_count },
      { label: 'References', value: summary?.references_count },
      { label: 'GC content', value: summary?.dna_metrics?.gc_percent, suffix: '%' },
      { label: 'ORFs detected', value: summary?.dna_metrics?.orf_count },
      { label: 'Embedding dim', value: summary?.dna_metrics?.embedding_dim },
    ],
    [summary],
  )

  const summaryTableRows = Array.isArray(paper.summary_table) ? paper.summary_table.slice(1) : []
  const fallbackEntries = Object.entries(result?.fallbacks || {})

  const sourceStatusCounts = useMemo(() => {
    if (!fallbackEntries.length) return [0, 0]
    let live = 0
    let fallback = 0
    fallbackEntries.forEach(([, status]) => {
      if (status?.used_fallback) fallback += 1
      else live += 1
    })
    return [live, fallback]
  }, [fallbackEntries])

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const runReport = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = await generateWritingReport({
        topic: form.topic,
        dna_sequence: form.dna_sequence.trim() || null,
        max_revision_rounds: Number(form.max_revision_rounds),
      })
      setBackendOnline(true)
      setResult(payload)
    } catch {
      setBackendOnline(false)
      setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setLoading(false)
    }
  }

  const loadDemo = async () => {
    setLoading(true)
    setError('')
    try {
      const payload = await generateWritingDemo()
      setBackendOnline(true)
      setResult(payload)
    } catch {
      setBackendOnline(false)
      setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setLoading(false)
    }
  }

  const loadLatest = async () => {
    setLoadingLatest(true)
    setError('')
    try {
      const payload = await getLatestWritingResults()
      setBackendOnline(true)
      setResult(payload)
    } catch (err) {
      if (err?.response?.status === 404) {
        setBackendOnline(true)
        setError('No previous Writing report is available yet. Run the pipeline first.')
      } else {
        setBackendOnline(false)
        setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
      }
    } finally {
      setLoadingLatest(false)
    }
  }

  return (
    <div className="py-12 container mx-auto px-4">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12">
          <div className="flex items-center space-x-3 mb-4 text-emerald-600 font-bold tracking-widest text-sm uppercase">
            <PenTool className="w-5 h-5" />
            <span>Writing Research Studio</span>
          </div>
          <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 items-center">
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 mb-4">Plant Research Paper Intelligence</h1>
              <p className="text-slate-600 text-lg max-w-3xl">
                Multi-agent scientific drafting for plant genetics topics, evidence retrieval, and optional DNA sequence analysis.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Pill tone="amber" icon={AlertTriangle} text="AI draft support - expert review required" />
                <BackendBadge online={backendOnline} />
              </div>
            </div>
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <div className="grid sm:grid-cols-2 gap-4">
                <MetricCard label="Output mode" value="PDF / TeX / JSON" />
                <MetricCard label="DNA analysis" value={summary?.dna_provided ? 'Enabled' : 'Optional'} />
                <MetricCard label="Revision rounds" value={metricValue(form.max_revision_rounds)} />
                <MetricCard label="Pipeline" value="Writer + Critic" />
              </div>
              <div className="mt-6 bg-slate-50 border border-slate-100 rounded-2xl p-5">
                <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">Architecture</div>
                <div className="flex flex-wrap gap-2">
                  {PIPELINE_STEPS.map((step, index) => (
                    <React.Fragment key={step}>
                      <span className="bg-white border border-slate-200 rounded-full px-4 py-2 text-xs font-bold text-slate-700">
                        {step}
                      </span>
                      {index < PIPELINE_STEPS.length - 1 && <span className="text-slate-300 font-bold self-center">→</span>}
                    </React.Fragment>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </header>

        {error && (
          <div className="bg-amber-50 border border-amber-100 text-amber-800 rounded-2xl p-5 mb-8 flex items-start gap-3">
            <Info className="w-5 h-5 mt-0.5 flex-shrink-0" />
            <p className="text-sm font-semibold">{error}</p>
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          {OVERVIEW_CARDS.map((card) => (
            <FeatureCard key={card.title} {...card} />
          ))}
        </div>

        <div className="grid lg:grid-cols-[420px_1fr] gap-8 mb-12 items-start">
          <form onSubmit={runReport} className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <FlaskConical className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Drafting Parameters</h2>
                <p className="text-slate-500 text-sm">Keep the same Writing route, but drive it with the real shared backend.</p>
              </div>
            </div>

            <div className="space-y-5">
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">Research Topic</label>
                <input
                  value={form.topic}
                  onChange={(event) => updateField('topic', event.target.value)}
                  className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-2 focus:ring-emerald-500/20"
                  placeholder="Drought resistance genes in maize"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">Optional DNA Sequence</label>
                <textarea
                  value={form.dna_sequence}
                  onChange={(event) => updateField('dna_sequence', event.target.value.toUpperCase())}
                  className="w-full p-4 min-h-[150px] bg-slate-50 border border-slate-200 rounded-2xl text-sm font-mono outline-none focus:ring-2 focus:ring-emerald-500/20"
                  placeholder="ATGCGTACGTAGCTAGCTAGCTAG"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">Revision Rounds</label>
                <select
                  value={form.max_revision_rounds}
                  onChange={(event) => updateField('max_revision_rounds', event.target.value)}
                  className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm outline-none"
                >
                  {[1, 2, 3, 4].map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={loading || !form.topic.trim()}
                className="inline-flex items-center gap-2 px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all shadow-lg shadow-emerald-200 disabled:opacity-60"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Run Writing Pipeline
              </button>
              <button
                type="button"
                onClick={loadDemo}
                disabled={loading}
                className="px-5 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl font-bold transition-all disabled:opacity-60"
              >
                Demo Run
              </button>
              <button
                type="button"
                onClick={loadLatest}
                disabled={loadingLatest}
                className="px-5 py-3 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-2xl font-bold transition-all disabled:opacity-60"
              >
                {loadingLatest ? 'Loading...' : 'Load Previous Report'}
              </button>
            </div>
          </form>

          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Database className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Run Snapshot</h2>
              <p className="text-slate-500 text-sm">This panel updates from the report you just ran or explicitly loaded.</p>
              </div>
            </div>

            {summary ? (
              <>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {summaryMetrics.map((item) => (
                    <MetricCard key={item.label} label={item.label} value={metricValue(item.value, item.suffix || '')} />
                  ))}
                </div>

                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 h-[260px]">
                    <Bar
                      data={{
                        labels: ['Literature', 'Evidence', 'References', 'ORFs', 'Motifs'],
                        datasets: [
                          {
                            label: 'Count',
                            data: [
                              summary.literature_count || 0,
                              summary.evidence_count || 0,
                              summary.references_count || 0,
                              summary.dna_metrics?.orf_count || 0,
                              summary.dna_metrics?.motif_count || 0,
                            ],
                            backgroundColor: ['#10b981', '#2563eb', '#0f172a', '#f59e0b', '#e11d48'],
                            borderRadius: 10,
                          },
                        ],
                      }}
                      options={{
                        ...chartBaseOptions,
                        plugins: { ...chartBaseOptions.plugins, legend: { display: false } },
                        scales: {
                          y: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
                          x: { grid: { display: false }, ticks: { color: '#64748b' } },
                        },
                      }}
                    />
                  </div>

                  <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 h-[260px]">
                    <Doughnut
                      data={{
                        labels: ['Live services', 'Fallback services'],
                        datasets: [
                          {
                            data: sourceStatusCounts,
                            backgroundColor: ['#10b981', '#f59e0b'],
                            borderWidth: 0,
                          },
                        ],
                      }}
                      options={{
                        ...chartBaseOptions,
                        cutout: '68%',
                      }}
                    />
                  </div>
                </div>
              </>
            ) : (
              <EmptyState label="No report loaded yet" text="Run the pipeline for your current topic, or load a previous report manually." />
            )}
          </div>
        </div>

        {summary && (
          <>
            <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-emerald-600 mb-2">Generated Title</div>
                  <h2 className="text-2xl font-bold text-slate-900">{summary.title}</h2>
                  <p className="text-slate-500 text-sm mt-2">{summary.topic}</p>
                </div>
                <div className="flex flex-wrap gap-3">
                  {links.map(({ label, href, icon: Icon }) => (
                    <a
                      key={label}
                      href={href}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-slate-200 bg-white text-slate-700 text-xs font-bold uppercase tracking-widest hover:bg-slate-50"
                    >
                      <Icon className="w-4 h-4" />
                      {label}
                    </a>
                  ))}
                </div>
              </div>

              <div className="grid lg:grid-cols-[0.9fr_1.1fr] gap-8">
                <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <BookOpen className="w-5 h-5 text-emerald-600" />
                    <h3 className="font-bold text-slate-900">Key Findings</h3>
                  </div>
                  <ul className="space-y-3 text-sm text-slate-600">
                    {(summary.key_findings || []).map((item) => (
                      <li key={item} className="flex items-start gap-3">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Layers className="w-5 h-5 text-emerald-600" />
                    <h3 className="font-bold text-slate-900">Report Metrics</h3>
                  </div>
                  {summaryTableRows.length ? (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <tbody>
                          {summaryTableRows.map((row) => (
                            <tr key={row.join('-')} className="border-b last:border-b-0 border-slate-200">
                              <td className="py-3 pr-4 font-semibold text-slate-500">{row[0]}</td>
                              <td className="py-3 text-right font-bold text-slate-900">{row[1]}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <EmptyState label="No summary table" text="The backend did not return a summary table for this report." compact />
                  )}
                </div>
              </div>
            </section>

            <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
              <div className="flex items-center gap-3 mb-6">
                <Microscope className="w-6 h-6 text-emerald-600" />
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">DNA Analytics & Figures</h2>
                  <p className="text-slate-500 text-sm">The original project already emits GC profile and ORF figure artifacts, so we surface them directly here.</p>
                </div>
              </div>

              <div className="grid lg:grid-cols-4 gap-4 mb-6">
                <MetricCard label="Sequence length" value={metricValue(dna.sequence_length)} />
                <MetricCard label="GC percent" value={metricValue(dna.gc_percent, '%')} />
                <MetricCard label="Protein translation" value={metricValue(dna.protein_translation)} />
                <MetricCard label="Embedding dim" value={metricValue(dna.embedding_dim)} />
              </div>

              <div className="grid lg:grid-cols-2 gap-6">
                {figureUrls.length ? (
                  figureUrls.map((url, index) => (
                    <div key={url} className="bg-slate-50 border border-slate-100 rounded-2xl p-4">
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
                        {index === 0 ? 'GC profile' : 'ORF map'}
                      </div>
                      <img src={backendAssetUrl(url)} alt="DNA figure" className="w-full rounded-2xl border border-slate-200 bg-white" />
                    </div>
                  ))
                ) : (
                  <>
                    <EmptyState label="GC profile pending" text="Run a report with DNA input to generate figure artifacts." compact />
                    <EmptyState label="ORF map pending" text="Run a report with DNA input to generate figure artifacts." compact />
                  </>
                )}
              </div>
            </section>

            <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
              <div className="flex items-center gap-3 mb-6">
                <FileText className="w-6 h-6 text-emerald-600" />
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Section Previews</h2>
                  <p className="text-slate-500 text-sm">Structured previews are much easier to scan than the old placeholder markdown block.</p>
                </div>
              </div>
              <div className="grid lg:grid-cols-2 gap-6">
                {PREVIEW_ORDER.map((section) => (
                  <div key={section} className="bg-slate-50 border border-slate-100 rounded-2xl p-6">
                    <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">{sectionLabel(section)}</div>
                    <p className="text-sm text-slate-600 leading-7">{shortText(summary.section_previews?.[section])}</p>
                  </div>
                ))}
              </div>
            </section>

            <div className="grid lg:grid-cols-2 gap-8 mb-12">
              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <Search className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Literature & Evidence</h2>
                    <p className="text-slate-500 text-sm">We keep both the paper list and the auxiliary evidence objects visible for the team.</p>
                  </div>
                </div>
                <div className="space-y-4">
                  {(literature.papers || []).map((paperItem, index) => (
                    <div key={`${paperItem.title}-${index}`} className="bg-slate-50 border border-slate-100 rounded-2xl p-5">
                      <div className="font-bold text-slate-900 mb-2">{paperItem.title || 'Untitled paper'}</div>
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">
                        {paperItem.journal || 'N/A'} · {paperItem.year || 'N/A'} · PMID {paperItem.pmid || 'N/A'}
                      </div>
                      <p className="text-sm text-slate-600 leading-6">{shortText(paperItem.abstract, 'No abstract returned for this record.')}</p>
                    </div>
                  ))}
                  {!literature.papers?.length && <EmptyState label="No literature records" text="A fresh run will populate retrieval results here." compact />}
                </div>
              </section>

              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <Network className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Service Modes & Retrieved Context</h2>
                    <p className="text-slate-500 text-sm">Optional heavy tools can fall back locally while still producing usable exports.</p>
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-4 mb-6">
                  {fallbackEntries.map(([service, status]) => (
                    <div key={service} className="bg-slate-50 border border-slate-100 rounded-2xl p-4">
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <div className="text-xs font-bold uppercase tracking-widest text-slate-400">{service}</div>
                        <span
                          className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-widest ${
                            status?.used_fallback ? 'bg-amber-50 text-amber-700 border border-amber-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'
                          }`}
                        >
                          {serviceModeLabel(service, status)}
                        </span>
                      </div>
                      <p className="text-sm text-slate-600 leading-6">{serviceModeMessage(service, status)}</p>
                    </div>
                  ))}
                </div>
                <div className="space-y-3">
                  {(report.retrieved_context || []).map((item, index) => (
                    <div key={`${item.text}-${index}`} className="bg-slate-50 border border-slate-100 rounded-2xl p-4">
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">
                        {item.metadata?.type || 'context'}
                      </div>
                      <p className="text-sm text-slate-600 leading-6">{shortText(item.text)}</p>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <section className="bg-amber-50 border border-amber-100 rounded-3xl p-8 mb-12">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-700 mt-1 flex-shrink-0" />
                <div>
                  <h2 className="text-lg font-bold text-amber-900 mb-2">Scientific Limitation</h2>
                  <p className="text-amber-800 text-sm leading-7">
                    This module accelerates scientific drafting and sequence-informed hypothesis generation, but it does not replace domain review, curated literature analysis, or experimental validation.
                  </p>
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}

const FeatureCard = ({ title, icon: Icon, text }) => (
  <motion.div whileHover={{ y: -4 }} className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm h-full">
    <div className="p-3 bg-slate-50 rounded-2xl border border-slate-100 w-fit mb-4">
      <Icon className="w-6 h-6 text-emerald-600" />
    </div>
    <h3 className="text-lg font-bold text-slate-900 mb-2">{title}</h3>
    <p className="text-slate-600 text-sm leading-relaxed">{text}</p>
  </motion.div>
)

const Pill = ({ tone, icon: Icon, text }) => {
  const styles =
    tone === 'amber'
      ? 'bg-amber-50 text-amber-700 border border-amber-100'
      : 'bg-emerald-50 text-emerald-700 border border-emerald-100'

  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit ${styles}`}>
      <Icon className="w-4 h-4" />
      {text}
    </span>
  )
}

const BackendBadge = ({ online }) => {
  if (online === true) return <Pill tone="emerald" icon={CheckCircle2} text="Backend online" />
  if (online === false) return <Pill tone="amber" icon={AlertTriangle} text="Backend offline" />

  return (
    <span className="inline-flex items-center gap-2 bg-slate-50 text-slate-500 border border-slate-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest w-fit">
      <Loader2 className="w-4 h-4 animate-spin" />
      Checking API
    </span>
  )
}

const MetricCard = ({ label, value }) => (
  <div className="bg-white p-5 rounded-2xl border border-slate-200 text-center shadow-sm">
    <div className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-2">{label}</div>
    <div className="text-xl font-black text-slate-900 break-words">{value}</div>
  </div>
)

const EmptyState = ({ label, text, compact = false }) => (
  <div className={`bg-slate-50 border border-slate-100 rounded-2xl text-center text-slate-500 font-semibold ${compact ? 'p-6' : 'p-10'}`}>
    <Server className="w-8 h-8 text-slate-300 mx-auto mb-3" />
    <div className="font-bold text-slate-900 mb-1">{label}</div>
    <p className="text-sm">{text}</p>
  </div>
)

export default ArticleGenerator
