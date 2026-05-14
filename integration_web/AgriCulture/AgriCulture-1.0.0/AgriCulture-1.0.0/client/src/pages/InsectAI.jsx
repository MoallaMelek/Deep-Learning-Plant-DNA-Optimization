import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import {
  Zap, Activity, Settings, Database, Dna, ChevronRight,
  AlertCircle, CheckCircle2, RefreshCw, Cpu, Download,
  Terminal, FileText, Search, BarChart3, Info, Share2,
  FlaskConical, ArrowRight, Clipboard, Leaf, Bug, Mic,
  Image as ImageIcon, History, Trash2, ShieldAlert,
  Beaker, Waves, Volume2, Camera, HelpCircle, Globe
} from 'lucide-react';
import AgriAgent from '../components/AgriAgent';

const speak = (text) => {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.lang = 'ar-TN';
    utt.rate = 0.9;
    window.speechSynthesis.speak(utt);
  }
};

const TTSButton = ({ text, className = '' }) => (
  <button
    onClick={(e) => { e.stopPropagation(); speak(text); }}
    title="استمع"
    className={`w-10 h-10 flex items-center justify-center rounded-full bg-emerald-50 hover:bg-emerald-100 text-emerald-600 transition-all shadow-sm hover:scale-110 active:scale-95 ${className}`}
  >
    <Volume2 className="w-4 h-4" />
  </button>
);

// --- Constants ---
const API_BASE = 'http://127.0.0.1:8000/api';

const TRANSLATIONS = {
  en: {
    title: "InsectAI Studio",
    subtitle: "Identify pests from sound or photos to protect your crops.",
    soundTab: "Sound Analysis",
    imageTab: "Photo Analysis",
    step1: "Step 1: Upload",
    step1_desc: "Upload a recording or photo of the insect.",
    step2: "Step 2: Results",
    step3: "Step 3: AI Advice",
    classify: "Start Classification",
    analyzing: "AI is thinking...",
    danger: "Danger Level",
    solution: "Solution",
    farmer_advice: "Advice for you",
    history: "Recent Checks"
  },
  tn: {
    title: "InsectAI — كشف الحشرات",
    subtitle: "اعرف نوع الحشرة بالصوت ولا بالتصويرة باش تحمي صابتك.",
    soundTab: "تحليل الصوت",
    imageTab: "تحليل التصويرة",
    step1: "المرحلة 1: ابعث الملف",
    step1_desc: "ابعث تسجيل صوتي ولا تصويرة متاع الحشرة.",
    step2: "المرحلة 2: النتيجة",
    step3: "المرحلة 3: نصيحة الذكاء الاصطناعي",
    classify: "ابدا التحليل",
    analyzing: "الذكاء الاصطناعي يخدم...",
    danger: "درجة الخطورة",
    solution: "الحل",
    farmer_advice: "نصيحة ليك",
    history: "التحليلات الأخيرة"
  }
};

const BackgroundVisuals = () => (
  <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
    <motion.div
      animate={{ scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
      transition={{ duration: 15, repeat: Infinity }}
      className="absolute top-0 right-0 w-[800px] h-[800px] bg-emerald-50 rounded-full blur-[100px]"
    />
    <div
      className="absolute inset-0 opacity-[0.02]"
      style={{ backgroundImage: `radial-gradient(#10b981 1px, transparent 1px)`, backgroundSize: '50px 50px' }}
    />
  </div>
);

const InsectAI = () => {
  const [lang, setLang] = useState('tn'); // Default to Tunisian Derja for user-friendliness
  const [activeMode, setActiveMode] = useState('sound');
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [history, setHistory] = useState([]);

  const t = TRANSLATIONS[lang];

  const handleFileUpload = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setAiAnalysis(null);
    if (activeMode === 'image') {
      const reader = new FileReader();
      reader.onloadend = () => setPreview(reader.result);
      reader.readAsDataURL(f);
    } else {
      setPreview('audio-preview');
    }
  };

  const runInference = async () => {
    setLoading(true);
    setResult(null);
    setAiAnalysis(null);

    try {
      await new Promise(r => setTimeout(r, 2000));
      const mockResult = activeMode === 'sound'
        ? { species: "Gryllus_bimaculatus", confidence: 0.874 }
        : { species: "army_worm", confidence: 0.921 };
      setResult(mockResult);
      setHistory([{ ...mockResult, mode: activeMode, time: new Date() }, ...history].slice(0, 5));
    } finally {
      setLoading(false);
    }
  };

  const getAiAnalysis = async () => {
    setLoading(true);
    try {
      await new Promise(r => setTimeout(r, 2500));
      setAiAnalysis({
        danger: "Medium",
        crops: ["Wheat", "Vegetables"],
        action: "Apply bait traps at field margins immediately.",
        summary_tn: "هذا صرار الحقول، ينجم يهلك النبتات الصغيرة. احسن حاجة تعملها هي تحط الفخاخ في جناب السانية باش توقفو قبل ما ينتشر."
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`min-h-screen bg-[#fcfdfe] font-sans text-slate-900 selection:bg-emerald-500/10 relative overflow-hidden ${lang === 'tn' ? 'dir-rtl' : ''}`} dir={lang === 'tn' ? 'rtl' : 'ltr'}>
      <BackgroundVisuals />

      <main className="relative z-10 max-w-6xl mx-auto px-6 py-16">

        {/* Farmer-Friendly Header */}
        <div className="flex flex-col md:flex-row justify-between items-start gap-8 mb-16">
          <div className="space-y-4 flex-1">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-emerald-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-emerald-200">
                <Bug className="w-7 h-7" />
              </div>
              <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900">
                {t.title}
              </h1>
              <TTSButton text={t.title} />
            </div>
            <div className="flex items-center gap-3">
              <p className="text-slate-500 text-lg font-medium max-w-2xl leading-relaxed">
                {t.subtitle}
              </p>
              <TTSButton text={t.subtitle} />
            </div>
          </div>

          {/* Language toggle — icon only */}
          <div className="flex items-center gap-2 bg-white p-2 rounded-2xl border border-slate-100 shadow-sm">
            <Globe className="w-4 h-4 text-slate-300 mx-1" />
            <button
              onClick={() => setLang('tn')}
              title="Tounsi"
              className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black transition-all ${lang === 'tn' ? 'bg-emerald-600 text-white shadow-md' : 'text-slate-400 hover:bg-slate-50'}`}
            >ع</button>
            <button
              onClick={() => setLang('en')}
              title="English"
              className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-black transition-all ${lang === 'en' ? 'bg-emerald-600 text-white shadow-md' : 'text-slate-400 hover:bg-slate-50'}`}
            >En</button>
          </div>
        </div>

        {/* Action Selection */}
        <div className="grid md:grid-cols-2 gap-6 mb-12">
          <button
            onClick={() => { setActiveMode('sound'); setFile(null); setResult(null); }}
            className={`group relative p-8 rounded-[2.5rem] border-2 transition-all flex items-center gap-6 ${activeMode === 'sound' ? 'bg-emerald-600 border-emerald-600 text-white shadow-2xl shadow-emerald-200' : 'bg-white border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/30'}`}
          >
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${activeMode === 'sound' ? 'bg-white/20 text-white' : 'bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100'}`}>
              <Volume2 className="w-8 h-8" />
            </div>
            <div className="text-left rtl:text-right">
              <h3 className="text-xl font-black leading-none mb-2">{t.soundTab}</h3>
              <p className={`text-xs font-bold ${activeMode === 'sound' ? 'text-emerald-100' : 'text-slate-400'}`}>سجل صوت الحشرة</p>
            </div>
            {activeMode === 'sound' && <div className="absolute top-4 right-4 rtl:left-4 rtl:right-auto w-2 h-2 bg-white rounded-full animate-pulse" />}
          </button>

          <button
            onClick={() => { setActiveMode('image'); setFile(null); setResult(null); }}
            className={`group relative p-8 rounded-[2.5rem] border-2 transition-all flex items-center gap-6 ${activeMode === 'image' ? 'bg-emerald-600 border-emerald-600 text-white shadow-2xl shadow-emerald-200' : 'bg-white border-slate-100 hover:border-emerald-200 hover:bg-emerald-50/30'}`}
          >
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-colors ${activeMode === 'image' ? 'bg-white/20 text-white' : 'bg-emerald-50 text-emerald-600 group-hover:bg-emerald-100'}`}>
              <Camera className="w-8 h-8" />
            </div>
            <div className="text-left rtl:text-right">
              <h3 className="text-xl font-black leading-none mb-2">{t.imageTab}</h3>
              <p className={`text-xs font-bold ${activeMode === 'image' ? 'text-emerald-100' : 'text-slate-400'}`}>صور الحشرة بالكاميرا</p>
            </div>
            {activeMode === 'image' && <div className="absolute top-4 right-4 rtl:left-4 rtl:right-auto w-2 h-2 bg-white rounded-full animate-pulse" />}
          </button>
        </div>

        <div className="grid lg:grid-cols-12 gap-12 items-start">

          {/* Workflow Card */}
          <div className="lg:col-span-8 space-y-8">
            <div className="bg-white border border-slate-100 rounded-[3rem] p-10 shadow-2xl shadow-slate-200/20">
              <div className="flex items-center gap-4 mb-10">
                <div className="w-8 h-8 bg-slate-900 text-white rounded-full flex items-center justify-center text-[10px] font-black italic">1</div>
                <h3 className="text-xl font-black tracking-tight">{t.step1}</h3>
              </div>

              <div className="group relative h-72 border-4 border-dashed border-slate-100 rounded-[3rem] flex flex-col items-center justify-center transition-all hover:border-emerald-500/30 hover:bg-emerald-50/10 cursor-pointer overflow-hidden">
                <input type="file" onChange={handleFileUpload} className="absolute inset-0 opacity-0 cursor-pointer z-10" />

                <AnimatePresence mode="wait">
                  {preview ? (
                    <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center gap-6">
                      {activeMode === 'image' ? (
                        <img src={preview} alt="preview" className="h-40 rounded-3xl shadow-2xl border-4 border-white" />
                      ) : (
                        <div className="flex gap-2 items-center h-16">
                          {[...Array(12)].map((_, i) => (
                            <motion.div key={i} animate={{ height: [15, 60, 15] }} transition={{ duration: 1, repeat: Infinity, delay: i * 0.1 }} className="w-2 bg-emerald-500 rounded-full" />
                          ))}
                        </div>
                      )}
                      <div className="px-6 py-2 bg-emerald-600 text-white rounded-full text-[10px] font-black uppercase tracking-widest shadow-lg">
                        {file.name}
                      </div>
                    </motion.div>
                  ) : (
                    <div className="text-center space-y-6">
                      <div className="w-20 h-20 bg-slate-50 rounded-[2rem] flex items-center justify-center text-slate-200 mx-auto group-hover:rotate-12 transition-transform">
                        {activeMode === 'sound' ? <Mic className="w-10 h-10" /> : <ImageIcon className="w-10 h-10" />}
                      </div>
                      <div className="space-y-2">
                        <p className="text-xl font-black text-slate-400">{lang === 'tn' ? 'حط التسجيل ولا التصويرة هنا' : 'Drop your file here'}</p>
                        <p className="text-xs font-bold text-slate-300">{t.step1_desc}</p>
                      </div>
                    </div>
                  )}
                </AnimatePresence>
              </div>

              <button
                onClick={runInference}
                disabled={!file || loading}
                className="w-full mt-10 py-6 bg-slate-900 text-white rounded-[2rem] font-black text-sm uppercase tracking-[0.2em] shadow-xl hover:bg-emerald-600 transition-all disabled:opacity-50 flex items-center justify-center gap-4 group"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    <span>{t.analyzing}</span>
                  </>
                ) : (
                  <>
                    <span>{t.classify}</span>
                    <ArrowRight className={`w-5 h-5 group-hover:translate-x-2 transition-transform ${lang === 'tn' ? 'rotate-180 group-hover:-translate-x-2' : ''}`} />
                  </>
                )}
              </button>
            </div>

            {/* Result Card Section */}
            <AnimatePresence>
              {result && (
                <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} className="space-y-12">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
                    <div className="bg-white border border-slate-100 rounded-[3.5rem] p-12 shadow-2xl flex flex-col items-center justify-center text-center space-y-6 min-h-[320px]">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t.step2}</p>
                      <h2 className="text-4xl md:text-5xl font-black text-slate-900 leading-tight">{result.species.replace('_', ' ')}</h2>
                      <div className="px-8 py-3 bg-emerald-50 text-emerald-600 rounded-full text-xs font-black shadow-inner">
                        {(result.confidence * 100).toFixed(0)}% {lang === 'tn' ? 'متاكدين' : 'Confidence'}
                      </div>
                      <TTSButton text={result.species.replace('_', ' ')} className="mt-2" />
                    </div>

                    <div className="bg-white border border-slate-100 rounded-[3.5rem] p-12 shadow-2xl flex flex-col items-center justify-center text-center space-y-6 min-h-[320px]">
                      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{t.danger}</p>
                      <div className="text-5xl md:text-6xl font-black text-rose-600">!! المتوسطة !!</div>
                      <p className="text-xs font-bold text-slate-400 italic">{lang === 'tn' ? 'لازمك تاخذ بالك' : 'Requires monitoring'}</p>
                    </div>
                  </div>

                  <div className="bg-white border border-slate-100 rounded-[3rem] p-12 shadow-2xl space-y-10 relative overflow-hidden border-t-8 border-t-emerald-500">
                    <div className="flex flex-row items-center justify-between gap-6">
                      <h3 className="text-2xl md:text-3xl font-black tracking-tight">{t.step3}</h3>
                      {!aiAnalysis && (
                        <button onClick={getAiAnalysis} className="whitespace-nowrap px-8 py-4 bg-emerald-600 text-white rounded-2xl text-[11px] font-black uppercase tracking-widest hover:bg-emerald-700 shadow-lg shadow-emerald-200 transition-all flex items-center gap-3">
                          <RefreshCw className="w-4 h-4" /> {lang === 'tn' ? 'اعطيني النصيحة' : 'Get AI Advice'}
                        </button>
                      )}
                    </div>

                    {aiAnalysis ? (
                      <div className="space-y-10">
                        <div className="bg-emerald-50 p-10 rounded-[3rem] border border-emerald-100 relative">
                          <div className="flex items-center justify-between mb-4">
                            <h5 className="text-[11px] font-black uppercase tracking-widest text-emerald-600">{t.farmer_advice}</h5>
                            <TTSButton text={aiAnalysis.summary_tn} />
                          </div>
                          <p className="text-2xl font-bold text-slate-900 leading-relaxed">{aiAnalysis.summary_tn}</p>
                        </div>

                        <div className="grid sm:grid-cols-2 gap-8">
                          <div className="p-8 bg-white border border-slate-100 rounded-[2.5rem] shadow-xl">
                            <div className="w-12 h-12 bg-rose-50 text-rose-500 rounded-xl flex items-center justify-center mb-6"><ShieldAlert className="w-6 h-6" /></div>
                            <h6 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">{t.solution}</h6>
                            <p className="text-sm font-bold text-slate-700">{aiAnalysis.action}</p>
                          </div>
                          <div className="p-8 bg-white border border-slate-100 rounded-[2.5rem] shadow-xl">
                            <div className="w-12 h-12 bg-emerald-50 text-emerald-500 rounded-xl flex items-center justify-center mb-6"><Leaf className="w-6 h-6" /></div>
                            <h6 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">{lang === 'tn' ? 'الزراعات المهددة' : 'Affected Crops'}</h6>
                            <p className="text-sm font-bold text-slate-700">{aiAnalysis.crops.join(', ')}</p>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="h-40 flex items-center justify-center text-slate-300 font-bold italic">
                        {lang === 'tn' ? 'انقر على الزر للحصول على نصيحة كاملة...' : 'Click button for full AI guidance...'}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Right Panel: Support */}
          <div className="lg:col-span-4 space-y-8">
            <div className="bg-slate-900 rounded-[3rem] p-10 text-white shadow-2xl relative overflow-hidden">
              <HelpCircle className="absolute -bottom-4 -right-4 w-32 h-32 text-white/5" />
              <h4 className="text-xl font-black mb-6 italic">{lang === 'tn' ? 'تحتاج مساعدة؟' : 'Need Help?'}</h4>
              <div className="space-y-6">
                <div className="p-5 bg-white/5 rounded-2xl border border-white/10 text-xs font-medium leading-relaxed">
                  {lang === 'tn'
                    ? 'الذكاء الاصطناعي متاعنا يعرف اكثر من 20 نوع من الحشرات. برشة فلاحين يستعملو فيه باش يحميو محصولهم.'
                    : 'Our AI recognizes over 20 species. Farmers use this tool to save their harvest from pests early.'}
                </div>
                <button className="w-full py-4 bg-emerald-600 rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-emerald-700 transition-all">
                  {lang === 'tn' ? 'اتصل بخبير' : 'Call an Expert'}
                </button>
              </div>
            </div>

            <div className="bg-white border border-slate-100 rounded-[3rem] p-10 shadow-xl">
              <div className="flex items-center justify-between mb-8">
                <h4 className="text-lg font-black tracking-tight">{t.history}</h4>
                <History className="w-4 h-4 text-slate-300" />
              </div>
              <div className="space-y-4">
                {history.map((item, i) => (
                  <div key={i} className="flex items-center gap-4 p-4 bg-slate-50 rounded-2xl border border-slate-100">
                    <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center text-emerald-600 shadow-sm">
                      {item.mode === 'sound' ? <Mic className="w-5 h-5" /> : <Camera className="w-5 h-5" />}
                    </div>
                    <div className="flex-1">
                      <p className="text-[10px] font-black text-slate-900">{item.species}</p>
                      <p className="text-[8px] font-bold text-slate-400 mt-1 uppercase">{(item.confidence * 100).toFixed(0)}% Confidence</p>
                    </div>
                  </div>
                ))}
                {history.length === 0 && <p className="text-center text-xs text-slate-300 italic py-8">No recent checks</p>}
              </div>
            </div>
          </div>
        </div>

        {/* Technical Footer */}
        <div className="mt-40 pt-16 border-t border-slate-100 text-center space-y-4">
          <div className="flex items-center justify-center gap-4 opacity-30 grayscale">
            <Dna className="w-6 h-6" />
            <Cpu className="w-6 h-6" />
            <FlaskConical className="w-6 h-6" />
          </div>
          <p className="text-[10px] font-black text-slate-300 uppercase tracking-[0.4em]">InsectAI · Agriculture Intelligence · Tunisian Edition</p>
        </div>

        <AgriAgent />
      </main>
    </div>
  );
};

export default InsectAI;
