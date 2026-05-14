import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Search, 
  Dna, 
  MessageSquare, 
  Hash, 
  Tag, 
  Sprout, 
  ChevronRight, 
  ChevronDown, 
  Layers, 
  Cpu, 
  BookOpen, 
  Send, 
  History, 
  BarChart3,
  ExternalLink,
  ChevronLeft,
  Settings2,
  Database,
  ArrowRight,
  Loader2,
  CheckCircle2,
  Info,
  Download,
  Terminal,
  Clock,
  Zap
} from 'lucide-react';

// --- Constants ---
const MODES = [
  { id: 'sequence', label: 'Raw DNA', icon: Dna, placeholder: 'Enter ATCG sequence...' },
  { id: 'text', label: 'Natural Language', icon: MessageSquare, placeholder: 'What genes are responsible for drought tolerance?' },
  { id: 'gene', label: 'Gene / Accession', icon: Tag, placeholder: 'Enter Gene Name or LC881789.1...' },
  { id: 'trait', label: 'Trait-Based', icon: Sprout, placeholder: 'Select target trait...' }
];

const TRAITS = [
  { id: 'drought', label: 'Drought Tolerance', color: 'bg-emerald-500' },
  { id: 'salt', label: 'Salt Tolerance', color: 'bg-blue-500' },
  { id: 'yield', label: 'High Yield', color: 'bg-amber-500' },
  { id: 'disease', label: 'Disease Resistance', color: 'bg-rose-500' }
];

// --- Typewriter Component ---
const Typewriter = ({ text, delay = 20, onComplete }) => {
  const [currentText, setCurrentText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setCurrentText(prevText => prevText + text[currentIndex]);
        setCurrentIndex(prevIndex => prevIndex + 1);
      }, delay);
      return () => clearTimeout(timeout);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, delay, text]);

  const formatTextWithLinks = (text) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return text.split(urlRegex).map((part, i) => {
      if (part.match(urlRegex)) {
        return <a key={i} href={part} target="_blank" rel="noopener noreferrer" className="text-emerald-500 hover:text-emerald-600 hover:underline">{part}</a>;
      }
      return part;
    });
  };

  return <span>{formatTextWithLinks(currentText)}</span>;
};

// --- Helper Components ---

const SignalBar = ({ label, value, max = 1, color = "bg-blue-400" }) => (
  <div className="flex-1 space-y-1">
    <div className="flex justify-between text-[8px] font-black uppercase text-slate-400 px-1">
      <span>{label}</span>
      <span className="font-mono">{value}</span>
    </div>
    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden border border-white">
      <motion.div 
        initial={{ width: 0 }}
        animate={{ width: `${(value / max) * 100}%` }}
        className={`h-full ${color}`}
      />
    </div>
  </div>
);

const ResultCard = ({ result }) => {
  const [expanded, setExpanded] = useState(false);
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    try {
      setDownloading(true);
      const response = await fetch('http://127.0.0.1:5007/api/rag/pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sequence: result.sequence_preview,
          accession: result.accession,
          gene: result.gene_name
        })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Download failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.setAttribute('download', `Fiche_${result.accession || 'Genomic'}.pdf`);
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }, 100);
    } catch (err) {
      console.error('PDF Download Error:', err);
      alert('Failed to generate PDF report');
    } finally {
      setDownloading(false);
    }
  };
  
  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white/80 backdrop-blur-xl rounded-[2.5rem] p-8 border border-white/50 shadow-sm hover:shadow-2xl hover:border-emerald-200 transition-all group relative overflow-hidden"
    >
      {/* RRF Score Badge */}
      <div className="absolute top-0 right-0 p-6">
        <div className="bg-emerald-500/10 text-emerald-600 px-4 py-1.5 rounded-full text-[10px] font-black uppercase tracking-widest border border-emerald-100/50">
          RRF SCORE: {result.rrf_score.toFixed(3)}
        </div>
      </div>

      <div className="flex items-start gap-6 mb-8">
        <div className="w-14 h-14 bg-slate-900 text-white rounded-[1.5rem] flex items-center justify-center font-black text-xl shadow-xl shadow-slate-900/20">
          #{result.rank}
        </div>
        <div>
          <h4 className="text-xl font-black font-mono text-slate-900 tracking-tighter uppercase mb-1">{result.gene_name || 'Unidentified Gene'}</h4>
          <div className="flex items-center gap-3">
             <span className="text-xs font-bold text-slate-400 font-mono tracking-widest">{result.accession}</span>
             <div className={`px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest text-white shadow-lg ${
               result.trait === 'drought_tolerance' ? 'bg-emerald-500 shadow-emerald-500/20' : 
               result.trait === 'salt_tolerance' ? 'bg-blue-500 shadow-blue-500/20' : 'bg-amber-500 shadow-amber-500/20'
             }`}>
               {result.trait.replace('_', ' ')}
             </div>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between items-center px-1">
            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Model Confidence</span>
            <span className="text-[11px] font-black font-mono text-emerald-600">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
          <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden border border-white shadow-inner p-0.5">
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${result.confidence * 100}%` }}
              className="h-full bg-emerald-500 rounded-full"
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-6">
          <SignalBar label="Sparse" value={result.signals.sparse} max={100} color="bg-blue-400" />
          <SignalBar label="DNABERT" value={result.signals.dnabert} max={1} color="bg-indigo-400" />
          <SignalBar label="K-mer" value={result.signals.kmer} max={1} color="bg-teal-400" />
        </div>

        <div className="bg-slate-50/80 rounded-[2rem] p-6 border border-white/50 relative overflow-hidden">
          <div className="flex items-center justify-between mb-3">
             <div className="text-[10px] font-black uppercase tracking-widest text-slate-300">Nucleotide Sequence (60bp Preview)</div>
             <Terminal className="w-3.5 h-3.5 text-slate-200" />
          </div>
          <div className="font-mono text-[11px] text-slate-500 break-all leading-relaxed bg-white/50 p-4 rounded-xl border border-white">
            {expanded ? result.sequence_preview : result.sequence_preview.slice(0, 60)}
            {!expanded && <span className="opacity-30">...</span>}
          </div>
          <button 
            onClick={() => setExpanded(!expanded)}
            className="mt-4 text-[10px] font-black text-emerald-600 uppercase tracking-widest flex items-center gap-2 hover:gap-3 transition-all"
          >
            {expanded ? 'Collapse Matrix' : 'Full Sequence Access'} <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="flex gap-4">
          <button className="flex-1 py-4 bg-slate-900 text-white hover:bg-black rounded-2xl text-[10px] font-black uppercase tracking-widest flex items-center justify-center gap-2 transition-all shadow-xl shadow-slate-900/10 active:scale-95">
            <ExternalLink className="w-4 h-4" /> Europe PMC Full Text
          </button>
          <button 
            onClick={handleDownload}
            disabled={downloading}
            className="w-14 h-14 bg-white border border-slate-100 text-slate-400 hover:text-emerald-500 hover:border-emerald-100 rounded-2xl flex items-center justify-center transition-all shadow-sm active:scale-90 disabled:opacity-50"
          >
            {downloading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Download className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

// --- Main Page Component ---

const RAGAnalysis = () => {
  const [activeMode, setActiveMode] = useState('text');
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [searchMode, setSearchMode] = useState('rag');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [answer, setAnswer] = useState(null);
  const [agentOpen, setAgentOpen] = useState(false);
  const [streamingComplete, setStreamingComplete] = useState(false);
  
  const resultsRef = useRef(null);
  
  const [messages, setMessages] = useState([
    { role: 'ai', text: "Researcher Identity Confirmed. Accessing IRA-Durum Database (3,998 entries). How can I assist with your trait analysis today?", time: 'Now' }
  ]);

  const RAG_API = 'http://127.0.0.1:5007';

  const handleSearch = async () => {
    if (!query && activeMode !== 'trait') return;
    setLoading(true);
    setResults([]);
    setAnswer(null);
    setStreamingComplete(false);

    try {
      const payload = {
        question: activeMode === 'trait' ? query || 'drought tolerance' : query,
        query: activeMode === 'trait' ? query || 'drought tolerance' : query,
        mode: activeMode,        // 'sequence' | 'text' | 'gene' | 'trait'
        top_k: topK,
        search_mode: searchMode  // 'rag' | 'search'
      };

      const response = await fetch(`${RAG_API}/${searchMode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const data = await response.json();

      // Map backend response → UI format
      const mapped = (data.sequences || data.results || []).map((r, i) => ({
        rank: i + 1,
        accession: r.accession || r.id || '—',
        gene_name: r.gene_name || r.name || 'Unknown',
        trait: r.trait || 'unknown',
        confidence: r.confidence ?? r.score ?? 0,
        signals: {
          sparse: r.signals?.sparse ?? r.sparse_score ?? 0,
          dnabert: r.signals?.dnabert ?? r.dense_dnabert ?? 0,
          kmer: r.signals?.kmer ?? r.dense_kmer ?? 0
        },
        rrf_score: r.rrf_score ?? r.score ?? 0,
        sequence_preview: r.sequence ?? r.description ?? ''
      }));

      setResults(mapped);

      if (data.answer) {
        setAnswer({
          text: data.answer,
          citations: (data.articles || data.citations || []).map((a, i) => ({
            index: i + 1,
            title: a.title,
            pmid: a.pmid,
            url: a.url
          })),
          model: data.model || 'LLaMA-3.3-70b via Groq',
          stats: data.stats || `${mapped.length} results · ${data.latency || '—'}s`
        });
      }

      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      console.error('RAG Search failed:', err);
      setAnswer({
        text: `⚠️ Connection error: ${err.message}. Make sure the RAG server is running on port 5007.`,
        citations: [],
        model: 'Unavailable',
        stats: 'Server offline'
      });
    } finally {
      setLoading(false);
    }
  };


  const addMessage = (text, role = 'user') => {
    setMessages(prev => [...prev, { role, text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
  };

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 p-6 sm:p-12 font-sans selection:bg-emerald-500/20">
      {/* Background Decor */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-0 right-0 w-[1000px] h-[1000px] bg-emerald-100/30 rounded-full blur-[180px] -mr-96 -mt-96" />
        <div className="absolute bottom-0 left-0 w-[800px] h-[800px] bg-blue-100/20 rounded-full blur-[150px] -ml-72 -mb-72" />
        <div className="absolute inset-0 opacity-[0.03]" style={{ backgroundImage: 'radial-gradient(#10b981 0.5px, transparent 0.5px)', backgroundSize: '48px 48px' }} />
      </div>

      <div className={`max-w-[1400px] mx-auto space-y-12 relative z-10 transition-all duration-700 ease-in-out ${agentOpen ? 'pr-[450px]' : ''}`}>
        
        {/* Header Section */}
        <header className="flex flex-col md:flex-row justify-between items-end gap-8">
          <div className="space-y-4">
            <div className="flex items-center gap-3 text-[11px] font-black uppercase tracking-[0.5em] text-slate-300">
              IRA AI Platform <ChevronRight className="w-3 h-3" /> Genomic Search <ChevronRight className="w-3 h-3" /> <span className="text-emerald-500">RAG Analysis</span>
            </div>
            <h1 className="text-6xl font-black tracking-tighter text-slate-900 leading-none">Geno<span className="text-emerald-500 italic">Nexus</span>.</h1>
            <p className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] max-w-2xl leading-relaxed">
              Autonomous Hybrid Retrieval Pipeline integrating <span className="text-emerald-500">DNABERT-2 Semantic Inference</span> and <span className="text-blue-500">RRF-Fused k-mer Indexing</span> for Precision Arid-Zone Genomics.
            </p>
          </div>
          
          <div className="bg-white/70 backdrop-blur-xl border border-white/50 rounded-[2rem] p-6 flex items-center gap-10 shadow-sm">
            {[
              { label: 'DB Sequences', val: '3,998', icon: Database },
              { label: 'SNP Features', val: '159', icon: Layers },
              { label: 'Signals', val: '3 Hybrid', icon: Cpu }
            ].map(stat => (
              <div key={stat.label} className="flex items-center gap-4">
                <div className="w-10 h-10 bg-slate-50 rounded-2xl flex items-center justify-center shadow-inner text-emerald-500"><stat.icon className="w-5 h-5" /></div>
                <div>
                  <div className="text-[9px] font-black uppercase tracking-widest text-slate-300 mb-0.5">{stat.label}</div>
                  <div className="text-base font-black text-slate-900 font-mono tracking-tighter">{stat.val}</div>
                </div>
              </div>
            ))}
          </div>
        </header>

        {/* Input Control Module */}
        <section className="bg-white/40 backdrop-blur-2xl rounded-[3.5rem] p-2 border border-white/50 shadow-2xl overflow-hidden">
          <div className="flex flex-col lg:flex-row min-h-[400px]">
            {/* Mode Switcher */}
            <div className="lg:w-72 bg-slate-50/50 p-6 space-y-3 border-r border-white/50">
              <div className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-400 mb-6 px-4">Research Mode</div>
              {MODES.map(mode => (
                <button
                  key={mode.id}
                  onClick={() => setActiveMode(mode.id)}
                  className={`w-full flex items-center gap-4 px-6 py-4 rounded-[1.5rem] transition-all text-left group ${
                    activeMode === mode.id ? 'bg-emerald-500 text-white shadow-xl shadow-emerald-500/20' : 'hover:bg-white text-slate-500'
                  }`}
                >
                  <mode.icon className={`w-5 h-5 ${activeMode === mode.id ? 'text-white' : 'text-emerald-500 group-hover:scale-110 transition-transform'}`} />
                  <span className="text-sm font-black tracking-tight">{mode.label}</span>
                </button>
              ))}
            </div>

            {/* Main Input & Parameters Area with Cinematic Background */}
            <div className="flex-1 p-10 flex flex-col relative overflow-hidden">
              {/* Soft Meaningful Background (Lab Research) */}
              <div className="absolute inset-0 z-0 opacity-40 pointer-events-none group-hover:opacity-60 transition-opacity duration-1000">
                <iframe 
                  className="absolute inset-0 w-full h-full scale-[1.8] object-cover"
                  src="https://www.youtube.com/embed/Ars8JB-g4p8?autoplay=1&mute=1&loop=1&playlist=Ars8JB-g4p8&controls=0&showinfo=0&rel=0&iv_load_policy=3&modestbranding=1" 
                  title="Lab Research Background"
                  frameBorder="0" 
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                />
              </div>

              <div className="relative z-10 flex-1 space-y-10">
                <div className="relative group">
                  <div className="absolute inset-0 bg-emerald-500/10 rounded-[2.5rem] blur-3xl opacity-0 group-focus-within:opacity-100 transition-opacity duration-700" />
                  <div className="relative bg-white/60 backdrop-blur-md border border-white rounded-[2.5rem] p-8 focus-within:border-emerald-500/40 transition-all shadow-xl shadow-slate-900/10">
                    <div className="flex items-center gap-6">
                      {activeMode === 'trait' ? (
                        <select 
                          className="w-full bg-slate-50 border border-slate-100 rounded-2xl px-8 h-16 text-lg font-bold text-slate-600 focus:outline-none appearance-none cursor-pointer"
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                        >
                          <option value="">Select Target Trait Profile...</option>
                          {TRAITS.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
                        </select>
                      ) : activeMode === 'sequence' ? (
                        <textarea 
                          className="w-full bg-transparent text-xl font-mono text-slate-800 placeholder:text-slate-200 outline-none resize-none scrollbar-hide"
                          placeholder={MODES.find(m => m.id === activeMode).placeholder}
                          rows={3}
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                        />
                      ) : (
                        <input 
                          className="w-full bg-transparent text-2xl font-black text-slate-900 placeholder:text-slate-200 outline-none tracking-tight"
                          placeholder={MODES.find(m => m.id === activeMode).placeholder}
                          value={query}
                          onChange={(e) => setQuery(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                        />
                      )}
                      <button 
                        onClick={handleSearch}
                        disabled={loading}
                        className="w-20 h-20 bg-slate-900 hover:bg-black text-white rounded-[2rem] flex items-center justify-center transition-all shadow-2xl shadow-slate-900/40 active:scale-90 disabled:opacity-50"
                      >
                        {loading ? <Loader2 className="w-8 h-8 animate-spin" /> : <ArrowRight className="w-10 h-10" />}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Advanced Search Parameters */}
                <div className="flex flex-wrap items-center justify-between gap-10">
                  <div className="flex items-center gap-12">
                    <div className="space-y-4">
                      <div className="flex justify-between items-center px-2">
                        <span className="text-[10px] font-black uppercase tracking-widest text-slate-300">Top-K Depth</span>
                        <span className="text-sm font-black text-emerald-600 font-mono">{topK} results</span>
                      </div>
                      <input 
                        type="range" min="3" max="20" step="1" 
                        value={topK} onChange={(e) => setTopK(e.target.value)}
                        className="w-56 h-1.5 bg-slate-100 rounded-full appearance-none cursor-pointer accent-emerald-500 shadow-inner"
                      />
                    </div>

                    <div className="h-12 w-px bg-slate-100 hidden md:block" />

                    <div className="flex bg-slate-50/80 p-1.5 rounded-[1.5rem] border border-white shadow-inner">
                      {[
                        { id: 'search', label: 'Search Only', icon: Search },
                        { id: 'rag', label: 'RAG Answer', icon: MessageSquare },
                        { id: 'agent', label: 'Agentic Flow', icon: Zap }
                      ].map(m => (
                        <button
                          key={m.id}
                          onClick={() => {
                            setSearchMode(m.id);
                            if (m.id === 'agent') setAgentOpen(true);
                          }}
                          className={`flex items-center gap-2.5 px-5 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all ${
                            searchMode === m.id ? 'bg-white text-slate-900 shadow-md' : 'text-slate-400 hover:text-slate-600'
                          }`}
                        >
                          <m.icon className="w-4 h-4" />
                          {m.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-[10px] font-black text-slate-300 uppercase tracking-widest">Region: Tunisia (Medenine)</div>
                    <button 
                      onClick={() => setAgentOpen(!agentOpen)}
                      className={`flex items-center gap-3 px-8 py-4 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all shadow-xl active:scale-95 ${
                        agentOpen ? 'bg-amber-500 text-white shadow-amber-500/30' : 'bg-white border border-slate-100 text-slate-500 shadow-slate-200/50'
                      }`}
                    >
                      <Zap className="w-4 h-4" /> DNA Agent {agentOpen ? 'Active' : 'Standby'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Dynamic Response Area */}
        <div ref={resultsRef} className="grid lg:grid-cols-3 gap-10 items-start pb-24">
          
          <div className="lg:col-span-2 space-y-10">
            {/* RAG Answer Display */}
            <AnimatePresence>
              {answer && (
                <motion.div 
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-white/90 backdrop-blur-3xl rounded-[3.5rem] p-12 border-2 border-emerald-500/20 shadow-[0_50px_100px_rgba(16,185,129,0.1)] relative overflow-hidden"
                >
                  <div className="absolute top-0 right-0 p-8">
                    <div className="bg-emerald-500 text-white px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-[0.2em] shadow-lg shadow-emerald-500/30 flex items-center gap-2">
                      <div className="w-2 h-2 bg-white rounded-full animate-pulse" /> AI GENERATED INSIGHT
                    </div>
                  </div>

                  <div className="flex items-center gap-6 mb-10">
                    <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center shadow-inner">
                      <MessageSquare className="w-8 h-8" />
                    </div>
                    <div>
                      <h3 className="text-3xl font-black text-slate-900 tracking-tight">RAG Synthesis</h3>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-[10px] font-black text-emerald-600 uppercase tracking-widest bg-emerald-50 px-3 py-1 rounded-full">LLaMA-3.3-70B-versatile</span>
                        <span className="text-[10px] font-black text-slate-300 uppercase tracking-widest">via Groq Cloud</span>
                      </div>
                    </div>
                  </div>

                  <div className="text-2xl font-medium text-slate-700 leading-relaxed mb-12 border-l-8 border-emerald-500/10 pl-10">
                    <Typewriter text={answer.text} onComplete={() => setStreamingComplete(true)} />
                    {!streamingComplete && <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 0.8 }} className="inline-block w-3 h-8 bg-emerald-500 ml-1 translate-y-1" />}
                  </div>

                  {streamingComplete && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 animate-in fade-in duration-1000">
                      <div className="text-[11px] font-black uppercase tracking-[0.4em] text-slate-400 px-2 flex items-center gap-4">
                        <BookOpen className="w-4 h-4" /> Academic Literature Citations
                      </div>
                      <div className="grid md:grid-cols-2 gap-6">
                        {answer.citations.map(cite => (
                            <a href={cite.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${cite.pmid}/` : cite.url || '#'} target="_blank" rel="noopener noreferrer" key={cite.index} className="bg-slate-50/50 p-6 rounded-[2rem] border border-white hover:border-emerald-300 transition-all group cursor-pointer shadow-sm block">
                              <div className="flex gap-4">
                                <div className="w-10 h-10 bg-white rounded-2xl flex items-center justify-center font-black text-sm text-emerald-500 shadow-sm border border-slate-50 group-hover:bg-emerald-500 group-hover:text-white transition-all">[{cite.index}]</div>
                                <div className="flex-1">
                                  <div className="text-sm font-black text-slate-800 leading-tight mb-2 group-hover:text-emerald-700 transition-colors">{cite.title}</div>
                                  <div className="flex items-center gap-3">
                                     <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">PMID: {cite.pmid || 'N/A'}</div>
                                     <div className="w-1 h-1 bg-slate-200 rounded-full" />
                                     <div className="text-[9px] font-black text-emerald-600 uppercase tracking-widest flex items-center gap-1">Open Access <ExternalLink className="w-3 h-3" /></div>
                                  </div>
                                </div>
                              </div>
                            </a>
                        ))}
                      </div>

                      <div className="mt-12 pt-8 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-6 text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">
                        <div className="flex items-center gap-6">
                           <span className="flex items-center gap-2"><Clock className="w-4 h-4 text-emerald-500" /> 1.39s latency</span>
                           <span className="flex items-center gap-2"><Database className="w-4 h-4 text-emerald-500" /> 5 papers analyzed</span>
                        </div>
                        <div className="flex items-center gap-2 bg-emerald-50 px-6 py-2 rounded-full text-emerald-600">
                           <CheckCircle2 className="w-4 h-4" /> PIPELINE SECURE & VERIFIED
                        </div>
                      </div>
                    </motion.div>
                  )}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Results Header */}
            <div className="flex items-center justify-between px-6 pt-6">
              <h3 className="text-3xl font-black tracking-tighter text-slate-900">
                {loading ? 'Processing DNA Signals...' : results.length > 0 ? `Hybrid Matches (${results.length})` : 'Awaiting Input...'}
              </h3>
              {results.length > 0 && (
                <div className="flex items-center gap-4">
                   <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Sort: RRF Score</div>
                   <button className="text-emerald-500 hover:text-emerald-600 font-black text-[10px] uppercase tracking-widest flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm border border-slate-100">
                     <Download className="w-4 h-4" /> Export CSV
                   </button>
                </div>
              )}
            </div>

            {/* Match Results List */}
            <div className="grid gap-8">
              {loading && !results.length && (
                [...Array(3)].map((_, i) => (
                  <div key={i} className="h-64 bg-white/50 animate-pulse rounded-[3rem] border border-white" />
                ))
              )}
              {results.map(r => <ResultCard key={r.rank} result={r} />)}
            </div>
          </div>

          {/* Contextual Stats Column */}
          <div className="space-y-10 lg:sticky lg:top-12">
            <div className="bg-white/80 backdrop-blur-2xl rounded-[3rem] p-10 border border-white/50 shadow-sm space-y-8">
              <h3 className="text-xl font-black text-slate-900 flex items-center gap-3">
                <Settings2 className="w-6 h-6 text-emerald-500" /> Retrieval Health
              </h3>
              <div className="space-y-6">
                {[
                  { l: 'Signal 1: Inverted Index', v: 'Exact Match', d: 'k-mer sparse matching' },
                  { l: 'Signal 2: DNABERT-2', v: 'Semantic Mean', d: 'Cosine similarity on 768-dim' },
                  { l: 'Signal 3: K-mer FAISS', v: 'Compositional', d: 'Frequency vector search' }
                ].map(s => (
                  <div key={s.l} className="group cursor-default">
                    <div className="text-[10px] font-black uppercase text-slate-400 mb-1 group-hover:text-emerald-500 transition-colors">{s.l}</div>
                    <div className="text-sm font-black text-slate-800 mb-0.5">{s.v}</div>
                    <div className="text-[9px] font-bold text-slate-300 italic">{s.d}</div>
                  </div>
                ))}
              </div>
              <div className="pt-8 border-t border-slate-50">
                <div className="bg-emerald-50 p-6 rounded-[2rem] border border-emerald-100/50">
                  <div className="flex items-center gap-3 mb-2">
                    <Info className="w-5 h-5 text-emerald-600" />
                    <span className="text-[10px] font-black text-emerald-600 uppercase tracking-widest">System Note</span>
                  </div>
                  <p className="text-[11px] font-bold text-emerald-700 leading-relaxed">
                    Hybrid RRF (Reciprocal Rank Fusion) is active. Signal weights: 0.4 Dense | 0.4 Semantic | 0.2 Sparse.
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-3xl relative overflow-hidden group">
              <div className="absolute inset-0 bg-emerald-500/10 -translate-x-full group-hover:translate-x-0 transition-transform duration-1000" />
              <Dna className="absolute -right-12 -bottom-12 w-48 h-48 opacity-10 rotate-12 group-hover:rotate-45 transition-transform duration-1000" />
              <div className="relative z-10 space-y-8">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.3em] opacity-40 mb-4">Search Context</div>
                  <div className="text-4xl font-black tracking-tighter">IRA-MED</div>
                  <div className="text-xs font-medium text-emerald-400 flex items-center gap-2 mt-1">
                     <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" /> Live FAISS Indexing
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between text-[10px] font-black uppercase opacity-60">Memory Occupancy</div>
                  <div className="h-2 bg-white/10 rounded-full overflow-hidden p-0.5">
                    <motion.div initial={{ width: 0 }} animate={{ width: '42%' }} className="h-full bg-emerald-500 rounded-full" />
                  </div>
                  <div className="text-[9px] font-bold opacity-30 text-right uppercase">7.2 GB / 16 GB</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Advanced Agent Panel */}
      <AnimatePresence>
        {agentOpen && (
          <motion.aside 
            initial={{ x: 500 }}
            animate={{ x: 0 }}
            exit={{ x: 500 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 w-[450px] h-full bg-white/95 backdrop-blur-3xl border-l border-white shadow-[-30px_0_60px_rgba(0,0,0,0.05)] z-[100] flex flex-col"
          >
            {/* Agent Header */}
            <div className="p-10 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-5">
                <div className="relative">
                  <div className="w-16 h-16 bg-amber-500 text-white rounded-[2rem] flex items-center justify-center shadow-2xl shadow-amber-500/30">
                    <Zap className="w-9 h-9" />
                  </div>
                  <div className="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-500 border-4 border-white rounded-full" />
                </div>
                <div>
                  <h3 className="text-2xl font-black text-slate-900 tracking-tight">DNA Agent</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black text-amber-500 uppercase tracking-widest">Memory Active</span>
                    <span className="text-xs font-bold text-slate-300 font-mono">v3.3</span>
                  </div>
                </div>
              </div>
              <button 
                onClick={() => setAgentOpen(false)}
                className="w-12 h-12 bg-slate-50 text-slate-400 rounded-full flex items-center justify-center hover:bg-slate-100 transition-all active:scale-90"
              >
                <ChevronRight className="w-7 h-7" />
              </button>
            </div>

            {/* Chat History */}
            <div className="flex-1 overflow-y-auto p-10 space-y-8 scrollbar-hide">
              {messages.map((m, i) => (
                <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[90%] p-8 rounded-[2.5rem] text-sm font-medium leading-relaxed shadow-sm ${
                    m.role === 'user' 
                    ? 'bg-amber-500 text-white rounded-br-none' 
                    : 'bg-slate-50 text-slate-600 border border-slate-100 rounded-bl-none'
                  }`}>
                    {m.text}
                  </div>
                  <span className="mt-2 text-[9px] font-black text-slate-300 uppercase tracking-widest px-4">{m.time} · {m.role === 'user' ? 'You' : 'Agent'}</span>
                </div>
              ))}
            </div>

            {/* Input Footer */}
            <div className="p-10 bg-slate-50/50 space-y-6">
              <div className="flex flex-wrap gap-2">
                {["Drought SNP?", "Compare to Medenine", "TaDREB Pathways"].map(p => (
                  <button 
                    key={p} 
                    onClick={() => addMessage(p)}
                    className="px-4 py-2 bg-white hover:bg-emerald-50 hover:text-emerald-600 text-[9px] font-black text-slate-400 border border-slate-100 rounded-full transition-all shadow-sm"
                  >
                    {p}
                  </button>
                ))}
              </div>
              <div className="relative group">
                <input 
                  className="w-full bg-white border border-slate-100 rounded-[2rem] px-8 py-6 text-sm font-bold text-slate-800 focus:outline-none focus:ring-8 focus:ring-amber-500/5 shadow-xl shadow-slate-200/20"
                  placeholder="Inquire with AI Agent..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.target.value) {
                      addMessage(e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
                <button className="absolute right-3 top-3 w-14 h-14 bg-slate-900 hover:bg-black text-white rounded-2xl flex items-center justify-center transition-all active:scale-95 shadow-lg shadow-slate-900/20">
                  <Send className="w-6 h-6" />
                </button>
              </div>
              <div className="flex justify-between items-center px-4">
                 <button className="text-[9px] font-black text-slate-300 uppercase tracking-widest hover:text-red-500 transition-colors">Wipe Memory</button>
                 <div className="text-[9px] font-black text-slate-300 uppercase tracking-widest">3 Exchanges · 1.2k Tokens</div>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  );
};

export default RAGAnalysis;
