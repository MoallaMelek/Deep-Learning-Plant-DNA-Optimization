import React, { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  CloudSun,
  Cpu,
  Dna,
  Droplets,
  FlaskConical,
  Gauge,
  Info,
  Layers,
  Leaf,
  Loader2,
  Play,
  Server,
  Sparkles,
  Thermometer,
  Trees,
  Wind,
} from 'lucide-react'
import {
  Chart as ChartJS,
  CategoryScale,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import * as THREE from 'three'
import {
  GROWTH_API_BASE,
  checkGrowthHealth,
  predictGrowth,
  simulateGrowth,
  trainGrowthModel,
} from '../services/growthApi'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend)

const OVERVIEW_CARDS = [
  {
    title: 'DNA + Climate Fusion',
    icon: Dna,
    text: 'Combines a raw sequence or accession with Open-Meteo or manual climate variables to forecast growth.',
  },
  {
    title: 'Forecast Timeline',
    icon: BarChart3,
    text: 'Returns day-by-day trajectories for height, leaves, stem thickness, branch count, and health index.',
  },
  {
    title: 'Training Lab',
    icon: Cpu,
    text: 'Allows shared-model training directly from the same backend when artifacts are missing or need refresh.',
  },
  {
    title: 'Simulation Export',
    icon: Layers,
    text: 'Supports chart artifacts, optional GIF simulation, and warning traces without leaving the group UI.',
  },
]

const PIPELINE_STEPS = ['DNA', 'Climate', 'Model', 'Forecast', 'Chart', 'Simulation']

const defaultForm = {
  dna_sequence: 'ATGGCTTCTTCTTCTGCTTCTCCGTTGCTGCTGCTGTTGATGGTGGTGATGCTGCTGATGATGCTGATGCTGATGTTGCTGATGATGCTGCTGCTGATGCTGATGATGCTGATGATGCTGATGATGCTGATGATGCTGATGATGCTGCTGATGATGCTGATGATGCTGCTGATGATGCTGCTGATGAT',
  accession: '',
  days: 60,
  use_open_meteo: false,
  auto_train_if_missing: true,
  generate_gif: true,
  manual_climate: {
    temperature_c: 22,
    humidity_pct: 60,
    precipitation_mm: 1.5,
    sunlight_hours: 8,
    wind_kph: 10,
  },
}

const defaultTrainForm = {
  epochs: 30,
  batch_size: 256,
  learning_rate: 0.001,
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

const formatNumber = (value, digits = 2) => {
  const number = Number(value)
  if (!Number.isFinite(number)) return 'N/A'
  return number.toFixed(digits)
}

const PlantGrowthStudio = () => {
  const [backendOnline, setBackendOnline] = useState(null)
  const [health, setHealth] = useState(null)
  const [form, setForm] = useState(defaultForm)
  const [trainForm, setTrainForm] = useState(defaultTrainForm)
  const [result, setResult] = useState(null)
  const [training, setTraining] = useState(null)
  const [mode, setMode] = useState('predict')
  const [loading, setLoading] = useState(false)
  const [trainingLoading, setTrainingLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const initialize = async () => {
      try {
        const payload = await checkGrowthHealth()
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

  const updateField = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }))
  }

  const updateClimate = (field, value) => {
    setForm((current) => ({
      ...current,
      manual_climate: {
        ...current.manual_climate,
        [field]: value,
      },
    }))
  }

  const updateTrainField = (field, value) => {
    setTrainForm((current) => ({ ...current, [field]: value }))
  }

  const runPrediction = async (simulate = false) => {
    setLoading(true)
    setError('')
    setMode(simulate ? 'simulate' : 'predict')
    try {
      const payload = {
        dna_sequence: form.dna_sequence.trim() || null,
        accession: form.accession.trim() || null,
        days: Number(form.days),
        use_open_meteo: form.use_open_meteo,
        manual_climate: {
          temperature_c: Number(form.manual_climate.temperature_c),
          humidity_pct: Number(form.manual_climate.humidity_pct),
          precipitation_mm: Number(form.manual_climate.precipitation_mm),
          sunlight_hours: Number(form.manual_climate.sunlight_hours),
          wind_kph: Number(form.manual_climate.wind_kph),
        },
        auto_train_if_missing: form.auto_train_if_missing,
        generate_chart: true,
        chart_as_base64: true,
      }

      const response = simulate
        ? await simulateGrowth({
            ...payload,
            generate_gif: form.generate_gif,
            gif_filename: 'latest_growth.gif',
          })
        : await predictGrowth(payload)

      setBackendOnline(true)
      setResult(response)
    } catch {
      setBackendOnline(false)
      setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setLoading(false)
    }
  }

  const runTraining = async () => {
    setTrainingLoading(true)
    setError('')
    try {
      const response = await trainGrowthModel({
        epochs: Number(trainForm.epochs),
        batch_size: Number(trainForm.batch_size),
        learning_rate: Number(trainForm.learning_rate),
      })
      setBackendOnline(true)
      setTraining(response)
      const refreshedHealth = await checkGrowthHealth()
      setHealth(refreshedHealth)
    } catch {
      setBackendOnline(false)
      setError('Backend unavailable. Start the shared API with: python -m uvicorn main_combine:app --reload')
    } finally {
      setTrainingLoading(false)
    }
  }

  const predictionSeries = useMemo(() => result?.predictions || [], [result])
  const chartImage = result?.chart_base64 ? `data:image/png;base64,${result.chart_base64}` : null
  const gifUrl = result?.asset_urls?.gif ? `${GROWTH_API_BASE}${result.asset_urls.gif}` : null

  return (
    <div className="py-12 container mx-auto px-4">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12">
          <div className="flex items-center space-x-3 mb-4 text-emerald-600 font-bold tracking-widest text-sm uppercase">
            <Leaf className="w-5 h-5" />
            <span>Growth Simulation Lab</span>
          </div>
          <div className="grid lg:grid-cols-[1.08fr_0.92fr] gap-8 items-center">
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold text-slate-900 mb-4">Plant Growth Simulator Intelligence</h1>
              <p className="text-slate-600 text-lg max-w-3xl">
                Shared-backend growth forecasting from DNA and climate signals, with optional model training and simulation export.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Pill tone="emerald" icon={CloudSun} text={form.use_open_meteo ? 'Open-Meteo mode' : 'Manual climate mode'} />
                <BackendBadge online={backendOnline} />
              </div>
            </div>
            <PlantGrowthScene summary={result?.summary} loading={loading} />
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
          <div className="space-y-8">
            <form className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8" onSubmit={(event) => event.preventDefault()}>
              <div className="flex items-center gap-3 mb-6">
                <Dna className="w-6 h-6 text-emerald-600" />
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Prediction Inputs</h2>
                  <p className="text-slate-500 text-sm">Run `projet_8` from the same Python and FastAPI backend as the rest of the platform.</p>
                </div>
              </div>

              <div className="space-y-5">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">DNA Sequence</label>
                  <textarea
                    value={form.dna_sequence}
                    onChange={(event) => updateField('dna_sequence', event.target.value.toUpperCase())}
                    className="w-full p-4 min-h-[120px] bg-slate-50 border border-slate-200 rounded-2xl text-sm font-mono outline-none focus:ring-2 focus:ring-emerald-500/20"
                    placeholder="Paste plant DNA sequence"
                  />
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <Field
                    label="NCBI accession"
                    value={form.accession}
                    onChange={(value) => updateField('accession', value)}
                    placeholder="Optional accession"
                  />
                  <Field
                    label="Days"
                    type="number"
                    value={form.days}
                    onChange={(value) => updateField('days', value)}
                    placeholder="60"
                  />
                </div>

                <div className="grid sm:grid-cols-2 gap-4">
                  <ToggleField
                    label="Use Open-Meteo"
                    checked={form.use_open_meteo}
                    onChange={(checked) => updateField('use_open_meteo', checked)}
                  />
                  <ToggleField
                    label="Auto-train if missing"
                    checked={form.auto_train_if_missing}
                    onChange={(checked) => updateField('auto_train_if_missing', checked)}
                  />
                </div>

                {!form.use_open_meteo && (
                  <div className="grid sm:grid-cols-2 gap-4">
                    <ClimateField
                      label="Temperature (C)"
                      icon={Thermometer}
                      value={form.manual_climate.temperature_c}
                      onChange={(value) => updateClimate('temperature_c', value)}
                    />
                    <ClimateField
                      label="Humidity (%)"
                      icon={Droplets}
                      value={form.manual_climate.humidity_pct}
                      onChange={(value) => updateClimate('humidity_pct', value)}
                    />
                    <ClimateField
                      label="Precipitation (mm)"
                      icon={CloudSun}
                      value={form.manual_climate.precipitation_mm}
                      onChange={(value) => updateClimate('precipitation_mm', value)}
                    />
                    <ClimateField
                      label="Sunlight hours"
                      icon={Sparkles}
                      value={form.manual_climate.sunlight_hours}
                      onChange={(value) => updateClimate('sunlight_hours', value)}
                    />
                    <ClimateField
                      label="Wind (kph)"
                      icon={Wind}
                      value={form.manual_climate.wind_kph}
                      onChange={(value) => updateClimate('wind_kph', value)}
                    />
                  </div>
                )}

                <ToggleField
                  label="Generate GIF simulation"
                  checked={form.generate_gif}
                  onChange={(checked) => updateField('generate_gif', checked)}
                />
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => runPrediction(false)}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-5 py-3 bg-emerald-600 hover:bg-emerald-700 text-white rounded-2xl font-bold transition-all shadow-lg shadow-emerald-200 disabled:opacity-60"
                >
                  {loading && mode === 'predict' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Gauge className="w-4 h-4" />}
                  Predict Growth
                </button>
                <button
                  type="button"
                  onClick={() => runPrediction(true)}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-5 py-3 bg-slate-900 hover:bg-slate-800 text-white rounded-2xl font-bold transition-all disabled:opacity-60"
                >
                  {loading && mode === 'simulate' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                  Simulate Growth
                </button>
              </div>
            </form>

            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <div className="flex items-center gap-3 mb-6">
                <Cpu className="w-6 h-6 text-emerald-600" />
                <div>
                  <h2 className="text-2xl font-bold text-slate-900">Training Lab</h2>
                  <p className="text-slate-500 text-sm">Refresh artifacts inside the same shared backend when needed.</p>
                </div>
              </div>

              <div className="grid sm:grid-cols-3 gap-4">
                <Field
                  label="Epochs"
                  type="number"
                  value={trainForm.epochs}
                  onChange={(value) => updateTrainField('epochs', value)}
                />
                <Field
                  label="Batch size"
                  type="number"
                  value={trainForm.batch_size}
                  onChange={(value) => updateTrainField('batch_size', value)}
                />
                <Field
                  label="Learning rate"
                  type="number"
                  step="0.0001"
                  value={trainForm.learning_rate}
                  onChange={(value) => updateTrainField('learning_rate', value)}
                />
              </div>

              <button
                type="button"
                onClick={runTraining}
                disabled={trainingLoading}
                className="mt-6 inline-flex items-center gap-2 px-5 py-3 bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 rounded-2xl font-bold transition-all disabled:opacity-60"
              >
                {trainingLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
                Train Shared Model
              </button>

              {training && (
                <div className="mt-6 grid sm:grid-cols-3 gap-4">
                  <MetricCard label="MSE scaled" value={formatNumber(training.mse_scaled, 4)} />
                  <MetricCard label="Model path" value={training.model_path?.split(/[\\/]/).pop() || 'growth_model.pt'} />
                  <MetricCard label="Status" value="Training complete" />
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
            <div className="flex items-center gap-3 mb-6">
              <Trees className="w-6 h-6 text-emerald-600" />
              <div>
                <h2 className="text-2xl font-bold text-slate-900">Forecast Snapshot</h2>
                <p className="text-slate-500 text-sm">Same design language, but this panel is now driven by real `projet_8` outputs.</p>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-4 mb-6">
              <MetricCard label="Model available" value={health?.model_available ? 'Yes' : 'No'} />
              <MetricCard label="API status" value={health?.status || 'N/A'} />
              <MetricCard label="Artifacts dir" value={health?.artifacts_dir ? 'Configured' : 'N/A'} />
              <MetricCard label="Mode" value={mode === 'simulate' ? 'Simulation' : 'Prediction'} />
            </div>

            <div className="bg-slate-50 border border-slate-100 rounded-2xl p-5">
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

        {result ? (
          <>
            <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm mb-12">
              <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
                <div>
                  <div className="text-xs font-bold uppercase tracking-widest text-emerald-600 mb-2">Run Summary</div>
                  <h2 className="text-2xl font-bold text-slate-900">
                    {mode === 'simulate' ? 'Plant growth simulation complete' : 'Plant growth prediction complete'}
                  </h2>
                  <p className="text-slate-500 text-sm mt-2">
                    DNA source: {result.dna_source} · Climate source: {result.climate_source} · Model status: {result.model_status}
                  </p>
                </div>
                <div className="flex flex-wrap gap-3">
                  <Pill tone="emerald" icon={Leaf} text={mode === 'simulate' ? 'Simulation mode' : 'Forecast mode'} />
                  {result.model_status && <Pill tone="emerald" icon={Cpu} text={result.model_status.replaceAll('_', ' ')} />}
                </div>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard label="Final height (cm)" value={formatNumber(result.summary?.final_height_cm)} />
                <MetricCard label="Final leaf count" value={formatNumber(result.summary?.final_leaf_count, 0)} />
                <MetricCard label="Final branches" value={formatNumber(result.summary?.final_branch_count, 0)} />
                <MetricCard label="Final health" value={formatNumber(result.summary?.final_health, 4)} />
              </div>
            </section>

            <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 mb-12">
              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <BarChart3 className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Forecast Curves</h2>
                    <p className="text-slate-500 text-sm">Height, health, and branching across the full prediction horizon.</p>
                  </div>
                </div>
                <div className="h-[360px]">
                  <Line
                    data={{
                      labels: predictionSeries.map((row) => `Day ${row.day_index + 1}`),
                      datasets: [
                        {
                          label: 'Height (cm)',
                          data: predictionSeries.map((row) => row.height_cm),
                          borderColor: '#10b981',
                          backgroundColor: 'rgba(16,185,129,0.15)',
                          tension: 0.35,
                        },
                        {
                          label: 'Health index',
                          data: predictionSeries.map((row) => row.health_index),
                          borderColor: '#2563eb',
                          backgroundColor: 'rgba(37,99,235,0.15)',
                          tension: 0.35,
                        },
                        {
                          label: 'Branch count',
                          data: predictionSeries.map((row) => row.branch_count),
                          borderColor: '#f59e0b',
                          backgroundColor: 'rgba(245,158,11,0.15)',
                          tension: 0.35,
                        },
                      ],
                    }}
                    options={{
                      ...chartBaseOptions,
                      scales: {
                        y: { beginAtZero: true, grid: { color: 'rgba(15,23,42,0.06)' }, ticks: { color: '#64748b' } },
                        x: { grid: { display: false }, ticks: { color: '#64748b', maxTicksLimit: 8 } },
                      },
                    }}
                  />
                </div>
              </section>

              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <Gauge className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Rendered Output</h2>
                    <p className="text-slate-500 text-sm">Backend-generated chart artifacts and optional simulation media.</p>
                  </div>
                </div>

                <div className="space-y-6">
                  {chartImage ? (
                    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4">
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Growth chart artifact</div>
                      <img src={chartImage} alt="Growth chart" className="w-full rounded-2xl border border-slate-200 bg-white" />
                    </div>
                  ) : (
                    <EmptyState label="Chart pending" text="Run a prediction or simulation to generate the chart artifact." compact />
                  )}

                  {gifUrl ? (
                    <div className="bg-slate-50 border border-slate-100 rounded-2xl p-4">
                      <div className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">Simulation GIF</div>
                      <img src={gifUrl} alt="Growth simulation" className="w-full rounded-2xl border border-slate-200 bg-white" />
                    </div>
                  ) : (
                    <EmptyState
                      label="Simulation GIF pending"
                      text={mode === 'simulate' ? 'The backend did not return a GIF for this simulation run.' : 'Use Simulate Growth with GIF generation enabled to render the animation asset.'}
                      compact
                    />
                  )}
                </div>
              </section>
            </div>

            <div className="grid lg:grid-cols-2 gap-8 mb-12">
              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <CloudSun className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Trajectory Details</h2>
                    <p className="text-slate-500 text-sm">A tighter view of the earliest forecast steps for quick review.</p>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left border-b border-slate-200">
                        <th className="py-3 pr-4 font-bold text-slate-500">Day</th>
                        <th className="py-3 pr-4 font-bold text-slate-500">Height</th>
                        <th className="py-3 pr-4 font-bold text-slate-500">Leaves</th>
                        <th className="py-3 pr-4 font-bold text-slate-500">Health</th>
                      </tr>
                    </thead>
                    <tbody>
                      {predictionSeries.slice(0, 8).map((row) => (
                        <tr key={row.day_index} className="border-b last:border-b-0 border-slate-100">
                          <td className="py-3 pr-4 font-semibold text-slate-700">{row.day_index + 1}</td>
                          <td className="py-3 pr-4 text-slate-600">{formatNumber(row.height_cm)}</td>
                          <td className="py-3 pr-4 text-slate-600">{formatNumber(row.leaf_count, 0)}</td>
                          <td className="py-3 pr-4 text-slate-600">{formatNumber(row.health_index, 4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="bg-white rounded-3xl border border-slate-200 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-6">
                  <Server className="w-6 h-6 text-emerald-600" />
                  <div>
                    <h2 className="text-2xl font-bold text-slate-900">Warnings & Status</h2>
                    <p className="text-slate-500 text-sm">The page stays resilient when climate or simulation helpers degrade.</p>
                  </div>
                </div>
                <div className="space-y-4">
                  {(result.warnings || []).map((warning) => (
                    <div key={warning} className="bg-amber-50 border border-amber-100 rounded-2xl p-4 text-sm text-amber-800 font-medium">
                      {warning}
                    </div>
                  ))}
                  {!result.warnings?.length && <EmptyState label="No warnings" text="This run completed without backend warnings." compact />}
                </div>
              </section>
            </div>
          </>
        ) : (
          <EmptyState label="No growth run yet" text="Run a prediction or simulation to populate the new Growth tab." />
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

const Field = ({ label, value, onChange, type = 'text', step, placeholder }) => (
  <div>
    <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">{label}</label>
    <input
      type={type}
      step={step}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="w-full p-4 bg-slate-50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-2 focus:ring-emerald-500/20"
      placeholder={placeholder}
    />
  </div>
)

const ClimateField = ({ label, icon: Icon, value, onChange }) => (
  <div>
    <label className="block text-xs font-semibold text-slate-500 uppercase mb-2">{label}</label>
    <div className="relative">
      <input
        type="number"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full p-4 pl-11 bg-slate-50 border border-slate-200 rounded-2xl text-sm outline-none focus:ring-2 focus:ring-emerald-500/20"
      />
      <Icon className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
    </div>
  </div>
)

const ToggleField = ({ label, checked, onChange }) => (
  <button
    type="button"
    onClick={() => onChange(!checked)}
    className={`w-full rounded-2xl border p-4 text-left transition-all ${
      checked ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-slate-50 text-slate-500 border-slate-200'
    }`}
  >
    <div className="flex items-center justify-between gap-4">
      <div>
        <div className="text-xs font-bold uppercase tracking-widest">{label}</div>
        <div className="text-sm font-semibold mt-1">{checked ? 'Enabled' : 'Disabled'}</div>
      </div>
      <div className={`w-11 h-6 rounded-full relative transition-colors ${checked ? 'bg-emerald-500' : 'bg-slate-300'}`}>
        <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${checked ? 'left-6' : 'left-1'}`} />
      </div>
    </div>
  </button>
)

const EmptyState = ({ label, text, compact = false }) => (
  <div className={`bg-slate-50 border border-slate-100 rounded-2xl text-center text-slate-500 font-semibold ${compact ? 'p-6' : 'p-10'}`}>
    <Leaf className="w-8 h-8 text-slate-300 mx-auto mb-3" />
    <div className="font-bold text-slate-900 mb-1">{label}</div>
    <p className="text-sm">{text}</p>
  </div>
)

const PlantGrowthScene = ({ summary, loading }) => {
  const mountRef = useRef(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return undefined

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100)
    camera.position.set(0, 1.3, 5.8)
    camera.lookAt(0, 1.4, 0)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0xf8fafc, 1)
    mount.appendChild(renderer.domElement)

    scene.add(new THREE.AmbientLight(0xffffff, 1.2))
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8)
    keyLight.position.set(4, 5, 6)
    scene.add(keyLight)

    const group = new THREE.Group()
    scene.add(group)

    const soil = new THREE.Mesh(
      new THREE.CylinderGeometry(1.8, 2.2, 0.65, 24),
      new THREE.MeshStandardMaterial({ color: '#b08968', roughness: 0.85 }),
    )
    soil.position.y = -0.75
    group.add(soil)

    const stemHeight = Math.max(1.8, Math.min(4.1, Number(summary?.final_height_cm || 30) / 18))
    const leafCount = Math.max(4, Math.min(10, Number(summary?.final_leaf_count || 7)))
    const branchCount = Math.max(1, Math.min(5, Number(summary?.final_branch_count || 2)))
    const health = Math.max(0.3, Math.min(1, Number(summary?.final_health || 0.74)))

    const stem = new THREE.Mesh(
      new THREE.CylinderGeometry(0.1, 0.14, stemHeight, 16),
      new THREE.MeshStandardMaterial({ color: '#2f855a', roughness: 0.5 }),
    )
    stem.position.y = stemHeight / 2 - 0.25
    group.add(stem)

    for (let index = 0; index < leafCount; index += 1) {
      const leaf = new THREE.Mesh(
        new THREE.SphereGeometry(0.22, 12, 12),
        new THREE.MeshStandardMaterial({ color: health > 0.7 ? '#10b981' : '#84cc16', roughness: 0.42 }),
      )
      const heightFactor = 0.25 + (index / leafCount) * (stemHeight - 0.4)
      const direction = index % 2 === 0 ? 1 : -1
      leaf.scale.set(1.6, 0.5, 0.85)
      leaf.position.set(direction * (0.42 + (index % 3) * 0.05), heightFactor, Math.sin(index * 0.7) * 0.22)
      leaf.rotation.z = direction * 0.65
      group.add(leaf)
    }

    for (let index = 0; index < branchCount; index += 1) {
      const branch = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.04, 0.85, 12),
        new THREE.MeshStandardMaterial({ color: '#2f855a', roughness: 0.5 }),
      )
      const side = index % 2 === 0 ? 1 : -1
      branch.position.set(side * 0.26, 0.8 + index * 0.55, 0)
      branch.rotation.z = side * 1.1
      group.add(branch)
    }

    const crown = new THREE.Mesh(
      new THREE.SphereGeometry(0.34 + health * 0.18, 16, 16),
      new THREE.MeshStandardMaterial({ color: '#16a34a', roughness: 0.34 }),
    )
    crown.position.y = stemHeight + 0.15
    group.add(crown)

    const resize = () => {
      const width = mount.clientWidth || 460
      const height = mount.clientHeight || 340
      renderer.setSize(width, height, false)
      camera.aspect = width / height
      camera.updateProjectionMatrix()
    }

    resize()
    const resizeObserver = new ResizeObserver(resize)
    resizeObserver.observe(mount)

    let frame = 0
    const animate = () => {
      frame = window.requestAnimationFrame(animate)
      group.rotation.y += 0.003
      crown.position.x = Math.sin(Date.now() * 0.0012) * 0.05
      renderer.render(scene, camera)
    }
    animate()

    return () => {
      window.cancelAnimationFrame(frame)
      resizeObserver.disconnect()
      renderer.dispose()
      mount.removeChild(renderer.domElement)
    }
  }, [summary])

  return (
    <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="relative h-[340px] w-full bg-gradient-to-b from-emerald-50 to-slate-50">
        <div ref={mountRef} className="h-full w-full" />
        {loading && (
          <div className="absolute inset-0 bg-white/60 flex items-center justify-center text-slate-700 text-xs font-bold uppercase tracking-widest">
            <Loader2 className="w-4 h-4 animate-spin mr-2" />
            Loading forecast
          </div>
        )}
      </div>
      <div className="p-5 border-t border-slate-100 flex items-center justify-between gap-4">
        <div>
          <div className="text-xs font-bold uppercase tracking-widest text-slate-400">3D growth context</div>
          <div className="font-bold text-slate-900">DNA-conditioned plant silhouette</div>
        </div>
        <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest">
          Live 3D
        </span>
      </div>
    </div>
  )
}

export default PlantGrowthStudio
