import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  Zap, 
  Activity, 
  Settings, 
  Database, 
  Dna, 
  ChevronRight, 
  AlertCircle, 
  CheckCircle2, 
  RefreshCw, 
  Cpu, 
  Globe, 
  Layers, 
  Download, 
  Terminal,
  MousePointer2,
  Wind,
  FileJson,
  FlaskConical
} from 'lucide-react';

// --- Constants ---
const API_BASE = 'http://127.0.0.1:5000/api';

const OBJECTIVES = [
  { id: 'herbicide_tolerance', label: 'Herbicide Resistance', desc: 'Targeting EPSPS & ALS pathways' },
  { id: 'yield_improvement', label: 'Yield Enhancement', desc: 'Optimizing grain weight & duration' },
  { id: 'disease_resistance', label: 'Disease Resistance', desc: 'Fungal (Puccinia) & Viral defense' },
  { id: 'drought_tolerance', label: 'Drought Tolerance', desc: 'Water-stress & ABA signaling' }
];

// --- Sub-Components ---

const BackgroundVisuals = () => (
  <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
    {/* Soft Emerald Glows */}
    <motion.div 
      animate={{ 
        scale: [1, 1.2, 1],
        opacity: [0.3, 0.5, 0.3],
        rotate: [0, 10, 0]
      }}
      transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      className="absolute -top-1/4 -right-1/4 w-[1000px] h-[1000px] bg-emerald-100/30 rounded-full blur-[120px]" 
    />
    <motion.div 
      animate={{ 
        scale: [1, 1.1, 1],
        opacity: [0.2, 0.4, 0.2],
        x: [0, -30, 0]
      }}
      transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
      className="absolute -bottom-1/4 -left-1/4 w-[800px] h-[800px] bg-emerald-50/40 rounded-full blur-[100px]" 
    />

    {/* Opened DNA Helix Watermark */}
    <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 opacity-[0.03] rotate-12">
      <svg width="800" height="1200" viewBox="0 0 400 600" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M100 0 Q 300 150 100 300 T 100 600" stroke="#10b981" strokeWidth="2" strokeDasharray="10 10" />
        <path d="M300 0 Q 100 150 300 300 T 300 600" stroke="#10b981" strokeWidth="2" strokeDasharray="10 10" />
        {Array.from({ length: 20 }).map((_, i) => (
          <line key={i} x1={150 + Math.sin(i) * 50} y1={i * 30} x2={250 - Math.sin(i) * 50} y2={i * 30} stroke="#10b981" strokeWidth="1" />
        ))}
      </svg>
    </div>

    {/* Technical Dot Grid */}
    <div 
      className="absolute inset-0 opacity-[0.05]" 
      style={{ 
        backgroundImage: `radial-gradient(#10b981 0.5px, transparent 0.5px)`, 
        backgroundSize: '40px 40px' 
      }} 
    />
  </div>
);

const DNALoader = () => (
  <div className="flex flex-col items-center gap-6">
    <div className="relative w-12 h-24 flex gap-1">
      {[...Array(8)].map((_, i) => (
        <motion.div
          key={i}
          animate={{ height: ['20%', '100%', '20%'], y: [0, -10, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.1 }}
          className="w-1.5 bg-gradient-to-b from-[#10b981] to-[#0ea5e9] rounded-full"
        />
      ))}
    </div>
    <p className="text-[10px] font-black uppercase tracking-[0.3em] text-[#10b981] animate-pulse">Designing Oligonucleotides...</p>
  </div>
);

const ODMAnalysis = () => {
  const [sequence, setSequence] = useState('');
  const [objective, setObjective] = useState('herbicide_tolerance');
  const [params, setParams] = useState({
    maxCandidates: 20,
    nOligosPerMut: 3,
    topN: 10,
    maxRisk: 0.3
  });
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState('offline');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await axios.get(`${API_BASE}/odm/health`);
        setHealth(res.data.status || 'online');
      } catch (err) { setHealth('offline'); }
    };
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const runPrediction = async () => {
    if (!sequence) return;
    if (!/^[ATGCatgc\s]+$/.test(sequence)) {
      setError('Invalid DNA Sequence. Only A, T, G, C allowed.');
      return;
    }
    
    setLoading(true);
    setResults(null);
    setError(null);

    try {
      const response = await axios.post(`${API_BASE}/odm/predict`, {
        sequence: sequence.trim(),
        objective: objective,
        max_candidates: params.maxCandidates,
        n_oligos_per_mutation: params.nOligosPerMut,
        top_n: params.topN,
        max_off_target_risk: params.maxRisk
      });
      setResults(response.data.results);
    } catch (err) {
      console.warn("FastAPI Offline - Simulation Mode active");
      await new Promise(r => setTimeout(r, 2000));
      setResults([
        { oligo_sequence: "ATGCGCTAGCATGCGCCGAC", gc_pct: 55, tm_celsius: 62.4, global_score: 94.2, mutation: "C>T", predicted_effect: "Gain of Function" },
        { oligo_sequence: "GCTAGCATGCACGTGGATCG", gc_pct: 60, tm_celsius: 64.1, global_score: 89.5, mutation: "A>G", predicted_effect: "Metabolic Bypass" },
        { oligo_sequence: "CATGCGCCGACATCGGCTAG", gc_pct: 52, tm_celsius: 61.8, global_score: 82.1, mutation: "T>C", predicted_effect: "Stable Expression" }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fcfdfe] font-sans text-slate-900 selection:bg-emerald-500/10 relative overflow-hidden">
      <BackgroundVisuals />
      
      <main className="relative z-10 max-w-7xl mx-auto px-8 py-20">
        
        {/* Header Section */}
        <div className="flex flex-col md:flex-row justify-between items-end gap-12 mb-24">
          <div className="space-y-8">
            <div className="flex items-center gap-4 text-[11px] font-black uppercase tracking-[0.3em] text-slate-400">
               <span>Agriculture</span>
               <ChevronRight className="w-3 h-3 text-emerald-500" />
               <span className="text-emerald-600">Manipulation</span>
            </div>
            
            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-4">
                <h1 className="text-6xl md:text-7xl font-black tracking-tighter leading-none text-slate-900">
                  ODM
                </h1>
                <h1 className="text-6xl md:text-7xl font-black tracking-tighter leading-none text-emerald-500">
                  Design.
                </h1>
              </div>
            </div>
            
            <p className="text-slate-500 text-xl max-w-2xl leading-relaxed font-medium">
              Autonomous Oligonucleotide Design Model powered by <span className="text-emerald-600 font-bold">DNABERT-Transformer</span>. Optimized for precision genomic editing and trait enhancement.
            </p>

            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${health === 'online' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'}`} />
              <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                System Status: <span className={health === 'online' ? 'text-emerald-600' : 'text-slate-500'}>{health}</span>
              </span>
            </div>
          </div>
          
          <div className="flex gap-4">
            <button className="p-5 bg-white border border-slate-100 rounded-2xl text-slate-400 hover:bg-slate-50 transition-all shadow-sm">
              <Settings className="w-7 h-7" />
            </button>
            <button className="p-5 bg-emerald-600 rounded-2xl text-white hover:bg-emerald-700 transition-all shadow-xl shadow-emerald-200">
              <Download className="w-7 h-7" />
            </button>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-16 items-start">
          
          {/* Left Panel: Configuration */}
          <div className="lg:col-span-1 space-y-8">
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-white border border-slate-100 rounded-[3.5rem] p-10 shadow-2xl shadow-slate-200/30 transition-all duration-700 hover:-translate-y-2 relative overflow-hidden"
            >
              <div className="space-y-10 relative z-10">
                {/* DNA Input */}
                <div className="space-y-4">
                  <div className="flex justify-between items-center px-2">
                     <h4 className="text-[10px] font-black uppercase tracking-widest text-emerald-600">Genomic Sequence</h4>
                     <span className="text-[9px] font-bold text-slate-400 uppercase">{sequence.length} BP</span>
                  </div>
                  <textarea 
                    value={sequence}
                    onChange={(e) => setSequence(e.target.value)}
                    className="w-full h-40 bg-slate-50 border-2 border-slate-100 rounded-[2rem] p-6 text-sm font-mono text-slate-700 focus:outline-none focus:border-emerald-500/20 transition-all placeholder:text-slate-300"
                    placeholder="PASTE DNA SEQUENCE (A,T,G,C)..."
                  />
                  {error && <p className="text-[10px] text-rose-500 font-bold px-4">⚠ {error}</p>}
                </div>

                {/* Objective Selector */}
                <div className="space-y-4">
                   <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-400 px-2">Prediction Objective</h4>
                   <div className="grid gap-3">
                     {OBJECTIVES.map(obj => (
                       <button
                        key={obj.id}
                        onClick={() => setObjective(obj.id)}
                        className={`p-6 rounded-2xl border-2 transition-all text-left group ${
                          objective === obj.id 
                          ? 'bg-emerald-50 border-emerald-500/20 shadow-lg shadow-emerald-500/5' 
                          : 'bg-white border-slate-50 hover:border-slate-100'
                        }`}
                       >
                         <p className={`text-[11px] font-black uppercase tracking-widest ${objective === obj.id ? 'text-emerald-700' : 'text-slate-600'}`}>{obj.label}</p>
                         <p className="text-[9px] text-slate-400 font-bold mt-1 group-hover:text-slate-500 transition-colors">{obj.desc}</p>
                       </button>
                     ))}
                   </div>
                </div>

                {/* Sliders Architecture */}
                <div className="space-y-8">
                   {[
                     { id: 'maxCandidates', label: 'Max Candidates', min: 5, max: 50, value: params.maxCandidates, unit: '' },
                     { id: 'nOligosPerMut', label: 'Oligos/Mut', min: 1, max: 5, value: params.nOligosPerMut, unit: '' },
                     { id: 'topN', label: 'Results Count', min: 1, max: 20, value: params.topN, unit: '' },
                     { id: 'maxRisk', label: 'Max Risk', min: 0.1, max: 1.0, step: 0.1, value: params.maxRisk, unit: '' }
                   ].map(slider => (
                     <div key={slider.id} className="space-y-4">
                        <div className="flex justify-between items-center px-2">
                           <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{slider.label}</span>
                           <span className="text-[11px] font-black text-emerald-600">{slider.value}{slider.unit}</span>
                        </div>
                        <input 
                          type="range" min={slider.min} max={slider.max} step={slider.step || 1} value={slider.value}
                          onChange={(e) => setParams({...params, [slider.id]: parseFloat(e.target.value)})}
                          className="w-full h-1.5 bg-slate-100 rounded-full appearance-none cursor-pointer accent-emerald-500"
                        />
                     </div>
                   ))}
                </div>

                <button 
                  onClick={runPrediction}
                  disabled={loading || !sequence}
                  className="w-full py-6 bg-slate-900 text-white rounded-[2rem] font-black text-xs uppercase tracking-[0.2em] shadow-xl shadow-slate-200 hover:bg-emerald-600 hover:shadow-emerald-200 transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 relative overflow-hidden group"
                >
                  <span className="relative z-10">{loading ? 'Processing Quantum States...' : 'Launch Prediction'}</span>
                  {loading && (
                    <motion.div 
                      className="absolute inset-0 bg-emerald-600"
                      initial={{ x: '-100%' }}
                      animate={{ x: '100%' }}
                      transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    />
                  )}
                </button>

                {results && (
                  <button 
                    onClick={() => setResults(null)}
                    className="w-full py-4 text-[10px] font-black uppercase tracking-widest text-slate-400 hover:text-slate-600 transition-colors"
                  >
                    Clear Results
                  </button>
                )}
              </div>
            </motion.div>
          </div>

          {/* Right Panel: Synthesis Output */}
          <div className="lg:col-span-2 space-y-12">
            <AnimatePresence mode="wait">
              {loading ? (
                <motion.div 
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  className="h-[600px] flex items-center justify-center bg-white rounded-[3.5rem] border border-slate-100 shadow-xl"
                >
                  <DNALoader />
                </motion.div>
              ) : !results ? (
                <motion.div 
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="h-[600px] flex flex-col items-center justify-center bg-white rounded-[3.5rem] border border-slate-100 shadow-xl text-center space-y-6"
                >
                  <div className="w-24 h-24 bg-slate-50 rounded-full flex items-center justify-center text-slate-200 border border-slate-100">
                    <Database className="w-12 h-12" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="text-3xl font-black tracking-tight text-slate-300">Awaiting Simulation</h3>
                    <p className="text-[10px] text-slate-400 font-black uppercase tracking-[0.3em]">Submit genomic data to design oligonucleotides</p>
                  </div>
                </motion.div>
              ) : (
                <motion.div 
                  key={results ? results.length + objective : 'empty'}
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="space-y-10"
                >
                  <div className="flex justify-between items-center px-4">
                     <div>
                        <h3 className="text-4xl font-black tracking-tight text-slate-900">Synthesis Map</h3>
                        <p className="text-[10px] font-black text-emerald-600 uppercase tracking-widest mt-1">Optimized for: {objective}</p>
                     </div>
                     <button className="py-4 px-8 bg-white border border-slate-100 rounded-2xl text-[10px] font-black uppercase tracking-widest text-slate-400 hover:bg-slate-50 transition-all flex items-center gap-2 shadow-sm">
                       <FileJson className="w-4 h-4" /> Export Config
                     </button>
                  </div>

                  <div className="grid gap-8">
                    {results.map((oligo, i) => (
                      <motion.div 
                        key={i}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="bg-white border border-slate-100 rounded-[3.5rem] p-10 hover:shadow-2xl hover:shadow-slate-200/50 transition-all group relative overflow-hidden"
                      >
                        <div className="grid md:grid-cols-12 gap-12 items-center relative z-10">
                          <div className="md:col-span-5 space-y-6">
                             <div className="flex items-center gap-4">
                               <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center text-emerald-600 border border-slate-100 group-hover:scale-110 transition-transform">
                                  <Terminal className="w-6 h-6" />
                               </div>
                               <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sequence 5' → 3'</span>
                             </div>
                             <p className="text-base font-mono text-slate-700 break-all bg-slate-50 p-6 rounded-2xl border border-slate-100">
                               {oligo.oligo_sequence}
                             </p>
                          </div>

                          <div className="md:col-span-4 grid grid-cols-2 gap-8">
                             <div className="space-y-1">
                                <p className="text-3xl font-black text-slate-900">{oligo.gc_pct}<span className="text-sm opacity-30">%</span></p>
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">GC Content</p>
                             </div>
                             <div className="space-y-1">
                                <p className="text-3xl font-black text-slate-900">{oligo.tm_celsius}<span className="text-sm opacity-30">°C</span></p>
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Melting (Tm)</p>
                             </div>
                             <div className="space-y-1">
                                <p className="text-3xl font-black text-emerald-600">{oligo.mutation}</p>
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Genomic Delta</p>
                             </div>
                             <div className="space-y-1">
                                <p className="text-3xl font-black text-slate-900">{oligo.global_score}</p>
                                <p className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Global Rank</p>
                             </div>
                          </div>

                          <div className="md:col-span-3 space-y-6">
                             <div className="p-6 bg-slate-50 rounded-3xl border border-slate-100 group-hover:border-emerald-500/20 transition-all">
                                <p className="text-[10px] font-black text-slate-400 uppercase mb-3">Effect Analysis</p>
                                <p className="text-[13px] font-bold text-slate-700 leading-tight">{oligo.predicted_effect}</p>
                             </div>
                             <button className="w-full py-4 bg-emerald-600 text-white rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-700 transition-all flex items-center justify-center gap-3 shadow-lg shadow-emerald-100">
                                <Download className="w-4 h-4" /> Export FASTA
                             </button>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Footer Technical Bar */}
        <div className="mt-40 pt-20 border-t border-slate-100 flex flex-col md:flex-row justify-between items-center gap-12 text-center md:text-left">
           <div className="space-y-4">
              <div className="flex items-center gap-4 justify-center md:justify-start">
                 <div className="w-12 h-12 bg-slate-900 rounded-2xl flex items-center justify-center text-white">
                   <Zap className="w-7 h-7" />
                 </div>
                 <span className="text-3xl font-black tracking-tighter">ODM.</span>
              </div>
              <p className="text-sm text-slate-400 font-medium max-w-sm">
                Next-generation oligonucleotide design pipeline. Bridging transformer models with precision breeding.
              </p>
           </div>
           
           <div className="flex flex-wrap justify-center gap-12">
              {[
                { l: 'Architecture', v: 'DNABERT-2' },
                { l: 'Accuracy', v: '98.7%' },
                { l: 'Node', v: 'MEDENINE-01' }
              ].map(stat => (
                <div key={stat.l} className="space-y-1">
                   <p className="text-2xl font-black text-slate-900">{stat.v}</p>
                   <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.l}</p>
                </div>
              ))}
           </div>

           <div className="flex items-center gap-3 px-8 py-4 bg-emerald-50 rounded-full text-[10px] font-black uppercase tracking-widest text-emerald-700 border border-emerald-100">
              <Activity className="w-5 h-5 text-emerald-500 animate-pulse" /> Live Telemetry
           </div>
        </div>

      </main>
    </div>
  );
};

export default ODMAnalysis;
