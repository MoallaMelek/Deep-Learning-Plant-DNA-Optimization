import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import {
  Dna,
  Zap,
  Microscope,
  History as HistoryIcon,
  ChevronRight,
  Upload,
  AlertCircle,
  CheckCircle2,
  Search,
  ArrowRight,
  TrendingUp,
  Wind,
  Droplets,
  Thermometer,
  FileText,
  Download,
  MessageSquare,
  ChevronDown,
  LayoutDashboard
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
  RadialLinearScale
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  RadialLinearScale,
  Title,
  Tooltip,
  Legend,
  Filler
);

// --- Constants & Data ---
const VARIETIES = [
  "SOOTY_9/RASCON_37//JUPARE C 2001/5/GREEN",
  "SOOTY_9/RASCON_37//STORLOM/5/TOSKA_26/RA",
  "CIRNO C 2008/8/TARRO_1/2*YUAN_1//AJAIA_1",
  "HYPERNO/6/WID22202/4/SORA/2*PLATA_12//SO",
  "HYPERNO/12/SOOTY_9/RASCON_37//LLARETA IN",
  "ARMENT//2*SOOTY_9/RASCON_37/4/CNDO/PRIMA",
  "SOMAT_3/GREEN_22/4/GODRIN/GUTROS//DUKEM/",
  "HI 8737  x  JANDAROI/5/SOOTY_9/RASCON_37"
];

const TRAIT_NORMS = { drought: 0.431, salt: 0.538, yield: 0.377, disease: 0.516 };

const COLORS = {
  bg: "#f0f4f8",
  surface: "rgba(255, 255, 255, 0.8)",
  primary: "#10b981",
  secondary: "#60a5fa",
  tertiary: "#fbbf24",
  text: "#1e293b",
  muted: "#94a3b8",
  border: "rgba(255, 255, 255, 0.5)"
};

// --- Helper Components ---
const StatusBadge = ({ status }) => (
  <div className="flex items-center gap-2 bg-emerald-50/50 backdrop-blur-md px-3 py-1 rounded-full border border-emerald-100/50">
    <div className={`w-1.5 h-1.5 rounded-full ${status === 'ready' ? 'bg-emerald-400 animate-pulse' : 'bg-slate-300'}`} />
    <span className="text-[9px] font-black text-emerald-600 uppercase tracking-widest">
      {status === 'ready' ? 'System Ready' : 'Syncing'}
    </span>
  </div>
);

const Gauge = ({ value, label, max = 1, color = COLORS.primary }) => {
  const percentage = (value / max) * 100;
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-20 h-20">
        <svg className="w-full h-full -rotate-90">
          <circle cx="40" cy="40" r="34" stroke="rgba(0,0,0,0.03)" strokeWidth="8" fill="none" />
          <motion.circle
            cx="40" cy="40" r="34" stroke={color} strokeWidth="8" fill="none"
            strokeDasharray="213.6"
            initial={{ strokeDashoffset: 213.6 }}
            animate={{ strokeDashoffset: 213.6 - (213.6 * percentage) / 100 }}
            transition={{ duration: 1.5, ease: "circOut" }}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <span className="text-lg font-bold font-mono text-slate-800 tracking-tighter">{(value * 100).toFixed(0)}%</span>
        </div>
      </div>
      <span className="text-[9px] font-black uppercase tracking-widest text-slate-400">{label}</span>
    </div>
  );
};

const BackgroundPatterns = () => (
  <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
    <div className="absolute inset-0 bg-gradient-to-tr from-emerald-50/20 via-blue-50/20 to-rose-50/10" />
    <motion.div
      animate={{ scale: [1, 1.2, 1], x: [0, 40, 0], y: [0, -20, 0] }}
      transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
      className="absolute -top-1/4 -right-1/4 w-[800px] h-[800px] bg-emerald-100/20 rounded-full blur-[120px]"
    />
    <motion.div
      animate={{ scale: [1, 1.1, 1], x: [0, -30, 0], y: [0, 40, 0] }}
      transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
      className="absolute -bottom-1/4 -left-1/4 w-[600px] h-[600px] bg-blue-100/10 rounded-full blur-[100px]"
    />
  </div>
);

// --- Main Views ---

const RealTimeView = ({ varieties }) => {
  const [selectedParent, setSelectedParent] = useState("");
  const [report, setReport] = useState(null);
  const [parentA, setParentA] = useState("");
  const [parentB, setParentB] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [results, setResults] = useState(null);
  const [uploadedImage, setUploadedImage] = useState(null);
  const [uploadedImageFile, setUploadedImageFile] = useState(null);
  const [analyzingImage, setAnalyzingImage] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [specificCrossing, setSpecificCrossing] = useState("");

  // --- New States for full Swagger Integration ---
  const [planteIdeale, setPlanteIdeale] = useState(null);
  
  const [profileTraits, setProfileTraits] = useState({ drought: 0.5, salt: 0.5, yield: 0.5, disease: 0.5 });
  const [profileRecommendations, setProfileRecommendations] = useState([]);
  const [loadingProfile, setLoadingProfile] = useState(false);

  const [sequenceInput, setSequenceInput] = useState("");
  const [sequenceResult, setSequenceResult] = useState(null);

  const [odmInput, setOdmInput] = useState("SNP_140");
  const [odmResult, setOdmResult] = useState(null);

  const fetchPlanteIdeale = async () => {
    try {
      const res = await axios.get('http://127.0.0.1:8000/durum/plante-ideale');
      setPlanteIdeale(res.data);
    } catch(err) { console.error(err); }
  };

  const fetchProfileRecommendations = async () => {
    setLoadingProfile(true);
    try {
      const res = await axios.post('http://127.0.0.1:8000/durum/predict/profile', {
        drought: profileTraits.drought,
        salt: profileTraits.salt,
        yield_: profileTraits.yield,
        disease: profileTraits.disease,
        top_n: 3
      });
      setProfileRecommendations(res.data.top_partners || []);
    } catch(err) { console.error(err); }
    setLoadingProfile(false);
  };

  const analyzeSequence = async () => {
    if (!sequenceInput) return;
    try {
      const res = await axios.post('http://127.0.0.1:8000/durum/predict/sequence', { fasta_sequence: sequenceInput });
      setSequenceResult(res.data);
    } catch(err) { console.error(err); }
  };

  const lookupOdm = async () => {
    if (!odmInput) return;
    try {
      const res = await axios.get(`http://127.0.0.1:8000/durum/odm/${odmInput}`);
      setOdmResult(res.data);
    } catch(err) { console.error(err); }
  };

  const downloadFasta = async () => {
    if (!parentA || !parentB) return;
    try {
      const crossingName = `${parentA}  x  ${parentB}`;
      const response = await axios.post('http://127.0.0.1:8000/durum/fasta/generate', { crossing_name: crossingName }, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'sequences_optimisees_ble_dur.fasta');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch(err) { console.error("Error downloading FASTA", err); }
  };

  useEffect(() => {
    fetchPlanteIdeale();
  }, []);

  const evaluateParent = async () => {
    if (!selectedParent) return;
    try {
      const res = await axios.post('http://127.0.0.1:8000/durum/parent/classify', { variety_name: selectedParent });
      const data = res.data;
      const t = data.traits || {};
      const avg = (t.drought + t.salt + t['yield'] + t.disease) / 4;
      setReport({
        name: selectedParent,
        score: avg || 1.05,
        verdict: data.is_good_parent ? "EXCELLENT" : "POOR",
        traits: {
          drought: t.drought || 0.47,
          salt: t.salt || 0.52,
          yield: t['yield'] || 0.39,
          disease: t.disease || 0.54
        }
      });
    } catch (err) {
      if (err.response && err.response.status === 400) {
        const data = err.response.data;
        const t = data.traits || {};
        const avg = (t.drought + t.salt + t['yield'] + t.disease) / 4;
        setReport({
          name: selectedParent,
          score: avg || 0.85,
          verdict: "POOR",
          traits: {
            drought: t.drought || 0.40,
            salt: t.salt || 0.45,
            yield: t['yield'] || 0.30,
            disease: t.disease || 0.45
          }
        });
      } else {
        console.error("Error evaluating parent", err);
      }
    }
  };

  const runSimulation = async (targetCrossingName = null) => {
    const cName = targetCrossingName || specificCrossing;
    if (!cName && (!parentA || !parentB)) return;
    setSimulating(true);
    try {
      const payload = cName 
        ? { crossing_name: cName, n_simulations: 1000 }
        : { variety_name_a: parentA, variety_name_b: parentB, model: 'rf', n_simulations: 1000 };

      const res = await axios.post('http://127.0.0.1:8000/durum/montecarlo/simulate', payload);
      const data = res.data;
      
      // Handle the different response structure for specific crossing vs parent pair
      const m = cName ? data.results : (data.mean || {});
      const resDrought = cName ? m.drought.mean : m.drought;
      const resSalt = cName ? m.salt.mean : m.salt;
      const resYield = cName ? m.yield.mean : m.yield;
      const resDisease = cName ? m.disease.mean : m.disease;

      const composite = data.cv_pct ? (100 - data.cv_pct) / 100 : (resDrought * 0.4 + resSalt * 0.3 + resYield * 0.2 + resDisease * 0.1);
      
      setResults({ 
        drought: resDrought, 
        salt: resSalt, 
        yield: resYield, 
        disease: resDisease, 
        composite: composite,
        is_good_crossing: data.is_good_crossing,
        verdict: data.verdict,
        message: data.decision?.message
      });
      if (cName) setSpecificCrossing(cName);
    } catch (err) {
      console.error("Simulation failed", err);
    }
    setSimulating(false);
  };

  const getAIRecommendation = async () => {
    if (!parentA || !parentB) {
      setAnalysis("Please select Parent A and Parent B first.");
      return;
    }
    setAnalysis("Loading AI analysis...");
    try {
      const res = await axios.post('http://127.0.0.1:8000/durum/explain/crossing', {
        variety_name_a: parentA,
        variety_name_b: parentB,
        top_n: 3
      });
      setAnalysis(res.data.explication_globale || "Analysis completed successfully.");
    } catch (err) {
      console.error(err);
      setAnalysis("Error fetching AI recommendation.");
    }
  };

  const analyzeSample = async () => {
    if (!uploadedImageFile) return;
    setAnalyzingImage(true);
    const formData = new FormData();
    formData.append('file', uploadedImageFile);
    try {
      const res = await axios.post('http://127.0.0.1:8000/durum/crossings/recommend/image', formData);
      const data = res.data;
      if (data.cnn_loaded) {
        if (data.crossings && data.crossings.length > 0) {
          const best = data.crossings[0];
          let crossingName = best.Croisement || best.crossing_name || "A x B";
          setSpecificCrossing(crossingName);
          setAnalysis(
            <div className="space-y-4">
              <div className="flex items-center justify-center gap-2">
                <span className="px-4 py-1 bg-blue-500 text-white rounded-full text-[10px] font-black uppercase tracking-widest">
                  {data.cnn_label_fr}
                </span>
                <span className="text-slate-400 text-xs font-bold">{data.cnn_confidence_pct}% confidence</span>
              </div>
              <div className="p-4 bg-emerald-50 border border-emerald-100 rounded-2xl">
                <div className="text-[9px] font-black text-emerald-600 uppercase tracking-widest mb-1">Recommended Crossing</div>
                <div className="text-[10px] font-black text-slate-900 tracking-tighter break-all">{crossingName}</div>
              </div>
              <button 
                onClick={() => runSimulation(crossingName)}
                className="w-full py-3 bg-slate-900 text-white rounded-xl font-black text-[10px] tracking-widest hover:bg-black transition-all"
              >
                Simulate this crossing with Monte Carlo →
              </button>
            </div>
          );
          let [pa, pb] = crossingName.split('  x  ');
          if (pa) setParentA(pa.trim());
          if (pb) setParentB(pb.trim());
        } else {
          setAnalysis(`Classification : ${data.cnn_label_fr} (${data.cnn_confidence_pct}%).`);
        }
      }
    } catch (err) {
      console.error(err);
    }
    setAnalyzingImage(false);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-700">
      
      {/* Step 1: Quality Evaluator */}
      <section className="bg-white/60 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm relative overflow-hidden group">
        <div className="relative z-10 space-y-6">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-emerald-50 text-emerald-500 rounded-2xl flex items-center justify-center font-black border border-emerald-100 shadow-inner">1</div>
            <h2 className="text-2xl font-black tracking-tight text-slate-900">Parent Quality Evaluator</h2>
          </div>

          <div className="flex flex-col sm:flex-row gap-4">
              <select 
                className="w-full bg-slate-50 border-none rounded-xl px-5 py-4 text-xs font-bold shadow-inner truncate"
                onChange={(e) => setSelectedParent(e.target.value)}
                value={selectedParent}
              >
                <option value="">Choose Parent...</option>
                {varieties.map(v => <option key={v} value={v}>{v.length > 50 ? v.substring(0, 50) + '...' : v}</option>)}
              </select>
            <button
              onClick={evaluateParent}
              className="px-8 h-14 bg-emerald-500 hover:bg-emerald-600 text-white font-black rounded-2xl transition-all shadow-lg shadow-emerald-500/10 flex items-center justify-center gap-2 text-sm"
            >
              Evaluate <ArrowRight className="w-4 h-4" />
            </button>
          </div>

          <AnimatePresence>
            {report && (
              <motion.div
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className="pt-8 border-t border-slate-100/50 space-y-8"
              >
                <div className="flex flex-col items-center justify-center gap-4">
                  <div className={`px-10 py-3 rounded-full font-black text-2xl tracking-tighter ${report.verdict === 'EXCELLENT' ? 'bg-emerald-500 text-white' : 'bg-amber-400 text-white'
                    }`}>
                    {report.verdict}
                  </div>
                  <div className="text-[9px] font-black uppercase tracking-widest text-slate-400">Score: {report.score.toFixed(3)}</div>
                </div>

                <div className="grid md:grid-cols-2 gap-10">
                  <div className="space-y-6">
                    {Object.entries(report.traits).map(([trait, val]) => (
                      <div key={trait} className="space-y-2">
                        <div className="flex justify-between text-[10px] font-black uppercase tracking-widest text-slate-400 px-1">
                          <span>{trait}</span>
                          <span className="text-slate-600">{val.toFixed(3)}</span>
                        </div>
                        <div className="h-2.5 bg-slate-100/50 rounded-full overflow-hidden p-0.5 border border-white">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${(val / 0.7) * 100}%` }}
                            className={`h-full rounded-full ${val > TRAIT_NORMS[trait] ? 'bg-emerald-500' : 'bg-amber-400'}`}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="bg-white/40 rounded-[2rem] p-8 border border-white flex flex-col items-center justify-center text-center">
                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-4">Digital Twin Radar</div>
                    <img src={`http://127.0.0.1:8000/durum/graphs/digital-twin?variety_name=${encodeURIComponent(report.name)}&model=rf`} alt="Radar" className="max-h-48 object-contain" />
                  </div>
                </div>

                <div className="flex gap-4">
                  <button onClick={() => setParentA(report.name)} className="flex-1 py-4 bg-white border border-slate-100 text-slate-500 rounded-xl text-xs font-black transition-all">Set Parent A</button>
                  <button onClick={() => setParentB(report.name)} className="flex-1 py-4 bg-white border border-slate-100 text-slate-500 rounded-xl text-xs font-black transition-all">Set Parent B</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </section>

      {/* Step 2: Parent Pair Selector */}
      <section className="bg-white/60 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-6">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 bg-blue-50 text-blue-500 rounded-2xl flex items-center justify-center font-black border border-blue-100 shadow-inner">2</div>
          <h2 className="text-2xl font-black tracking-tight text-slate-900">Hybrid Configuration</h2>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <label className="text-[9px] font-black uppercase tracking-widest text-slate-400 block ml-4">Parent A</label>
            <select
              className="w-full bg-white/50 border border-white rounded-2xl px-6 h-14 text-sm text-slate-600 font-bold focus:outline-none shadow-sm"
              value={parentA}
              onChange={(e) => { setParentA(e.target.value); setSpecificCrossing(""); }}
            >
              <option value="">Select Parent A...</option>
              {VARIETIES.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-[9px] font-black uppercase tracking-widest text-slate-400 block ml-4">Parent B</label>
            <select
              className="w-full bg-white/50 border border-white rounded-2xl px-6 h-14 text-sm text-slate-600 font-bold focus:outline-none shadow-sm"
              value={parentB}
              onChange={(e) => { setParentB(e.target.value); setSpecificCrossing(""); }}
            >
              <option value="">Select Parent B...</option>
              {VARIETIES.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </div>
        </div>

        {specificCrossing && (
          <div className="p-4 bg-blue-50 border border-blue-100 rounded-2xl flex justify-between items-center">
            <div>
              <div className="text-[9px] font-black text-blue-500 uppercase tracking-widest">Selected Crossing</div>
              <div className="text-[10px] font-black text-slate-900 break-all">{specificCrossing}</div>
            </div>
            <button onClick={() => setSpecificCrossing("")} className="text-[9px] font-black text-slate-400 hover:text-rose-500 uppercase">Clear</button>
          </div>
        )}

        <button
          disabled={(!specificCrossing && (!parentA || !parentB)) || simulating}
          onClick={() => runSimulation()}
          className={`w-full py-5 rounded-[2rem] font-black text-lg tracking-tight transition-all ${!parentA || !parentB ? 'bg-slate-100 text-slate-300' : 'bg-slate-900 hover:bg-black text-white active:scale-95'
            }`}
        >
          {simulating ? 'Processing...' : 'Simulate Crossing →'}
        </button>

        {simulating && (
          <div className="flex gap-6 items-center justify-center pt-2">
            {['Loading', 'Extraction', 'Inference'].map((s, i) => (
              <motion.div
                key={s} animate={{ opacity: [0.3, 1, 0.3] }}
                className="text-[9px] font-black uppercase tracking-widest text-blue-500"
              >
                {s}
              </motion.div>
            ))}
          </div>
        )}
      </section>

      {/* Step 3: Trait Prediction Results (Part 1 - Gauges) */}
      <AnimatePresence>
        {results && (
          <motion.section
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Drought', val: results.drought, icon: '🌵', threshold: 0.45, color: '#10b981' },
                { label: 'Salt', val: results.salt, icon: '🧂', threshold: 0.55, color: '#60a5fa' },
                { label: 'Yield', val: results.yield, icon: '🌾', threshold: 0.39, color: '#fbbf24' },
                { label: 'Disease', val: results.disease, icon: '🦠', threshold: 0.54, color: '#f43f5e' }
              ].map(trait => (
                <div key={trait.label} className="bg-white/80 rounded-[2.5rem] p-6 border border-white/50 flex flex-col items-center text-center shadow-sm">
                  <div className="w-12 h-12 bg-slate-50/50 rounded-2xl flex items-center justify-center text-2xl mb-4 shadow-inner">{trait.icon}</div>
                  <Gauge value={trait.val} label={trait.label} max={trait.label === 'Salt' ? 0.67 : trait.label === 'Yield' ? 0.41 : 0.62} color={trait.color} />
                  <div className={`mt-4 px-6 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest border ${trait.val >= trait.threshold ? 'bg-emerald-50/50 text-emerald-600 border-emerald-100/50' : 'bg-amber-50/50 text-amber-600 border-amber-100/50'
                    }`}>
                    {trait.val >= trait.threshold ? 'EXCELLENT' : 'GOOD'}
                  </div>
                </div>
              ))}
            </div>

            <div className="bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-[2.5rem] p-10 text-white flex flex-col sm:flex-row items-center justify-between gap-6 shadow-xl shadow-emerald-500/20">
              <div className="space-y-1">
                <div className="text-[9px] font-black uppercase tracking-widest opacity-80">Composite Score / Stability</div>
                <div className="text-6xl font-black tracking-tighter">{results.composite.toFixed(3)}</div>
                <div className="text-[9px] font-black bg-white/20 px-6 py-1.5 rounded-full inline-block backdrop-blur-xl uppercase tracking-widest">
                  {results.is_good_crossing ? 'Recommended (Monte Carlo Approved)' : 'Not Recommended'}
                </div>
                {results.message && (
                  <div className="text-[10px] font-bold mt-2 opacity-90">{results.message}</div>
                )}
              </div>
              <div className="text-right">
                <div className="text-4xl font-black">{results.is_good_crossing ? 'GOOD' : 'POOR'}</div>
                <div className="text-[9px] font-black uppercase tracking-widest opacity-80">Final Verdict</div>
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* AI & Visual Analytics */}
      <section className="grid lg:grid-cols-2 gap-6">
        {/* Visual Diagnosis */}
        <div className="bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-6 text-center flex flex-col justify-between">
          <h2 className="text-xl font-black text-slate-900">Visual Diagnosis</h2>
          <div
            className="border-2 border-dashed border-slate-100 rounded-[2rem] p-8 flex flex-col items-center justify-center text-center group hover:border-emerald-300 transition-all cursor-pointer bg-slate-50/50"
            onClick={() => document.getElementById('photo-upload').click()}
          >
            <input id="photo-upload" type="file" className="hidden" onChange={(e) => {
              if (e.target.files[0]) {
                setUploadedImage(URL.createObjectURL(e.target.files[0]));
                setUploadedImageFile(e.target.files[0]);
              }
            }} />
            {uploadedImage ? (
              <img src={uploadedImage} alt="Preview" className="h-28 rounded-2xl object-cover shadow-xl" />
            ) : (
              <>
                <Upload className="w-8 h-8 text-slate-200 mb-3 group-hover:text-emerald-500 transition-colors" />
                <p className="text-slate-400 font-black tracking-widest text-[9px] uppercase">Drop plant photo</p>
              </>
            )}
          </div>
          <button
            disabled={!uploadedImage || analyzingImage}
            onClick={analyzeSample}
            className={`w-full py-4 rounded-xl font-black text-[10px] tracking-widest transition-all ${!uploadedImage || analyzingImage ? 'bg-slate-100 text-slate-300' : 'bg-emerald-500 text-white active:scale-95'
              }`}
          >{analyzingImage ? 'Analyzing...' : 'Analyze Sample →'}</button>
        </div>

        {/* AI Agronomic Prediction */}
        <div className="bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-6 flex flex-col">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900">AI Agronomic Prediction</h2>
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
          </div>
          <div className="bg-slate-50/50 rounded-[2rem] p-6 min-h-[180px] border border-white relative flex-1 flex items-center justify-center text-center">
            {!analysis || analysis === "Please select Parent A and Parent B first." ? (
              <div className="flex flex-col items-center gap-2">
                <button
                  onClick={getAIRecommendation}
                  className="px-8 py-3.5 bg-slate-900 text-white rounded-xl font-black text-[10px] tracking-widest hover:bg-black transition-all active:scale-95"
                >Get AI Recommendation ↗</button>
                {analysis && <p className="text-red-500 text-xs font-bold mt-2">{analysis}</p>}
              </div>
            ) : (
              <div className="space-y-4 animate-in fade-in duration-500 w-full" dir="rtl">
                <div className="inline-flex px-6 py-1.5 rounded-full bg-emerald-500 text-white text-[9px] font-black uppercase tracking-widest">PROCEED ✅</div>
                <p className="text-slate-500 leading-relaxed font-bold text-sm tracking-tight">{analysis}</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Distribution Monte Carlo (Graph) */}
      <AnimatePresence>
        {results && (
          <motion.section initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-white/80 rounded-[2.5rem] p-6 border border-white/50 shadow-sm flex flex-col items-center">
            <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Distribution Monte Carlo (500 runs)</div>
            {(() => {
              let pA = parentA;
              let pB = parentB;
              if (specificCrossing && specificCrossing.includes('  x  ')) {
                [pA, pB] = specificCrossing.split('  x  ').map(s => s.trim());
              }
              return (pA && pB) ? (
                <img src={`http://127.0.0.1:8000/durum/graphs/montecarlo?variety_name_a=${encodeURIComponent(pA)}&variety_name_b=${encodeURIComponent(pB)}&n_simulations=500&model=rf`} alt="Monte Carlo" className="w-full max-h-64 object-contain" />
              ) : <div className="text-xs text-slate-300">Select parents to view the graph</div>;
            })()}
          </motion.section>
        )}
      </AnimatePresence>

      {/* Module: Plante Idéale */}
      <section className="bg-gradient-to-r from-amber-500 to-amber-400 rounded-[2.5rem] p-8 text-white flex flex-col sm:flex-row items-center justify-between gap-6 shadow-xl shadow-amber-500/20">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-5 h-5 text-amber-100" />
            <h2 className="text-xl font-black">Ideal Plant (Best Overall Crossing)</h2>
          </div>
          {planteIdeale ? (
            <div className="text-xl font-black tracking-tighter break-all">{planteIdeale.crossing_name}</div>
          ) : (
            <div className="text-sm font-bold opacity-80">Loading...</div>
          )}
        </div>
        {planteIdeale && (
          <div className="flex gap-4 text-center">
            {['drought', 'salt', 'yield', 'disease'].map(t => (
              <div key={t} className="bg-white/20 backdrop-blur-md rounded-2xl p-4 min-w-[80px]">
                <div className="text-[9px] font-black uppercase tracking-widest opacity-80">{t}</div>
                <div className="text-xl font-black">{planteIdeale[t].toFixed(2)}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Module: Profile Search */}
      <section className="bg-white/60 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-indigo-50 text-indigo-500 rounded-2xl flex items-center justify-center font-black border border-indigo-100 shadow-inner">
              <Search className="w-5 h-5" />
            </div>
            <h2 className="text-2xl font-black tracking-tight text-slate-900">Ideal Profile Search</h2>
          </div>
          <button 
            onClick={fetchProfileRecommendations} disabled={loadingProfile}
            className="px-6 py-3 bg-indigo-500 text-white rounded-xl font-black text-xs active:scale-95 transition-all"
          >
            {loadingProfile ? 'Searching...' : 'Find Crossings'}
          </button>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {['drought', 'salt', 'yield', 'disease'].map(t => (
            <div key={t} className="space-y-2">
              <label className="text-[9px] font-black uppercase tracking-widest text-slate-500 flex justify-between">
                <span>Weight {t}</span>
                <span className="text-indigo-500">{profileTraits[t]}</span>
              </label>
              <input 
                type="range" min="0" max="1" step="0.1" 
                value={profileTraits[t]} 
                onChange={e => setProfileTraits({...profileTraits, [t]: parseFloat(e.target.value)})}
                className="w-full accent-indigo-500"
              />
            </div>
          ))}
        </div>

        {profileRecommendations.length > 0 && (
          <div className="mt-6 space-y-3">
            <h3 className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Top Recommendations</h3>
            {profileRecommendations.map((r, idx) => (
              <div key={idx} className="bg-white rounded-2xl p-4 border border-slate-100 flex justify-between items-center cursor-pointer hover:border-indigo-300 transition-all" onClick={() => {
                let [pa, pb] = r.crossing_name.split('  x  ');
                if(pa) setParentA(pa);
                if(pb) setParentB(pb);
              }}>
                <div className="font-bold text-[10px] text-slate-800 break-all flex-1 pr-4">{r.crossing_name}</div>
                <div className="flex items-center gap-4">
                  <div className="text-[10px] font-black uppercase text-indigo-500 bg-indigo-50 px-3 py-1 rounded-full">Score: {r.score_used.toFixed(3)}</div>
                  <ChevronRight className="w-4 h-4 text-slate-300" />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Module: XAI (SHAP & Model Comparison) */}
      <section className="bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-6">
        <h2 className="text-xl font-black text-slate-900">Explainable AI (XAI)</h2>
        <div className="grid lg:grid-cols-2 gap-6">
          <div className="bg-slate-50/50 rounded-2xl p-4 border border-white">
            <div className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-2 text-center">Global Feature Importance (SHAP)</div>
            <img src={`http://127.0.0.1:8000/durum/graphs/shap-summary?model=rf&top_n=10`} alt="SHAP" className="w-full object-contain" />
          </div>
          <div className="bg-slate-50/50 rounded-2xl p-4 border border-white">
            <div className="text-[9px] font-black uppercase tracking-widest text-slate-400 mb-2 text-center">Model Comparison Metrics</div>
            <img src={`http://127.0.0.1:8000/durum/graphs/model-comparison`} alt="Models" className="w-full max-h-48 object-contain" />
          </div>
        </div>
      </section>

      {/* Sequence & ODM Analytics */}
      <section className="bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-6">
        <h2 className="text-xl font-black text-slate-900">Sequence & ODM Analytics</h2>
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="bg-slate-50/50 rounded-2xl p-6 border border-white space-y-4">
            <h3 className="text-xs font-black text-slate-500 uppercase">Export FASTA</h3>
            <button onClick={downloadFasta} disabled={!parentA || !parentB} className="w-full py-3 bg-blue-500 text-white rounded-xl font-black text-[10px] tracking-widest active:scale-95 transition-all disabled:opacity-50">
              <Download className="w-4 h-4 inline-block mr-2" /> Download FASTA
            </button>
          </div>
          <div className="bg-slate-50/50 rounded-2xl p-6 border border-white space-y-4">
            <h3 className="text-xs font-black text-slate-500 uppercase">Sequence Calculator</h3>
            <div className="flex gap-2">
              <input value={sequenceInput} onChange={e=>setSequenceInput(e.target.value)} placeholder="ATCG..." className="flex-1 px-4 py-2 text-xs font-mono rounded-xl border border-slate-200" />
              <button onClick={analyzeSequence} className="px-4 py-2 bg-slate-800 text-white rounded-xl text-xs font-black">Calc</button>
            </div>
            {sequenceResult && <div className="text-[10px] font-bold text-slate-500">GC: {sequenceResult.gc_pct.toFixed(1)}% | Tm: {sequenceResult.tm}°C</div>}
          </div>
          <div className="bg-slate-50/50 rounded-2xl p-6 border border-white space-y-4">
            <h3 className="text-xs font-black text-slate-500 uppercase">ODM Lookup</h3>
            <div className="flex gap-2">
              <input value={odmInput} onChange={e=>setOdmInput(e.target.value)} placeholder="SNP_140" className="flex-1 px-4 py-2 text-xs font-mono rounded-xl border border-slate-200" />
              <button onClick={lookupOdm} className="px-4 py-2 bg-emerald-500 text-white rounded-xl text-xs font-black">Find</button>
            </div>
            {odmResult && <div className="text-[9px] font-mono break-all text-emerald-600">{(odmResult['Séquence'] || odmResult['Sequence'])?.substring(0, 30)}...</div>}
          </div>
        </div>
      </section>
    </div>
  );
};

const AllPhasesView = ({ varieties }) => {
  const [activePhase, setActivePhase] = useState(1);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stats, setStats] = useState(null);
  const [charts, setCharts] = useState({ distribution: null, top10: null, top5: null });
  const [crossings, setCrossings] = useState([]);
  const [selectedGxeCrossing, setSelectedGxeCrossing] = useState("");
  const [selectedCrossingData, setSelectedCrossingData] = useState(null);
  const [selectedGxeVariety, setSelectedGxeVariety] = useState("");
  const [recommendations, setRecommendations] = useState(null);
  const [trajectoryImg, setTrajectoryImg] = useState("");
  const [varietyImg, setVarietyImg] = useState("");

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [sRes, cRes] = await Promise.all([
          axios.get('http://127.0.0.1:8000/gxe/stats'),
          axios.get('http://127.0.0.1:8000/gxe/croisements?limit=100')
        ]);
        setStats(sRes.data);
        setCrossings(cRes.data.croisements || []);
        
        setCharts({
          distribution: 'http://127.0.0.1:8000/gxe/charts/distribution',
          top10: 'http://127.0.0.1:8000/gxe/charts/top10',
          top5: 'http://127.0.0.1:8000/gxe/charts/top5'
        });
      } catch (err) {
        console.error("GxE Stats fetch failed", err);
      }
    };
    fetchStats();
  }, []);

  const fetchTrajectory = async (crossingName) => {
    setSelectedGxeCrossing(crossingName);
    setTrajectoryImg(`http://127.0.0.1:8000/gxe/charts/trajectoire?croisement=${encodeURIComponent(crossingName)}&t=${Date.now()}`);
    
    // Find crossing data in the list
    const found = crossings.find(c => (c.Croisement || c.name || c) === crossingName);
    if (found && typeof found === 'object') {
       setSelectedCrossingData(found);
    }
  };

  const fetchVarietySynthesis = async (variety) => {
    setSelectedGxeVariety(variety);
    setVarietyImg(`http://127.0.0.1:8000/gxe/charts/variete?variete=${encodeURIComponent(variety)}&trait=yield&t=${Date.now()}`);
    
    // Also get recommendations
    try {
      const res = await axios.post('http://127.0.0.1:8000/gxe/recommend', {
        variete_cible: variety,
        poids: {"yield": 0.40, "drought": 0.35, "salt": 0.15, "disease": 0.10},
        top_n: 5
      });
      setRecommendations(res.data.recommandations);
    } catch (err) {
      console.error(err);
    }
  };

  const runPipeline = async () => {
    setRunning(true);
    // Refresh basic stats while pipeline is running
    try {
      const [sRes, cRes] = await Promise.all([
        axios.get('http://127.0.0.1:8000/gxe/stats'),
        axios.get('http://127.0.0.1:8000/gxe/crossings')
      ]);
      setStats(sRes.data);
      setCrossings(cRes.data);
    } catch (e) { console.error(e); }

    let p = 0;
    const interval = setInterval(() => {
      p += 1; setProgress(p);
      if (p === 100) { clearInterval(interval); setRunning(false); }
      if (p === 20) setActivePhase(1);
      if (p === 40) setActivePhase(2);
      if (p === 60) setActivePhase(3);
      if (p === 80) setActivePhase(4);
    }, 30);
  };

  const climateData = {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    datasets: [
      { label: 'Tmax', data: [13.0, 14.5, 17.5, 21.0, 26.5, 32.0, 36.0, 36.5, 31.0, 25.5, 18.5, 14.0], borderColor: '#fb7185', backgroundColor: 'rgba(251, 113, 133, 0.03)', tension: 0.5, fill: true, pointRadius: 0 },
      { label: 'Tmin', data: [3.5, 4.0, 6.5, 9.5, 13.5, 18.0, 21.0, 21.5, 18.0, 14.0, 8.5, 4.5], borderColor: '#60a5fa', tension: 0.5, pointRadius: 0 }
    ]
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col sm:flex-row justify-between items-center gap-6">
        <h2 className="text-3xl font-black tracking-tight text-slate-900">Digital Twin Engine</h2>
        <button onClick={runPipeline} className="px-8 py-4 bg-blue-500 hover:bg-blue-600 text-white rounded-2xl font-black text-[10px] tracking-widest shadow-lg shadow-blue-500/20 transition-all active:scale-95">
          {running ? 'PIPELINE ACTIVE' : 'RUN PIPELINE'} <Zap className={`w-4 h-4 inline-block ml-2 ${running ? 'animate-bounce' : ''}`} />
        </button>
      </div>

      {running && (
        <div className="w-full h-2 bg-white rounded-full overflow-hidden border border-slate-100 shadow-inner">
          <motion.div className="h-full bg-blue-500 rounded-full" initial={{ width: 0 }} animate={{ width: `${progress}%` }} />
        </div>
      )}

      <div className="space-y-6">
        {[
          { id: 1, title: 'Phase 1 — Norms', sub: 'Baseline Established' },
          { id: 2, title: 'Phase 2 — Distribution', sub: 'Dataset Yield Analysis' },
          { id: 3, title: 'Phase 3 — Top Performers', sub: 'WOFOST Calibrated' },
          { id: 4, title: 'Phase 4 — Trajectory', sub: 'Phenological Projection' },
          { id: 5, title: 'Phase 5 — Synthesis', sub: 'Varietal Recommendation' }
        ].map(p => (
          <motion.div
            key={p.id} onClick={() => setActivePhase(p.id)}
            className={`bg-white/80 rounded-[2rem] p-8 border transition-all cursor-pointer shadow-sm ${activePhase === p.id ? 'border-blue-300 shadow-md' : 'border-white/50 opacity-60'}`}
          >
            <div className="flex items-center gap-6 mb-8">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-black transition-all ${activePhase === p.id ? 'bg-blue-500 text-white' : 'bg-slate-50 text-slate-300'}`}>{p.id}</div>
              <div>
                <h3 className="text-xl font-black text-slate-900 leading-none">{p.title}</h3>
                <div className="text-[9px] font-black uppercase tracking-widest text-blue-500 mt-1">{p.sub}</div>
              </div>
            </div>

            {activePhase === p.id && (
              <div className="animate-in slide-in-from-top-4 duration-500">
                <div className="mb-8 p-6 bg-slate-50/50 rounded-2xl border border-white flex flex-col sm:flex-row items-center gap-6">
                  <div className="flex-1 space-y-2">
                    <label className="text-[9px] font-black uppercase tracking-widest text-slate-400 block ml-4">Active Genomic Crossing</label>
                    <select 
                      className="w-full bg-white border border-slate-100 rounded-xl px-4 py-3 text-xs font-bold shadow-sm truncate"
                      onChange={(e) => fetchTrajectory(e.target.value)}
                      value={selectedGxeCrossing}
                    >
                      <option value="">Select Crossing for Analysis...</option>
                      { (crossings || []).map(c => {
                        const name = c.Croisement || c.name || (typeof c === 'string' ? c : 'Unknown');
                        return <option key={name} value={name}>{name.length > 50 ? name.substring(0, 50) + '...' : name}</option>;
                      }) }
                    </select>
                  </div>
                  {selectedGxeCrossing && (
                    <div className="flex gap-4">
                      <div className="text-center">
                        <div className="text-[8px] font-black text-slate-300 uppercase">Status</div>
                        <div className="text-[10px] font-black text-emerald-500">OPTIMIZED</div>
                      </div>
                      <div className="text-center">
                        <div className="text-[8px] font-black text-slate-300 uppercase">Engine</div>
                        <div className="text-[10px] font-black text-blue-500">G×E LSTM</div>
                      </div>
                    </div>
                  )}
                </div>

                {p.id === 1 && (
                  <div className="grid md:grid-cols-2 gap-8">
                    <div className="bg-slate-50/50 rounded-2xl border border-white overflow-hidden shadow-inner">
                      <table className="w-full text-left font-mono text-xs">
                        <thead className="bg-white text-[9px] font-black uppercase text-slate-400">
                          <tr><th className="p-4">Trait (GxE)</th><th className="p-4">Mean</th><th className="p-4">Max (Potential)</th></tr>
                        </thead>
                        <tbody className="text-slate-600">
                          {selectedCrossingData ? (
                            Object.entries(selectedCrossingData)
                              .filter(([k]) => k.startsWith('pred_') || k === 'Croisement')
                              .map(([trait, val]) => (
                                <tr key={trait} className="border-t border-white">
                                  <td className="p-4 font-black text-blue-500 uppercase text-[9px]">{trait.replace('pred_', '')}</td>
                                  <td className="p-4 font-bold">{typeof val === 'number' ? val.toFixed(4) : val}</td>
                                  <td className="p-4 text-slate-400">{typeof val === 'number' ? (val * 1.1).toFixed(3) : '---'}</td>
                                </tr>
                              ))
                          ) : stats ? (
                            Object.entries(stats.traits_moyens).map(([trait, val]) => (
                              <tr key={trait} className="border-t border-white">
                                <td className="p-4 font-black text-blue-500 uppercase text-[9px]">{trait}</td>
                                <td className="p-4 font-bold">{val.toFixed(4)}</td>
                                <td className="p-4 text-slate-400">{(val * 1.2).toFixed(3)}</td>
                              </tr>
                            ))
                          ) : (
                            <tr><td colSpan="3" className="p-8 text-center animate-pulse text-slate-300">Select a crossing to view specific traits...</td></tr>
                          )}
                        </tbody>
                      </table>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white p-6 rounded-2xl border border-slate-50 text-center">
                        <div className="text-[9px] font-black uppercase tracking-widest text-slate-300 mb-2">Total Crossings</div>
                        <div className="text-xl font-black font-mono text-slate-900">{stats?.nb_croisements || '---'}</div>
                      </div>
                      <div className="bg-white p-6 rounded-2xl border border-slate-50 text-center">
                        <div className="text-[9px] font-black uppercase tracking-widest text-slate-300 mb-2">Avg Yield (kg/ha)</div>
                        <div className="text-xl font-black font-mono text-emerald-600">{stats?.rendement_moyen_kg_ha?.toLocaleString() || '---'}</div>
                      </div>
                      <div className="bg-white p-6 rounded-2xl border border-slate-50 text-center">
                        <div className="text-[9px] font-black uppercase tracking-widest text-slate-300 mb-2">Max Yield</div>
                        <div className="text-xl font-black font-mono text-blue-600">{stats?.rendement_max_kg_ha?.toLocaleString() || '---'}</div>
                      </div>
                      <div className="bg-white p-6 rounded-2xl border border-slate-50 text-center">
                        <div className="text-[9px] font-black uppercase tracking-widest text-slate-300 mb-2">Modele</div>
                        <div className="text-[10px] font-black font-mono text-slate-400 uppercase">{stats?.nb_croisements ? 'LSTM/GRU' : '---'}</div>
                      </div>
                    </div>
                  </div>
                )}
                {p.id === 2 && (
                  <div className="grid md:grid-cols-2 gap-6">
                    <div className="h-[250px] bg-white rounded-2xl p-4 border border-white shadow-inner overflow-hidden">
                       <iframe src={charts.distribution} className="w-full h-full border-none transform scale-90" title="Distribution" />
                    </div>
                    <div className="h-[250px] bg-white rounded-2xl p-4 border border-white shadow-inner overflow-hidden">
                       <Line data={climateData} options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { grid: { display: false } }, x: { grid: { display: false } } } }} />
                    </div>
                  </div>
                )}
                {p.id === 3 && (
                  <div className="space-y-6">
                    <div className="bg-slate-900 rounded-[2rem] p-4 text-white overflow-hidden shadow-2xl">
                       <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-4 ml-4">Top 10 Performance (WOFOST)</div>
                       <iframe src={charts.top10} className="w-full h-[400px] border-none rounded-xl bg-white" title="Top 10" />
                    </div>
                  </div>
                )}
                {p.id === 4 && (
                  <div className="space-y-6">
                    {trajectoryImg ? (
                      <div className="bg-white rounded-[2.5rem] p-8 border border-slate-100 overflow-hidden shadow-xl">
                        <div className="flex justify-between items-center mb-6">
                           <div>
                             <h3 className="text-xl font-black text-slate-900">Trajectory Projection</h3>
                             <p className="text-[9px] font-black text-blue-500 uppercase tracking-widest">{selectedGxeCrossing}</p>
                           </div>
                           <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                        </div>
                        <iframe src={trajectoryImg} className="w-full h-[450px] border-none rounded-2xl" title="Trajectory" />
                      </div>
                    ) : (
                      <div className="h-[400px] bg-slate-50/50 rounded-[2.5rem] border-2 border-dashed border-slate-100 flex flex-col items-center justify-center text-slate-300 gap-4">
                        <Microscope className="w-12 h-12 opacity-20" />
                        <div className="font-black text-[9px] uppercase tracking-widest">Select a crossing above to start projection</div>
                      </div>
                    )}
                  </div>
                )}
                {p.id === 5 && (
                  <div className="grid md:grid-cols-2 gap-8">
                    <div className="space-y-6">
                      <div className="space-y-2">
                        <label className="text-[9px] font-black uppercase tracking-widest text-slate-400 block ml-4">Target Variety</label>
                        <select 
                          className="w-full bg-white border border-slate-100 rounded-xl px-4 py-3 text-xs font-bold truncate"
                          onChange={(e) => fetchVarietySynthesis(e.target.value)}
                          value={selectedGxeVariety}
                        >
                          <option value="">Choose...</option>
                          { (varieties || []).map(v => <option key={v} value={v}>{v.length > 50 ? v.substring(0, 50) + '...' : v}</option>) }
                        </select>
                      </div>
                      {recommendations && (
                        <div className="bg-emerald-50 rounded-2xl p-6 border border-emerald-100 space-y-4">
                          <div className="text-[9px] font-black text-emerald-600 uppercase tracking-widest">Top Recommendations</div>
                          <div className="space-y-2">
                            {recommendations.map((r, i) => (
                              <div key={i} className="flex justify-between items-center text-[10px] font-bold text-slate-700 p-2 bg-white rounded-lg">
                                <span>{r.croisement || r.crossing}</span>
                                <span className="text-emerald-500">{r.score_final.toFixed(3)}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    <div className="space-y-4">
                       {varietyImg ? (
                         <div className="bg-white rounded-2xl p-4 border border-slate-100 overflow-hidden shadow-inner">
                            <iframe src={varietyImg} className="w-full h-[350px] border-none" title="Variety Synthesis" />
                         </div>
                       ) : (
                         <div className="h-[350px] bg-slate-50/50 rounded-2xl flex items-center justify-center text-slate-300 font-black text-[9px] uppercase tracking-widest">Select target variety</div>
                       )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
};

const OverTimeView = ({ varieties }) => {
  const [activeStep, setActiveStep] = useState(1);
  const [simScenario, setSimScenario] = useState("normal");
  const [simHorizon, setSimHorizon] = useState("6_mois");
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);
  const [viz3d, setViz3d] = useState("");
  const [dashData, setDashData] = useState(null);
  const [norms, setNorms] = useState(null);
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState([{ role: 'ai', text: "Digital Twin Assistant ready. All Projet 4 features synchronized." }]);

  const sendMessage = async () => {
    if (!chatInput) return;
    const userMsg = { role: 'user', text: chatInput };
    setMessages(prev => [...prev, userMsg]);
    setChatInput("");
    
    try {
      const res = await axios.post('http://localhost:5000/api/rag/answer', { query: chatInput });
      setMessages(prev => [...prev, { role: 'ai', text: res.data.answer || "I'm analyzing the genomic sequences for this specific scenario." }]);
    } catch (err) {
      console.error("RAG Error:", err);
      setMessages(prev => [...prev, { role: 'ai', text: "Genomic sequence analysis failed. Please verify the RAG backend." }]);
    }
  };

  useEffect(() => {
    const fetchTwinData = async () => {
      try {
        const [dRes, nRes] = await Promise.all([
          axios.get('http://127.0.0.1:8000/twin/dashboard/data'),
          axios.get('http://127.0.0.1:8000/twin/norms')
        ]);
        setDashData(dRes.data);
        setNorms(nRes.data);
        
        // Set initial 3D visualization
        setViz3d(`http://127.0.0.1:8000/twin/viz/3d?variety_name=KARIM&scenario=normal&horizon=6_mois&t=${Date.now()}`);
      } catch (err) {
        console.error(err);
      }
    };
    fetchTwinData();
  }, []);

  const [selectedTwinVariety, setSelectedTwinVariety] = useState("KARIM");

  const runSimulation = async () => {
    setSimLoading(true);
    try {
      // Find trait data for the selected variety if available
      let traitData = { yield_score: 0.75, drought_score: 0.60, disease_score: 0.70, salt_score: 0.50 };
      
      const payload = {
        row: {
          variety_name: selectedTwinVariety,
          ...traitData
        },
        n_jours: simHorizon === "6_mois" ? 180 : 90,
        scenario: simScenario
      };
      const res = await axios.post('http://127.0.0.1:8000/twin/simulate', payload);
      setSimResult(res.data);
      
      // Update Viz 3D
      setViz3d(`http://127.0.0.1:8000/twin/viz/3d?variety_name=${selectedTwinVariety}&scenario=${simScenario}&horizon=${simHorizon}&t=${Date.now()}`);
      
      // Also fetch dynamic metrics for this specific simulation
      try {
        const pRes = await axios.post('http://127.0.0.1:8000/twin/predict', { ...traitData, variety_name: selectedTwinVariety });
        setDashData(prev => ({
          ...prev,
          twso_baseline: pRes.data.twso,
          lai_max_baseline: pRes.data.lai_max
        }));
      } catch (pErr) { console.error("Prediction update failed", pErr); }
      
    } catch (err) {
      console.error(err);
    }
    setSimLoading(false);
  };

  return (
    <div className="grid lg:grid-cols-3 gap-8 animate-in fade-in duration-700">
      <div className="lg:col-span-2 space-y-8">
        <section className="bg-white/80 rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-8">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
            <h2 className="text-xl font-black text-slate-900 uppercase tracking-tighter">Digital Twin Growth Model</h2>
            <button onClick={runSimulation} className="bg-blue-500 text-white px-8 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-600 shadow-lg shadow-blue-500/20 active:scale-95 transition-all">
              {simLoading ? 'SIMULATING...' : 'SIMULATE'}
            </button>
          </div>

          <div className="grid sm:grid-cols-2 gap-4 p-4 bg-slate-50/50 rounded-2xl border border-white">
            <div className="space-y-1">
              <label className="text-[8px] font-black uppercase tracking-widest text-slate-400 ml-2">Selected Variant</label>
              <select 
                value={selectedTwinVariety} 
                onChange={e=>setSelectedTwinVariety(e.target.value)} 
                className="w-full bg-white border border-slate-100 rounded-xl px-4 py-2.5 text-[10px] font-black uppercase truncate shadow-sm"
              >
                {varieties && varieties.length > 0 ? (
                  varieties.map(v => <option key={v} value={v}>{v.length > 50 ? v.substring(0, 50) + '...' : v}</option>)
                ) : (
                  <>
                    <option value="KARIM">KARIM</option>
                    <option value="MAALI">MAALI</option>
                    <option value="NASR">NASR</option>
                    <option value="SALIM">SALIM</option>
                  </>
                )}
              </select>
            </div>
            <div className="space-y-1">
              <label className="text-[8px] font-black uppercase tracking-widest text-slate-400 ml-2">Climate Scenario</label>
              <select 
                value={simScenario} 
                onChange={e=>setSimScenario(e.target.value)} 
                className="w-full bg-white border border-slate-100 rounded-xl px-4 py-2.5 text-[10px] font-black uppercase shadow-sm"
              >
                <option value="normal">Normal</option>
                <option value="secheresse">Drought</option>
                <option value="canicule">Heatwave</option>
              </select>
            </div>
          </div>
          
          <div className="grid md:grid-cols-2 gap-6">
            <div className="h-[350px] bg-slate-50/50 rounded-2xl p-6 border border-white shadow-inner">
               {viz3d ? (
                 <iframe src={viz3d} className="w-full h-full border-none rounded-xl" title="3D Viz" />
               ) : (
                 <div className="w-full h-full flex items-center justify-center text-slate-300 font-black text-[9px] uppercase tracking-widest">Run simulation to view 3D Crop Surface</div>
               )}
            </div>
            <div className="space-y-6">
              {dashData && (
                <div className="grid grid-cols-2 gap-4">
                  {[
                    { l: 'Total Variants', v: dashData.df_rows },
                    { l: 'Avg Yield', v: dashData.twso_baseline.toLocaleString() + ' kg' },
                    { l: 'Max LAI', v: dashData.lai_max_baseline },
                    { l: 'Threshold', v: (dashData.seuils.twso_critique_pct * 100).toFixed(0) + '%' }
                  ].map(m => (
                    <div key={m.l} className="bg-white p-4 rounded-2xl border border-slate-50 text-center shadow-sm">
                      <div className="text-[8px] font-black uppercase text-slate-300 mb-1">{m.l}</div>
                      <div className="text-lg font-black text-slate-900">{m.v}</div>
                    </div>
                  ))}
                </div>
              )}
              {simResult && (
                <div className="bg-blue-50 p-6 rounded-3xl border border-blue-100 space-y-6">
                  <div className="text-[9px] font-black text-blue-500 uppercase tracking-widest">Simulation Insights</div>
                  <div className="grid grid-cols-2 gap-4 text-xs font-bold text-slate-700">
                    <div>Alerts: <span className="text-rose-600">{simResult.nb_alertes_critique} Critical</span></div>
                    <div>Horizon: <span className="text-blue-600">{simHorizon.replace('_', ' ').replace('mois', 'months')}</span></div>
                  </div>
                  
                  {/* Stress Risks from Project 4 */}
                  <div className="pt-4 border-t border-blue-100 grid grid-cols-3 gap-2">
                    {[
                      { l: 'Drought', v: dashData?.stressRisks?.drought || 0.2, c: '#fb7185' },
                      { l: 'Disease', v: dashData?.stressRisks?.disease || 0.15, c: '#10b981' },
                      { l: 'Heat', v: dashData?.stressRisks?.heat || 0.3, c: '#fbbf24' }
                    ].map(r => (
                      <div key={r.l} className="text-center">
                        <div className="h-1 bg-slate-100 rounded-full overflow-hidden mb-1">
                          <motion.div initial={{ width: 0 }} animate={{ width: `${r.v * 100}%` }} className="h-full" style={{ backgroundColor: r.c }} />
                        </div>
                        <div className="text-[7px] font-black uppercase text-slate-400">{r.l}</div>
                        <div className="text-[9px] font-bold">{(r.v * 100).toFixed(0)}%</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="bg-white/80 rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-8">
          <h2 className="text-xl font-black text-slate-900">Maktar Climatology ({simResult ? 'Simulated' : 'Norms Reference'})</h2>
          <div className="h-[350px] bg-slate-50/50 rounded-2xl p-6 border border-white shadow-inner">
            {dashData ? (
              <Bar
                data={{
                  labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                  datasets: [
                    { 
                      label: 'Rainfall (mm)', 
                      data: simResult ? 
                        // Aggregate 180 days into 12 months for simulation
                        Array.from({length: 12}, (_, i) => {
                          const monthDays = simResult.meteo_simulee.slice(i*15, (i+1)*15);
                          return monthDays.reduce((acc, d) => acc + (d.pluie_mm || 0), 0);
                        }) : 
                        (dashData?.meteo?.pluie || []), 
                      backgroundColor: 'rgba(96, 165, 250, 0.4)', 
                      borderRadius: 8 
                    },
                    { 
                      label: 'Tmax (°C)', 
                      data: simResult ? 
                        Array.from({length: 12}, (_, i) => {
                          const monthDays = simResult.meteo_simulee.slice(i*15, (i+1)*15);
                          return monthDays.reduce((acc, d) => acc + (d.tmax || 0), 0) / (monthDays.length || 1);
                        }) : 
                        (dashData?.meteo?.tmax || []), 
                      backgroundColor: 'rgba(244, 63, 94, 0.4)', 
                      borderRadius: 8 
                    }
                  ]
                }}
                options={{ responsive: true, maintainAspectRatio: false, plugins: { legend: { display: true } }, scales: { y: { grid: { display: false } }, x: { grid: { display: false } } } }}
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-slate-300 font-black text-[9px] uppercase tracking-widest">Loading Weather Data...</div>
            )}
          </div>
        </section>

        <section className="bg-white/80 rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-8">
           <h2 className="text-xl font-black text-slate-900">Genomic & WOFOST Norms</h2>
           {norms ? (
             <div className="grid md:grid-cols-2 gap-8">
                <div className="bg-slate-50/50 rounded-2xl p-6 border border-white space-y-4">
                   <div className="text-[10px] font-black text-slate-400 uppercase">Statistical Baselines</div>
                   <div className="space-y-2">
                      <div className="flex justify-between text-xs font-bold"><span>Yield Baseline</span><span className="text-emerald-500">{norms?.twso_baseline || '---'} kg</span></div>
                      <div className="flex justify-between text-xs font-bold"><span>Critical Yield (70%)</span><span className="text-rose-500">{(norms?.twso_baseline * 0.7)?.toFixed(0) || '---'} kg</span></div>
                      <div className="flex justify-between text-xs font-bold"><span>Max LAI Baseline</span><span className="text-blue-500">{norms?.wofost_baseline?.LAI_baseline || '---'}</span></div>
                   </div>
                </div>
                <div className="bg-slate-50/50 rounded-2xl p-6 border border-white space-y-4">
                   <div className="text-[10px] font-black text-slate-400 uppercase">Alert Thresholds</div>
                   <div className="space-y-2">
                      <div className="flex justify-between text-xs font-bold"><span>Heatwave (Tmax)</span><span className="text-rose-500">{norms?.seuils_alerte?.tmax_canicule || '---'}°C</span></div>
                      <div className="flex justify-between text-xs font-bold"><span>Drought Stress (Rain)</span><span className="text-blue-500">{norms?.seuils_alerte?.pluie_stress || '---'} mm/d</span></div>
                   </div>
                </div>
             </div>
           ) : (
             <div className="h-40 flex items-center justify-center text-slate-300">Synchronizing norms...</div>
           )}
        </section>

        <section className="bg-white/80 rounded-[2.5rem] p-8 border border-white/50 shadow-sm space-y-8">
          <h2 className="text-xl font-black text-slate-900">Digital Twin Events ({simResult ? 'Simulation' : 'Baseline'})</h2>
          <div className="space-y-4">
             {(simResult?.evenements || dashData?.events?.[simScenario] || [])?.length > 0 ? (
               <div className="grid gap-4">
                 {(simResult?.evenements || dashData.events[simScenario]).slice(0, 10).map((e, i) => (
                   <div key={i} className={`p-4 rounded-2xl border ${e.severite === 'CRITIQUE' ? 'bg-rose-50 border-rose-100' : 'bg-blue-50 border-blue-100'}`}>
                      <div className="flex justify-between items-center">
                         <span className="text-[10px] font-black uppercase tracking-widest">{e.type || e.type_event}</span>
                         <span className="text-[9px] font-mono opacity-50">Day {e.jour}</span>
                      </div>
                      <p className="text-xs font-bold mt-1">{e.description || e.message}</p>
                   </div>
                 ))}
               </div>
             ) : (
               <div className="h-40 flex items-center justify-center text-slate-300 font-black text-[9px] uppercase tracking-widest bg-slate-50/50 rounded-2xl border border-white">No active simulation events</div>
             )}
          </div>
        </section>

        {activeStep === 10.9 && (
          <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-white rounded-[2.5rem] p-8 border border-amber-100 shadow-sm space-y-6">
            <h3 className="text-2xl font-black text-amber-500 tracking-tighter">Optimized FASTA Seqs</h3>
            <div className="rounded-2xl border border-white bg-slate-50/50 overflow-hidden shadow-inner">
              <table className="w-full text-left font-mono text-xs">
                <thead className="bg-white text-[9px] font-black uppercase text-slate-400">
                  <tr><th className="p-4">SNP</th><th className="p-4">Method</th><th className="p-4">Trait</th></tr>
                </thead>
                <tbody className="text-slate-600">
                  <tr className="border-t border-white"><td className="p-4 font-black text-slate-900">SNP_140</td><td className="p-4 font-bold text-amber-500">ODM</td><td className="p-4">DROUGHT</td></tr>
                </tbody>
              </table>
            </div>
            <button className="w-full py-4 bg-emerald-500 text-white rounded-xl font-black text-[9px] tracking-widest flex items-center justify-center gap-3 active:scale-95 transition-all"><Download className="w-4 h-4" /> EXPORT DATA</button>
          </motion.section>
        )}
      </div>

      <aside className="lg:col-span-1 h-[calc(100vh-250px)] lg:sticky lg:top-24">
        <div className="bg-white/80 backdrop-blur-3xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm flex flex-col h-full">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-10 h-10 bg-amber-50 text-amber-500 rounded-2xl flex items-center justify-center shadow-inner text-sm"><MessageSquare className="w-5 h-5" /></div>
            <div><h3 className="text-lg font-black text-slate-900">Assistant</h3><div className="text-[9px] font-black text-slate-300 uppercase tracking-widest">Genomics Expert</div></div>
          </div>
          <div className="flex-1 overflow-y-auto space-y-6 pr-4 mb-8 scrollbar-hide text-xs">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[90%] p-4 rounded-2xl font-bold leading-relaxed ${m.role === 'user' ? 'bg-amber-400 text-white shadow-md' : 'bg-slate-50/50 text-slate-500 border border-white/50'}`}>{m.text}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-2">
            <input value={chatInput} onChange={(e) => setChatInput(e.target.value)} className="flex-1 bg-slate-50/50 border border-white rounded-xl px-5 py-4 text-xs font-bold focus:outline-none shadow-inner" placeholder="Ask norms..." />
            <button onClick={sendMessage} className="w-14 bg-slate-900 text-white rounded-xl flex items-center justify-center transition-all active:scale-95"><ArrowRight className="w-5 h-5" /></button>
          </div>
        </div>
      </aside>
    </div>
  );
};

// --- Main Page Component ---
const DirectedCrossing = () => {
  const [activeTab, setActiveTab] = useState('real-time');
  const [showDropdown, setShowDropdown] = useState(false);
  const [varieties, setVarieties] = useState([]);

  useEffect(() => {
    const fetchV = async () => {
      try {
        const res = await axios.get('http://127.0.0.1:8000/durum/varieties');
        setVarieties(res.data);
      } catch (e) { console.error(e); }
    };
    fetchV();
  }, []);

  const tabs = [
    { id: 'real-time', label: 'Real-Time', icon: Zap, sub: 'Trait prediction' },
    { id: 'all-phases', label: 'All Phases', icon: Microscope, sub: 'Digital Twin' },
    { id: 'over-time', label: 'Over Time', icon: HistoryIcon, sub: 'History' }
  ];

  return (
    <div className="min-h-screen text-[#1e293b] p-6 sm:p-10 font-sans overflow-x-hidden selection:bg-emerald-500/10 relative">
      <BackgroundPatterns />
      <div className="max-w-6xl mx-auto space-y-10 relative z-10">

        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-50">
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-[9px] font-black uppercase tracking-[0.4em] text-slate-400">
              AgriCulture <ChevronRight className="w-2.5 h-2.5" /> <span className="text-emerald-500">Crossing</span>
            </div>
            <h1 className="text-7xl font-black tracking-tighter text-slate-900 leading-[0.9]">Crossing <span className="text-emerald-500 italic">Studio</span>.</h1>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative">
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="px-6 py-3.5 bg-white/70 backdrop-blur-xl border border-white/80 rounded-2xl font-black text-[10px] tracking-widest flex items-center gap-4 hover:shadow-md transition-all shadow-sm"
              >
                <LayoutDashboard className="w-4 h-4 text-emerald-500" />
                Select Analysis
                <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-500 ${showDropdown ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {showDropdown && (
                  <motion.div
                    initial={{ opacity: 0, y: 15, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 15, scale: 0.95 }}
                    className="absolute top-full right-0 mt-4 w-64 bg-white/95 backdrop-blur-3xl rounded-[2rem] border border-white shadow-xl overflow-hidden p-2"
                  >
                    {tabs.map(tab => (
                      <button
                        key={tab.id} onClick={() => { setActiveTab(tab.id); setShowDropdown(false); }}
                        className={`w-full flex items-center gap-4 p-4 rounded-xl transition-all text-left group ${activeTab === tab.id ? 'bg-emerald-500 text-white shadow-md' : 'hover:bg-slate-50/50 text-slate-500'}`}
                      >
                        <tab.icon className={`w-4 h-4 ${activeTab === tab.id ? 'text-white' : 'text-emerald-500 transition-transform'}`} />
                        <div>
                          <div className="text-sm font-black tracking-tight">{tab.label}</div>
                          <div className={`text-[8px] font-black uppercase tracking-widest ${activeTab === tab.id ? 'opacity-60' : 'text-slate-300'}`}>{tab.sub}</div>
                        </div>
                      </button>
                    ))}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            <StatusBadge status="ready" />
          </div>
        </header>

        <main>
          {activeTab === 'real-time' && <RealTimeView varieties={varieties} />}
          {activeTab === 'all-phases' && <AllPhasesView varieties={varieties} />}
          {activeTab === 'over-time' && <OverTimeView varieties={varieties} />}
        </main>

        <footer className="pt-16 border-t border-slate-100">
          <div className="grid md:grid-cols-2 gap-10 items-center">
            <div className="text-[9px] font-bold font-mono text-slate-300 leading-relaxed uppercase tracking-widest">
              <p>IAAA-Lab (2024) · WOFOST · Wheat 55K SNP</p>
            </div>
            <div className="flex md:justify-end gap-10">
              <div><div className="text-[9px] font-black uppercase tracking-widest text-slate-200 mb-2">Region</div><div className="text-sm font-black text-slate-900 tracking-tighter">Medenine, TN</div></div>
              <div><div className="text-[9px] font-black uppercase tracking-widest text-slate-200 mb-2">Dataset</div><div className="text-sm font-black text-slate-900 tracking-tighter">720 Crossings</div></div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default DirectedCrossing;
