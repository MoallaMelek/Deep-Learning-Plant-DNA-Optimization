import React, { useRef, useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import { 
  Search, 
  Database, 
  ArrowRight, 
  FlaskConical, 
  Sprout, 
  ShieldCheck, 
  Dna, 
  MessageSquare, 
  Zap, 
  Loader2, 
  ChevronRight, 
  Layers, 
  Cpu, 
  ExternalLink, 
  Download, 
  Clock, 
  CheckCircle2, 
  BookOpen,
  Info,
  Settings2,
  Send,
  Terminal
} from 'lucide-react'
import RAGSearch from '../components/RAGSearch'

// --- Shared Components for Results (Ported from RAGAnalysis) ---

const Typewriter = ({ text, onComplete }) => {
  const [currentText, setCurrentText] = useState("");
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (index < text.length) {
      const timeout = setTimeout(() => {
        setCurrentText(prev => prev + text[index]);
        setIndex(prev => prev + 1);
      }, 5);
      return () => clearTimeout(timeout);
    } else if (onComplete) {
      onComplete();
    }
  }, [index, text, onComplete]);

  const formatTextWithLinks = (content) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    return content.split(urlRegex).map((part, i) => {
      if (part.match(urlRegex)) {
        return <a key={i} href={part} target="_blank" rel="noopener noreferrer" className="text-emerald-500 hover:text-emerald-600 hover:underline">{part}</a>;
      }
      return part;
    });
  };

  return <span>{formatTextWithLinks(currentText)}</span>;
};

const ResultCard = ({ result }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="bg-white rounded-[2.5rem] border border-slate-100 hover:border-emerald-300 transition-all p-8 shadow-sm hover:shadow-xl group relative overflow-hidden"
  >
    <div className="absolute top-0 right-0 p-6 flex gap-2">
      <div className="bg-emerald-50 text-emerald-600 px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest">
        Match {result.confidence ? (result.confidence * 100).toFixed(1) : 0}%
      </div>
      <div className="bg-slate-50 text-slate-400 px-3 py-1 rounded-full text-[9px] font-black uppercase tracking-widest">
        #{result.rank}
      </div>
    </div>

    <div className="flex items-center gap-6 mb-8">
      <div className="w-14 h-14 bg-emerald-500 text-white rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20 group-hover:scale-110 transition-transform">
        <Dna className="w-7 h-7" />
      </div>
      <div>
        <h4 className="text-xl font-black text-slate-900 tracking-tight leading-none mb-2">{result.gene_name}</h4>
        <div className="text-[10px] font-black text-slate-300 uppercase tracking-widest flex items-center gap-2">
          Accession: <a 
            href={`https://www.ncbi.nlm.nih.gov/nuccore/${result.accession}`} 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-emerald-600 hover:text-emerald-500 hover:underline transition-colors"
          >
            {result.accession}
          </a>
        </div>
      </div>
    </div>

    <div className="grid grid-cols-3 gap-4 mb-8">
      {[
        { label: 'Sparse', val: result.signals.sparse, col: 'bg-blue-50 text-blue-600' },
        { label: 'DNABERT', val: result.signals.dnabert, col: 'bg-purple-50 text-purple-600' },
        { label: 'K-Mer', val: result.signals.kmer, col: 'bg-amber-50 text-amber-600' }
      ].map(s => (
        <div key={s.label} className={`${s.col} p-4 rounded-3xl text-center border border-current/5`}>
          <div className="text-[8px] font-black uppercase tracking-widest opacity-60 mb-1">{s.label}</div>
          <div className="text-sm font-black font-mono">{(s.val * 100).toFixed(0)}%</div>
        </div>
      ))}
    </div>

    <div className="space-y-4">
      <div className="flex items-center justify-between px-2">
        <div className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Sequence Preview</div>
        <div className="text-[9px] font-black text-emerald-500 uppercase tracking-widest cursor-pointer hover:underline">Full View</div>
      </div>
      <div className="bg-slate-50 rounded-2xl p-5 font-mono text-[10px] text-slate-400 break-all leading-relaxed border border-slate-100 group-hover:bg-white group-hover:border-emerald-100 transition-colors">
        {result.sequence_preview}
      </div>
      {result.publication && (
        <div className="px-2 pt-2">
          <div className="text-[8px] font-black text-slate-300 uppercase tracking-widest mb-1">Source Publication</div>
          <div className="text-[10px] font-bold text-slate-500 leading-tight">
            {result.publication} 
            {result.pmid && (
              <a 
                href={`https://pubmed.ncbi.nlm.nih.gov/${result.pmid}`} 
                target="_blank" 
                rel="noopener noreferrer"
                className="ml-2 text-emerald-600 hover:underline inline-flex items-center gap-1"
              >
                PMID:{result.pmid} <ExternalLink className="w-2 h-2" />
              </a>
            )}
          </div>
        </div>
      )}
    </div>

    <div className="mt-8 pt-6 border-t border-slate-50 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Trait: {result.trait}</span>
      </div>
      <div className="flex items-center gap-4">
        <button 
          onClick={async () => {
            try {
              const res = await fetch('http://127.0.0.1:5007/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  sequence: result.sequence || result.sequence_preview, 
                  accession: result.accession,
                  gene: result.gene_name,
                  species: 'Triticum durum'
                })
              });
              if (!res.ok) throw new Error('PDF generation failed');
              const blob = await res.blob();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `report_${result.accession}.pdf`;
              a.click();
            } catch (err) {
              alert("PDF Export Error: " + err.message);
            }
          }}
          className="flex items-center gap-2 text-[9px] font-black text-blue-600 uppercase tracking-[0.2em] hover:text-blue-700 transition-colors"
        >
          <Download className="w-3 h-3" /> PDF Report
        </button>
        <button className="flex items-center gap-2 text-[9px] font-black text-slate-900 uppercase tracking-[0.2em] group-hover:text-emerald-600 transition-colors">
          Sequence Details <ArrowRight className="w-3 h-3 transition-transform group-hover:translate-x-1" />
        </button>
      </div>
    </div>
  </motion.div>
);

const BackgroundPatterns = () => (
  <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden opacity-30">
    <div className="absolute top-0 right-0 w-[800px] h-[800px] bg-emerald-500/5 blur-[120px] rounded-full -translate-y-1/2 translate-x-1/3" />
    <div className="absolute bottom-0 left-0 w-[600px] h-[600px] bg-blue-500/5 blur-[100px] rounded-full translate-y-1/3 -translate-x-1/4" />
    <div className="absolute top-1/4 left-1/3 w-[300px] h-[300px] bg-purple-500/5 blur-[80px] rounded-full" />
  </div>
);

// --- Home Page Main Component ---

const API_BASE = 'http://127.0.0.1:8000/api'

const Home = () => {
  const scrollRef = useRef(null)
  const resultsRef = useRef(null)
  
  // RAG States
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState([])
  const [answer, setAnswer] = useState(null)
  const [agentOpen, setAgentOpen] = useState(false)
  const [streamingComplete, setStreamingComplete] = useState(false)
  const [messages, setMessages] = useState([
    { role: 'ai', text: "GenoNexus Online. Accessing 3,998 sequences. How can I help with your genomic research?", time: 'Now' }
  ])

  const scroll = (direction) => {
    if (scrollRef.current) {
      const { scrollLeft, clientWidth } = scrollRef.current
      const scrollTo = direction === 'left' ? scrollLeft - clientWidth / 2 : scrollLeft + clientWidth / 2
      scrollRef.current.scrollTo({ left: scrollTo, behavior: 'smooth' })
    }
  }

  // Triggered when RAGSearch submits
  const handleSearchTrigger = async (queryData) => {
    setLoading(true)
    setResults([])
    setAnswer(null)
    setStreamingComplete(false)
    
    try {
      // Production FastAPI Call directly to Module 7 Server
      const payload = {
        question: queryData.query || queryData,
        query: queryData.query || queryData,
        mode: 'text',
        top_k: 5,
        search_mode: 'rag'
      };

      const response = await fetch('http://127.0.0.1:5007/rag', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) throw new Error(`Server error: ${response.status}`);
      const data = await response.json();
      
      const mapped = (data.sequences || []).map((r, i) => ({
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
        sequence: r.sequence || '',
        sequence_preview: r.sequence ? r.sequence.substring(0, 100) + '...' : (r.description || ''),
        publication: r.publication || '',
        pmid: r.pmid || ''
      }));

      setResults(mapped);
      
      if (data.answer) {
        setAnswer({
          text: data.answer,
          citations: (data.articles || []).map((a, i) => ({
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
  }

  const addMessage = (text, role = 'user') => {
    setMessages(prev => [...prev, { role, text, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }]);
  };

  return (
    <div className={`relative transition-all duration-500 ${agentOpen ? 'pr-[450px]' : ''}`}>
      {/* Hero Section with Search Engine */}
      <section className="relative min-h-[95vh] flex items-center justify-center">
        {/* Background "Video" Mockup */}
        <div className="absolute inset-0 z-0 bg-slate-900 overflow-hidden">
          <div className="absolute inset-0 bg-slate-900/60 z-10 pointer-events-none" />
          <iframe 
            className="absolute inset-0 w-full h-full scale-150 pointer-events-none"
            src="https://www.youtube.com/embed/Ars8JB-g4p8?autoplay=1&mute=1&loop=1&playlist=Ars8JB-g4p8&controls=0&showinfo=0&rel=0&iv_load_policy=3&modestbranding=1" 
            title="Researcher Background"
            frameBorder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowFullScreen
          />
        </div>

        <div className="relative z-20 container mx-auto px-4 text-center">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <h1 className="text-5xl md:text-8xl font-black text-white mb-6 tracking-tighter">
              Geno<span className="text-emerald-400">Nexus</span>.
            </h1>
            <p className="text-lg md:text-xl font-bold text-emerald-400 uppercase tracking-[0.4em] mb-8">
              The CropDNA Project
            </p>
            <p className="text-xl text-slate-100 mb-12 max-w-3xl mx-auto font-medium leading-relaxed">
              Bridging traditional farming with advanced DNA analysis, genomic search, and AI-driven insights through an autonomous hybrid retrieval pipeline.
            </p>

            {/* Genomic Search Engine (RAG Integrated) */}
            <div className="mt-12 relative max-w-4xl mx-auto">
              <RAGSearch onSearch={handleSearchTrigger} loading={loading} />
              
              {/* Stats Bar Below Search */}
              <div className="mt-8 flex flex-wrap justify-center gap-8 opacity-60">
                 {[
                  { label: 'DB Sequences', val: '3,998', icon: Database },
                  { label: 'SNP Features', val: '159', icon: Layers },
                  { label: 'Signals', val: '3 Hybrid', icon: Cpu }
                ].map(stat => (
                  <div key={stat.label} className="flex items-center gap-3 text-white">
                    <stat.icon className="w-4 h-4 text-emerald-400" />
                    <div className="text-left">
                      <div className="text-[8px] font-black uppercase tracking-widest leading-none">{stat.label}</div>
                      <div className="text-xs font-black font-mono">{stat.val}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Quick Toggle for Agent */}
            <button 
              onClick={() => setAgentOpen(!agentOpen)}
              className="mt-10 px-8 py-3.5 bg-white/10 hover:bg-white/20 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-widest text-emerald-400 border border-white/10 transition-all flex items-center gap-3 mx-auto"
            >
              <Zap className="w-4 h-4" /> {agentOpen ? 'Close DNA Agent' : 'Activate DNA Agent'}
            </button>
          </motion.div>
        </div>
      </section>

      {/* RAG Results Display (Dynamic Part) */}
      <AnimatePresence>
        {(loading || results.length > 0 || answer) && (
          <motion.section 
            ref={resultsRef}
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            className="py-24 bg-slate-50 relative overflow-hidden"
          >
             {/* Technical Grid Background */}
            <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(#10b981 0.5px, transparent 0.5px)', backgroundSize: '48px 48px' }} />
            
            <div className="container mx-auto px-4 max-w-[1400px] relative z-10">
              <div className="grid lg:grid-cols-2 gap-12 items-start">
                {/* AI Answer Column */}
                <div className="space-y-10">
                  <AnimatePresence>
                    {answer && (
                      <motion.div 
                        initial={{ opacity: 0, x: -30 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="bg-white rounded-[3.5rem] p-10 border-2 border-emerald-500/10 shadow-2xl relative overflow-hidden h-full"
                      >
                        <div className="absolute top-0 right-0 p-8">
                          <div className="bg-emerald-50 text-white px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-[0.2em] shadow-lg shadow-emerald-500/30 flex items-center gap-2">
                            <div className="w-2 h-2 bg-white rounded-full animate-pulse" /> AI INSIGHT
                          </div>
                        </div>

                        <div className="flex items-center gap-6 mb-10">
                          <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center shadow-inner">
                            <MessageSquare className="w-8 h-8" />
                          </div>
                          <h3 className="text-3xl font-black text-slate-900 tracking-tighter">GenoNexus Synthesis</h3>
                        </div>

                        <div className="text-xl font-medium text-slate-700 leading-relaxed mb-12 border-l-8 border-emerald-500/10 pl-10">
                          <Typewriter text={answer.text} onComplete={() => setStreamingComplete(true)} />
                          {!streamingComplete && <motion.span animate={{ opacity: [0, 1, 0] }} transition={{ repeat: Infinity, duration: 0.8 }} className="inline-block w-3 h-8 bg-emerald-500 ml-1 translate-y-1" />}
                        </div>

                        {streamingComplete && (
                          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8 animate-in fade-in duration-1000">
                            <div className="text-[10px] font-black uppercase tracking-[0.4em] text-slate-300 px-2">Source Citations</div>
                            <div className="grid gap-4">
                              {answer.citations.map(cite => (
                                <a href={cite.pmid ? `https://pubmed.ncbi.nlm.nih.gov/${cite.pmid}/` : cite.url || '#'} target="_blank" rel="noopener noreferrer" key={cite.index} className="bg-slate-50/50 p-6 rounded-[2rem] border border-slate-100 hover:border-emerald-300 transition-all group cursor-pointer shadow-sm block">
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
                            <div className="pt-8 border-t border-slate-100 flex items-center justify-between text-[10px] font-black text-slate-400 uppercase tracking-widest">
                               <span>{answer.stats}</span>
                            </div>
                          </motion.div>
                        )}
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* Match Results Column */}
                <div className="space-y-10">
                  <div className="flex items-center justify-between px-6">
                     <h3 className="text-3xl font-black tracking-tighter text-slate-900">Genomic Matches</h3>
                     <div className="text-[10px] font-black text-slate-400 uppercase tracking-widest">3,998 Records</div>
                  </div>
                  <div className="grid gap-8">
                    {loading && results.length === 0 && (
                      [...Array(2)].map((_, i) => <div key={i} className="h-64 bg-white animate-pulse rounded-[2.5rem] border border-slate-100" />)
                    )}
                    {results.map(r => <ResultCard key={r.rank} result={r} />)}
                  </div>
                </div>
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      {/* Services Grid Section */}
      <section className="py-24 bg-white">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <p className="text-emerald-600 font-bold uppercase tracking-widest text-sm mb-2">Scientific Solutions</p>
            <h2 className="text-4xl font-black text-slate-900 tracking-tight">Advanced Genomic Services</h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 border-l border-t border-slate-100">
            {[
              { title: "Genomic Mapping", icon: <Database className="w-8 h-8" />, desc: "Comprehensive indexing and mapping of complex plant DNA sequences." },
              { title: "Trait Identification", icon: <Search className="w-8 h-8" />, desc: "AI-driven markers for detecting drought and pest resistance traits." },
              { title: "CRISPR Simulation", icon: <FlaskConical className="w-8 h-8" />, desc: "Virtual gene-editing models to predict outcomes before lab work." },
              { title: "Neural Crossing", icon: <Dna className="w-8 h-8" />, desc: "LSTM-powered breeding recommendations for optimal crop yields." },
              { title: "Pharma Synthesis", icon: <Sprout className="w-8 h-8" />, desc: "Designing plants as bioreactors for high-value medicinal compounds." },
              { title: "Ethical Auditing", icon: <ShieldCheck className="w-8 h-8" />, desc: "Real-time compliance monitoring for international genomic standards." },
              { title: "Phenotype Projection", icon: <ArrowRight className="w-8 h-8" />, desc: "Advanced projections of plant growth and yield based on DNA markers." },
              { title: "Data Archiving", icon: <Database className="w-8 h-8" />, desc: "Secure, high-scale storage for massive genomic and research datasets." }
            ].map((service, idx) => (
              <div key={idx} className="p-10 border-r border-b border-slate-100 hover:bg-slate-50 transition-colors group relative">
                <span className="absolute top-4 right-6 text-slate-200 font-bold text-sm">0{idx + 1}</span>
                <div className="text-emerald-600 mb-6 group-hover:scale-110 transition-transform duration-300">
                  {service.icon}
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">{service.title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">
                  {service.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Case Studies Carousel Section */}
      <section className="py-24 bg-white overflow-hidden">
        <style dangerouslySetInnerHTML={{__html: `
          .no-scrollbar::-webkit-scrollbar { display: none; }
          .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        `}} />
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row justify-between items-end mb-16 gap-6">
            <div>
              <p className="text-emerald-600 font-bold uppercase tracking-widest text-sm mb-2">Research in Action</p>
              <h2 className="text-4xl font-black text-slate-900 tracking-tight">Scientific Case Studies</h2>
            </div>
            <div className="flex gap-4">
              <button 
                onClick={() => scroll('left')}
                className="w-12 h-12 rounded-full border border-slate-200 flex items-center justify-center hover:bg-slate-50 transition-all text-slate-400 hover:text-emerald-600"
              >
                <ArrowRight className="w-6 h-6 rotate-180" />
              </button>
              <button 
                onClick={() => scroll('right')}
                className="w-12 h-12 rounded-full bg-emerald-600 flex items-center justify-center hover:bg-emerald-700 transition-all text-white shadow-lg shadow-emerald-200"
              >
                <ArrowRight className="w-6 h-6" />
              </button>
            </div>
          </div>

          <div 
            ref={scrollRef}
            className="flex gap-8 overflow-x-auto no-scrollbar pb-12 snap-x"
          >
            {[
              { title: "Arctic Wheat Simulation", category: "DNA RESILIENCE", img: "/assets/img/hero_2.jpg", color: "from-blue-500 to-cyan-400" },
              { title: "Desert Corn Engineering", category: "CLIMATE ADAPTATION", img: "/assets/img/hero_3.jpg", color: "from-orange-500 to-yellow-400" },
              { title: "Bio-Insulin Harvest", category: "PHARMA SYNTHESIS", img: "/assets/img/hero_4.jpg", color: "from-purple-500 to-pink-400" },
              { title: "Pest-Resistant Rice", category: "IMMUNITY EDITING", img: "/assets/img/hero_5.jpg", color: "from-emerald-500 to-teal-400" }
            ].map((study, idx) => (
              <motion.div 
                key={idx}
                whileHover={{ y: -10 }}
                className="min-w-[350px] md:min-w-[450px] group cursor-pointer snap-start"
              >
                <div className="relative h-[500px] rounded-[3rem] overflow-hidden mb-8 shadow-xl">
                  <img 
                    src={study.img} 
                    alt={study.title}
                    className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
                  />
                  <div className={`absolute inset-0 bg-gradient-to-br ${study.color} opacity-0 group-hover:opacity-20 transition-opacity duration-500`} />
                  
                  {/* Floating Badge */}
                  <div className="absolute top-6 left-6">
                    <span className="px-4 py-2 bg-white/90 backdrop-blur-md rounded-full text-[10px] font-black tracking-widest text-slate-900 shadow-lg">
                      {study.category}
                    </span>
                  </div>
                </div>
                
                <div className="px-4">
                  <h3 className="text-2xl font-bold text-slate-900 group-hover:text-emerald-600 transition-colors duration-300">
                    {study.title}
                  </h3>
                  <div className="w-12 h-1 bg-slate-100 mt-4 group-hover:w-24 group-hover:bg-emerald-500 transition-all duration-500" />
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Advanced Agent Sidebar (Fixed) */}
      <AnimatePresence>
        {agentOpen && (
          <motion.aside 
            initial={{ x: 500 }}
            animate={{ x: 0 }}
            exit={{ x: 500 }}
            className="fixed top-0 right-0 w-[450px] h-full bg-white shadow-[-30px_0_60px_rgba(0,0,0,0.1)] z-[100] flex flex-col border-l border-slate-100"
          >
            <div className="p-10 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-5">
                <div className="w-14 h-14 bg-amber-500 text-white rounded-[1.5rem] flex items-center justify-center shadow-xl shadow-amber-500/30"><Zap className="w-8 h-8" /></div>
                <div>
                  <h3 className="text-2xl font-black text-slate-900 tracking-tighter">DNA Agent</h3>
                  <div className="text-[10px] font-black text-amber-500 uppercase tracking-widest">Research Memory Active</div>
                </div>
              </div>
              <button onClick={() => setAgentOpen(false)} className="w-10 h-10 rounded-full bg-slate-50 flex items-center justify-center hover:bg-slate-100 transition-all"><ChevronRight className="w-6 h-6 text-slate-400" /></button>
            </div>

            <div className="flex-1 overflow-y-auto p-10 space-y-8 scrollbar-hide">
              {messages.map((m, i) => (
                <div key={i} className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}>
                  <div className={`max-w-[90%] p-6 rounded-[2rem] text-sm font-medium leading-relaxed shadow-sm ${
                    m.role === 'user' ? 'bg-amber-500 text-white rounded-br-none' : 'bg-slate-50 text-slate-500 border border-slate-100 rounded-bl-none'
                  }`}>
                    {m.text}
                  </div>
                  <span className="mt-2 text-[9px] font-black text-slate-300 uppercase tracking-widest px-4">{m.time} · {m.role === 'user' ? 'You' : 'Agent'}</span>
                </div>
              ))}
            </div>

            <div className="p-10 bg-slate-50/50 space-y-6">
              <div className="relative group">
                <input 
                  className="w-full bg-white border border-slate-100 rounded-[2rem] px-8 py-6 text-sm font-bold text-slate-800 focus:outline-none shadow-xl shadow-slate-200/20"
                  placeholder="Inquire with DNA Agent..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.target.value) {
                      addMessage(e.target.value);
                      e.target.value = '';
                    }
                  }}
                />
                <button className="absolute right-4 top-4 w-12 h-12 bg-slate-900 text-white rounded-2xl flex items-center justify-center shadow-lg active:scale-95"><Send className="w-6 h-6" /></button>
              </div>
              <button className="w-full text-[9px] font-black text-slate-300 uppercase tracking-widest hover:text-red-500 transition-colors">Reset Session History</button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </div>
  )
}

export default Home
