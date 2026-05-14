import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  CheckCircle2,
  Database,
  Download,
  Gavel,
  Info,
  Layers,
  Loader2,
  Scale,
  Search,
  Server,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js'
import { Bar, Doughnut } from 'react-chartjs-2'
import {
  ETHICS_API_BASE,
  checkEthicsHealth,
  getLatestEthicsResults,
  runEthicsAudit,
} from '../services/ethicsApi'

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend)

const OVERVIEW_CARDS = [
  {
    title: 'MLP Compliance Model',
    icon: ShieldCheck,
    text: 'Classifies DNA chunks into low risk, sensitive, or high risk using the trained PlantAI model.',
  },
  {
    title: 'Legal Mapping',
    icon: Gavel,
    text: 'Connects predictions to Tunisia-focused rules and EU biotechnology references.',
  },
  {
    title: 'XAI k-mer Evidence',
    icon: Search,
    text: 'Surfaces the most influential 4-mers for each audited DNA chunk.',
  },
  {
    title: 'Shared API Ready',
    icon: Database,
    text: 'Runs inside the same FastAPI backend and exports the latest JSON report.',
  },
]

const PIPELINE_STEPS = ['DNA', 'k-mers', 'MLP', 'Risk split', 'XAI', 'Laws', 'Decision']

const defaultSequence =
  'ATGCCATGGATAATGCACGCGGGAACGGAACAAAGACACGCGGCGTGCGGGGCCTCGCTCCTCTGGTCTTCCCTCCAGCCCTCGACGGTGGTCATGGCCGCCGCCGCCGCCACTTTCGGCTTCCTCCATCCTCCAATCCGGAAACCTGCAGTCCCACCAC'

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

const assetUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${ETHICS_API_BASE}${url}`
}

const formatNumber = (value, digits = 2) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return 'N/A'
  return number.toFixed(digits)
}

const riskTone = (risk) => {
  if (risk === 'high') return 'rose'
  if (risk === 'medium') return 'amber'
  return 'emerald'
}

const EthicAnalysis = () => {
  const [backendOnline, setBackendOnline] = useState(null)
  const [health, setHealth] = useState(null)
  const [sequence, setSequence] = useState(defaultSequence)
  const [plantName, setPlantName] = useState('Maize ethics sample')
  const [topN, setTopN] = useState(5)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingLatest, setLoadingLatest] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const initialize = async () => {
      try {
        const payload = await checkEthicsHealth()
        setHealth(payload)
        setBackendOnline(true)
        setError('')
      } catch {
        setBackendOnline(false)
        setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
      }
    }

    initialize()
  }, [])

  const distribution = result?.distribution || {}
  const meanProbabilities = result?.mean_probabilities || {}
  const summary = result?.summary || {}
  const tone = riskTone(result?.risk_level)
  const jsonHref = assetUrl(result?.asset_urls?.json)

  const distributionRows = useMemo(
    () => [
      { label: 'Low risk', count: distribution.low_risk, chunkPct: distribution.low_risk_pct, probabilityPct: meanProbabilities.low_risk, color: '#10b981' },
      { label: 'Sensitive', count: distribution.sensitive, chunkPct: distribution.sensitive_pct, probabilityPct: meanProbabilities.sensitive, color: '#f59e0b' },
      { label: 'High risk', count: distribution.high_risk, chunkPct: distribution.high_risk_pct, probabilityPct: meanProbabilities.high_risk, color: '#e11d48' },
    ],
    [distribution, meanProbabilities],
  )

  const runAudit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = await runEthicsAudit({
        sequence,
        plant_name: plantName || 'Custom sequence',
        top_n: Number(topN),
      })
      setBackendOnline(true)
      setResult(payload)
    } catch (err) {
      setBackendOnline(false)
      const detail = err?.response?.data?.detail
      setError(detail || 'Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setLoading(false)
    }
  }

  const loadLatest = async () => {
    setLoadingLatest(true)
    setError('')
    try {
      const payload = await getLatestEthicsResults()
      setBackendOnline(true)
      setResult(payload)
    } catch (err) {
      if (err?.response?.status === 404) {
        setBackendOnline(true)
        setError('No previous ethics report is available yet. Run an audit first.')
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
            <Scale className="w-5 h-5" />
            <span>Ethics Compliance Lab</span>
          </div>
          <div className="grid lg:grid-cols-[1.08fr_0.92fr] gap-8 items-center">
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 mb-4">PlantAI Ethical Compliance Intelligence</h1>
              <p className="text-slate-600 text-lg max-w-3xl">
                Shared-backend genomic ethics auditing for plant DNA sequences, legal review signals, and explainable k-mer evidence.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Pill tone="amber" icon={AlertTriangle} text="Decision support - human review required" />
                <BackendBadge online={backendOnline} />
              </div>
            </div>
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <div className="grid sm:grid-cols-2 gap-4">
                <MetricCard label="Model" value={health?.model_loaded ? 'MLP loaded' : 'Fallback mode'} />
                <MetricCard label="Device" value={health?.device || 'Checking'} />
                <MetricCard label="Input" value="DNA / FASTA" />
                <MetricCard label="Export" value="JSON report" />
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
          <form onSubmit={runAudit} className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <ShieldAlert className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Audit Inputs</h2>
                <p className="text-slate-500 text-sm">Run `projet_9` through the same shared Python backend.</p>
              </div>
            </div>

            <div className="space-y-5">
              <Field label="Plant / sample name" value={plantName} onChange={setPlantName} />
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">DNA or FASTA sequence</label>
                <textarea
                  value={sequence}
                  onChange={(event) => setSequence(event.target.value.toUpperCase())}
                  className="w-full p-4 min-h-[210px] bg-slate-50 border border-slate-200 rounded-2xl text-sm font-mono outline-none focus:ring-2 focus:ring-emerald-500/20"
                  placeholder="Paste A/T/G/C sequence or FASTA content"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">Top k-mers per chunk</label>
                <select
                  value={topN}
                  onChange={(event) => setTopN(event.target.value)}
                  className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm outline-none"
                >
                  {[3, 5, 7, 10].map((value) => (
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
                disabled={loading || sequence.trim().length < 20}
                className="inline-flex items-center gap-2 px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all shadow-lg shadow-emerald-200 disabled:opacity-60"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Run Ethics Audit
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
              <ShieldCheck className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Decision Dashboard</h2>
                <p className="text-slate-500 text-sm">Current audit only. Previous reports load only when you choose them.</p>
              </div>
            </div>

            {result ? (
              <>
                <div className={`rounded-2xl border p-5 mb-6 ${tone === 'rose' ? 'bg-rose-50 border-rose-100' : tone === 'amber' ? 'bg-amber-50 border-amber-100' : 'bg-emerald-50 border-emerald-100'}`}>
                  <div className="flex items-start gap-3">
                    {tone === 'rose' ? <AlertTriangle className="w-5 h-5 text-rose-700 mt-1" /> : <CheckCircle2 className="w-5 h-5 text-emerald-700 mt-1" />}
                    <div>
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">Global decision</div>
                      <h3 className="text-xl font-bold text-slate-900">{summary.decision}</h3>
                    </div>
                  </div>
                </div>

                <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <MetricCard label="DNA length" value={`${result.sequence_length} bp`} />
                  <MetricCard label="Chunks" value={result.total_sequences} />
                  <MetricCard label="Mean confidence" value={`${formatNumber(result.confiance_moyenne)}%`} />
                  <MetricCard label="Uncertain" value={`${formatNumber(result.sequences_incertaines_pct)}%`} />
                </div>

                <div className="grid lg:grid-cols-2 gap-6">
                  <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 h-[280px]">
                    <Doughnut
                      data={{
                        labels: distributionRows.map((row) => row.label),
                        datasets: [{ data: distributionRows.map((row) => row.probabilityPct || 0), backgroundColor: distributionRows.map((row) => row.color), borderWidth: 0 }],
                      }}
                      options={{ ...chartBaseOptions, cutout: '68%' }}
                    />
                  </div>
                  <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4 h-[280px]">
                    <Bar
                      data={{
                        labels: distributionRows.map((row) => row.label),
                        datasets: [{ label: 'Mean probability', data: distributionRows.map((row) => row.probabilityPct || 0), backgroundColor: distributionRows.map((row) => row.color), borderRadius: 10 }],
                      }}
                      options={{
                        ...chartBaseOptions,
                        plugins: { ...chartBaseOptions.plugins, legend: { display: false } },
                        scales: {
                          y: { beginAtZero: true, max: 100, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
                          x: { grid: { display: false }, ticks: { color: '#64748b' } },
                        },
                      }}
                    />
                  </div>
                </div>
              </>
            ) : (
              <EmptyState label="No audit yet" text="Run the ethics audit to populate model decisions, laws, and XAI evidence." />
            )}
          </div>
        </div>

        {result && (
          <>
            <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-emerald-600 mb-2">PlantAI Report</div>
                  <h2 className="text-2xl font-bold text-slate-900">{result.plant_name}</h2>
                  <p className="text-slate-500 text-sm mt-2">
                    Source: {result.source} · Model: {result.model_status?.loaded ? 'MLP loaded' : 'Deterministic fallback'}
                  </p>
                </div>
                {jsonHref && (
                  <a
                    href={jsonHref}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-slate-200 bg-white text-slate-700 text-xs font-bold uppercase tracking-widest hover:bg-slate-50"
                  >
                    <Download className="w-4 h-4" />
                    JSON
                  </a>
                )}
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left border-b border-slate-200">
                      <th className="py-3 pr-4 font-bold text-slate-500">Class</th>
                      <th className="py-3 pr-4 font-bold text-slate-500">Count</th>
                      <th className="py-3 pr-4 font-bold text-slate-500">Chunk percent</th>
                      <th className="py-3 pr-4 font-bold text-slate-500">Mean probability</th>
                      <th className="py-3 pr-4 font-bold text-slate-500">Use</th>
                    </tr>
                  </thead>
                  <tbody>
                    {distributionRows.map((row) => (
                      <tr key={row.label} className="border-b last:border-b-0 border-slate-100">
                        <td className="py-3 pr-4 font-semibold text-slate-800">{row.label}</td>
                        <td className="py-3 pr-4 text-slate-600">{row.count ?? 0}</td>
                        <td className="py-3 pr-4 text-slate-600">{formatNumber(row.chunkPct)}%</td>
                        <td className="py-3 pr-4 text-slate-600">{formatNumber(row.probabilityPct)}%</td>
                        <td className="py-3 pr-4 text-slate-600">
                          {row.label === 'Low risk' ? 'Proceed with normal documentation' : row.label === 'Sensitive' ? 'Human ethics review' : 'Reject or quarantine sequence'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-8 mb-12">
              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <Layers className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Explainable AI</h2>
                    <p className="text-slate-500 text-sm">Top k-mers by frequency for the most relevant audited chunks.</p>
                  </div>
                </div>
                <div className="space-y-4">
                  {(result.xai_top_sequences || []).map((item) => (
                    <div key={item.sequence_id} className="bg-slate-50 border border-slate-100 rounded-2xl p-5">
                      <div className="flex items-center justify-between gap-4 mb-4">
                        <div className="font-bold text-slate-900">Sequence chunk #{item.sequence_id + 1}</div>
                        <span className="rounded-full px-3 py-1 bg-white border border-slate-200 text-xs font-bold text-slate-600">
                          {formatNumber(item.confidence)}% confidence
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(item.top_kmers || []).map((kmer) => (
                          <span key={`${item.sequence_id}-${kmer.kmer}`} className="rounded-full px-4 py-2 bg-white border border-slate-200 text-xs font-bold text-slate-700">
                            {kmer.kmer} · {formatNumber(kmer.frequency, 4)}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <Gavel className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Legal References</h2>
                    <p className="text-slate-500 text-sm">Tunisia-first review signals with EU reference framing.</p>
                  </div>
                </div>
                <div className="space-y-4">
                  {Object.entries(result.lois?.tunisie || {}).map(([group, laws]) => (
                    <div key={group} className="bg-slate-50 border border-slate-100 rounded-2xl p-5">
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">{group.replace('_', ' ')}</div>
                      <ul className="space-y-2 text-sm text-slate-600">
                        {(laws || []).map((law) => (
                          <li key={law} className="flex items-start gap-2">
                            <CheckCircle2 className="w-4 h-4 text-emerald-600 mt-0.5 flex-shrink-0" />
                            <span>{law}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              </section>
            </div>

            <section className="bg-amber-50 border border-amber-100 rounded-3xl p-8 mb-12">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-700 mt-1 flex-shrink-0" />
                <div>
                  <h2 className="text-lg font-bold text-amber-900 mb-2">Scientific & Regulatory Limitation</h2>
                  <p className="text-amber-800 text-sm leading-7">
                    This module supports early-stage genomic ethics triage. It does not replace legal counsel, institutional biosafety review, or official regulatory approval.
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

const Field = ({ label, value, onChange }) => (
  <div>
    <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">{label}</label>
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-2 focus:ring-emerald-500/20"
    />
  </div>
)

const EmptyState = ({ label, text }) => (
  <div className="bg-slate-50 border border-slate-100 rounded-2xl text-center text-slate-500 font-semibold p-10">
    <Server className="w-8 h-8 text-slate-300 mx-auto mb-3" />
    <div className="font-bold text-slate-900 mb-1">{label}</div>
    <p className="text-sm">{text}</p>
  </div>
)

export default EthicAnalysis
