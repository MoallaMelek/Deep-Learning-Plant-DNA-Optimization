import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  ChevronLeft, 
  UploadCloud, 
  Image as ImageIcon, 
  Loader2, 
  CheckCircle2, 
  AlertTriangle, 
  Volume2, 
  Sparkles,
  Home,
  Languages,
  Activity
} from 'lucide-react';
import { useTranslation } from '../hooks/useTranslation';
import { speak } from '../utils/tts';
import AgriAgent from '../components/AgriAgent';

const API_BASE = 'http://127.0.0.1:8000/wheat';

const PlantDisease = () => {
  const navigate = useNavigate();
  const { t, language, toggleLanguage } = useTranslation('derja');
  
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleTTS = (text) => {
    speak(text, language === 'derja' ? 'derja' : 'fr-FR');
  };


  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreviewUrl(URL.createObjectURL(selectedFile));
      setResult(null);
      setError(null);
      
      handleTTS(msg);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile && droppedFile.type.startsWith('image/')) {
      setFile(droppedFile);
      setPreviewUrl(URL.createObjectURL(droppedFile));
      setResult(null);
      setError(null);
    }
  };

  const analyzeImage = async () => {
    if (!file) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    const formData = new FormData();
    formData.append('image', file);
    
    try {
      const response = await axios.post(`${API_BASE}/predict`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      const { prediction, confidence } = response.data;
      setResult({ prediction, confidence });
      
      const resultMsg = language === 'derja' 
        ? `النتيجة طلعت: ${prediction}. نسبة التأكد: ${Math.round(confidence * 100)} بالمية.`
        : `Le résultat est : ${prediction}. Confiance : ${Math.round(confidence * 100)} %.`;
      handleTTS(resultMsg);
      
    } catch (err) {
      console.error(err);
      setError(language === 'derja' ? 'صارت مشكلة في الاتصال بالسيرفر. عاود جرب.' : 'Erreur de connexion au serveur.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen relative flex flex-col font-sans selection:bg-emerald-100 overflow-x-hidden bg-slate-950" dir={language === 'derja' ? 'rtl' : 'ltr'}>
      {/* Background */}
      <div className="absolute inset-0 z-0">
        <img 
          src="/assets/img/modern_industrial_farm_bg.png" 
          alt="Modern Farm" 
          className="w-full h-full object-cover blur-[4px] scale-105"
        />
        <div className="absolute inset-0 bg-slate-950/60" />
      </div>

      {/* Header */}
      <header className={`p-8 flex justify-between items-center relative z-30 ${language === 'derja' ? 'flex-row-reverse' : ''}`}>
        <div className={`flex items-center gap-4 ${language === 'derja' ? 'flex-row-reverse' : ''}`}>
          <button onClick={() => navigate('/farmer-dashboard')} className="w-12 h-12 bg-white/5 hover:bg-white/10 transition-colors rounded-2xl flex items-center justify-center text-white backdrop-blur-2xl border border-white/10 shadow-2xl">
            <ChevronLeft className={`w-6 h-6 ${language === 'derja' ? 'rotate-180' : ''}`} />
          </button>
          <div>
            <h1 className="text-2xl font-black tracking-tighter uppercase text-white leading-none">AgriCulture</h1>
            <div className="h-0.5 w-full bg-blue-500/50 mt-1 rounded-full" />
          </div>
        </div>

        <button 
          onClick={toggleLanguage}
          className="text-white/80 hover:text-white transition-all flex items-center gap-2 text-[10px] font-black bg-white/5 px-6 py-2.5 rounded-2xl backdrop-blur-2xl border border-white/10 shadow-lg"
        >
          <Languages className="w-4 h-4" />
          <span>{t('lang_toggle')}</span>
        </button>
      </header>

      {/* Main Content */}
      <main className="flex-grow p-6 flex flex-col relative z-10 max-w-4xl mx-auto w-full justify-center">
        <div className="mb-10 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-blue-500/10 text-blue-400 rounded-full text-xs font-black uppercase tracking-widest border border-blue-500/20 mb-6">
            <Activity className="w-4 h-4" />
            {language === 'derja' ? 'تحليل ذكي بالأشعة' : 'Analyse Intelligente'}
          </div>
          <h2 className="text-4xl sm:text-6xl font-black text-white tracking-tighter mb-4 drop-shadow-2xl">
            {language === 'derja' ? 'تحليل أمراض ' : 'Analyse des '}
            <span className="text-blue-400">{language === 'derja' ? 'النباتات' : 'Plantes'}</span>
          </h2>
          <p className="text-white/50 text-lg font-medium max-w-2xl mx-auto">
            {language === 'derja' 
              ? 'ابعث تصويرة لأوراق الزرع باش نكتشفو كان فما مرض باستعمال الذكاء الاصطناعي (CNN).' 
              : 'Envoyez une photo des feuilles pour détecter d\'éventuelles maladies à l\'aide de l\'IA.'}
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 items-start">
          {/* Upload Section */}
          <motion.div 
            initial={{ opacity: 0, x: language === 'derja' ? 20 : -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white/5 backdrop-blur-3xl p-8 rounded-[3rem] border border-white/10 shadow-2xl relative overflow-hidden group"
          >
            <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />

            {!previewUrl ? (
              <label 
                className="border-2 border-dashed border-white/20 hover:border-blue-500/50 rounded-[2rem] p-12 text-center transition-all cursor-pointer bg-white/5 block w-full"
                onDragOver={handleDragOver}
                onDrop={handleDrop}
              >
                <input 
                  type="file" 
                  accept="image/*" 
                  className="hidden" 
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />
                <div className="w-20 h-20 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-6 text-blue-400">
                  <UploadCloud className="w-10 h-10" />
                </div>
                <h3 className="text-xl font-black text-white mb-2">{language === 'derja' ? 'حط تصويرتك هنا' : 'Déposez votre image'}</h3>
                <p className="text-white/40 text-sm font-medium">{language === 'derja' ? 'أو انزل باش تختار ملف' : 'ou cliquez pour parcourir'}</p>
              </label>
            ) : (
              <div className="relative rounded-[2rem] overflow-hidden border border-white/20 bg-black/50 aspect-square flex items-center justify-center">
                <img src={previewUrl} alt="Preview" className="max-w-full max-h-full object-contain" />
                <button 
                  onClick={() => setPreviewUrl(null)}
                  className="absolute top-4 right-4 bg-red-500/80 hover:bg-red-500 text-white p-2 rounded-xl backdrop-blur-md transition-colors"
                >
                  {language === 'derja' ? 'بدل التصويرة' : 'Changer'}
                </button>
              </div>
            )}

            <button 
              onClick={analyzeImage}
              disabled={!file || loading}
              className={`w-full mt-6 py-4 rounded-2xl font-black text-lg flex items-center justify-center gap-3 transition-all ${
                !file || loading 
                  ? 'bg-white/5 text-white/30 cursor-not-allowed border border-white/5' 
                  : 'bg-blue-500 hover:bg-blue-400 text-white shadow-[0_0_20px_rgba(59,130,246,0.3)]'
              }`}
            >
              {loading ? (
                <>
                  <Loader2 className="w-6 h-6 animate-spin" />
                  {language === 'derja' ? 'قاعد يحلل...' : 'Analyse...'}
                </>
              ) : (
                <>
                  <Sparkles className="w-6 h-6" />
                  {language === 'derja' ? 'ابدا الفحص' : 'Lancer l\'analyse'}
                </>
              )}
            </button>
          </motion.div>

          {/* Results Section */}
          <motion.div 
            initial={{ opacity: 0, x: language === 'derja' ? -20 : 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-white/5 backdrop-blur-3xl p-8 rounded-[3rem] border border-white/10 shadow-2xl h-full flex flex-col"
          >
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-2xl font-black text-white">{language === 'derja' ? 'النتيجة' : 'Résultat'}</h3>
              <button 
                onClick={() => handleTTS(agentMessage)}
                className="w-12 h-12 bg-white/5 hover:bg-white/10 rounded-2xl flex items-center justify-center text-white/50 hover:text-white transition-colors border border-white/5"
              >
                <Volume2 className="w-6 h-6" />
              </button>
            </div>

            <div className="flex-grow flex flex-col items-center justify-center text-center">
              {loading ? (
                <div className="space-y-6">
                  <div className="w-24 h-24 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mx-auto" />
                  <p className="text-white/60 font-medium animate-pulse">{language === 'derja' ? 'الذكاء الاصطناعي يخدم...' : 'L\'IA travaille...'}</p>
                </div>
              ) : error ? (
                <div className="bg-red-500/10 border border-red-500/20 p-6 rounded-3xl text-red-400">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-4" />
                  <p className="font-bold">{error}</p>
                </div>
              ) : result ? (
                <div className="space-y-8 w-full">
                  <div className="p-8 bg-blue-500/10 rounded-[2rem] border border-blue-500/20 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/20 rounded-full blur-3xl" />
                    <p className="text-white/50 text-xs font-bold uppercase tracking-widest mb-2">{language === 'derja' ? 'التشخيص' : 'Diagnostic'}</p>
                    <p className="text-4xl font-black text-white capitalize">{result.prediction}</p>
                  </div>
                  
                  <div className="space-y-3">
                    <div className="flex justify-between text-sm font-bold text-white/60">
                      <span>{language === 'derja' ? 'نسبة التأكد' : 'Confiance'}</span>
                      <span className="text-blue-400">{Math.round(result.confidence * 100)}%</span>
                    </div>
                    <div className="h-3 bg-white/5 rounded-full overflow-hidden border border-white/5">
                      <motion.div 
                        initial={{ width: 0 }}
                        animate={{ width: `${result.confidence * 100}%` }}
                        transition={{ duration: 1, ease: "easeOut" }}
                        className="h-full bg-gradient-to-r from-blue-600 to-blue-400"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-white/20">
                  <ImageIcon className="w-24 h-24 mx-auto mb-6 opacity-50" />
                  <p className="font-bold text-lg">{language === 'derja' ? 'النتيجة تطلع هنا' : 'Le résultat apparaîtra ici'}</p>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      </main>

      <AgriAgent />
    </div>
  );
};

export default PlantDisease;
