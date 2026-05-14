import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Home, Languages, Menu, ArrowRight, Volume2 } from 'lucide-react'
import { useTranslation } from '../hooks/useTranslation'
import { speak } from '../utils/tts'
import AgriAgent from '../components/AgriAgent'

const FarmerDashboard = () => {
  const navigate = useNavigate()
  const { t, language, toggleLanguage } = useTranslation('derja')
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const handleTTS = (text) => {
    speak(text, language === 'derja' ? 'derja' : 'fr-FR')
  }

  const actions = [
    {
      id: 'plant-sound',
      title: language === 'derja' ? 'صوت الزرع' : 'Son des Plantes',
      path: '/plant-sound',
      desc: language === 'derja' ? 'تتبع الري الذكي' : 'Suivi irrigation intelligente',
      color: 'from-emerald-400 to-emerald-600'
    },
    {
      id: 'plant-disease',
      title: language === 'derja' ? 'صحة النبات' : 'Santé des Plantes',
      path: '/plant-disease',
      desc: language === 'derja' ? 'كشف الأمراض بالصور' : 'Détection maladies par photo',
      color: 'from-blue-400 to-blue-600'
    },
    {
      id: 'insect-ai',
      title: language === 'derja' ? 'عالم الحشرات' : 'Monde des Insectes',
      path: '/insect-ai',
      desc: language === 'derja' ? 'تحليل بالذكاء الاصطناعي' : 'Analyse par IA',
      color: 'from-rose-400 to-rose-600'
    }
  ]

  return (
    <div className="min-h-screen relative flex flex-col font-sans selection:bg-emerald-100 overflow-hidden bg-slate-950" dir={language === 'derja' ? 'rtl' : 'ltr'}>
      {/* Background with SOFT BLUR */}
      <div className="absolute inset-0 z-0">
        <img 
          src="/assets/img/modern_industrial_farm_bg.png" 
          alt="Modern Farm" 
          className="w-full h-full object-cover blur-[4px] scale-105"
        />
        <div className="absolute inset-0 bg-slate-950/40" />
      </div>

      {/* DNA Icon */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="fixed left-10 top-1/2 -translate-y-1/2 z-40 hidden lg:flex flex-col items-center gap-2"
      >
        <div className="w-14 h-14 flex items-center justify-center relative">
          <div className="absolute inset-0 bg-emerald-500/20 blur-xl rounded-full animate-pulse" />
          <img 
            src="/assets/img/dna_custom_icon.png" 
            alt="DNA Icon" 
            className="w-full h-full object-contain relative z-10 filter drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]"
          />
        </div>
        <div className="h-24 w-0.5 bg-gradient-to-b from-emerald-500/50 via-emerald-500/20 to-transparent rounded-full" />
      </motion.div>

      {/* Header */}
      <header className={`p-8 flex justify-between items-center relative z-30 ${language === 'derja' ? 'flex-row-reverse' : ''}`}>
        <div className={`flex items-center gap-4 ${language === 'derja' ? 'flex-row-reverse' : ''}`}>
          <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center text-white backdrop-blur-2xl border border-white/10 shadow-2xl">
            <Home className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tighter uppercase text-white leading-none">AgriCulture</h1>
            <div className="h-0.5 w-full bg-emerald-500/50 mt-1 rounded-full" />
          </div>
        </div>

        <div className={`flex items-center gap-4 ${language === 'derja' ? 'flex-row-reverse' : ''}`}>
          <button 
            onClick={toggleLanguage}
            className="text-white/80 hover:text-white transition-all flex items-center gap-2 text-[10px] font-black bg-white/5 px-6 py-2.5 rounded-2xl backdrop-blur-2xl border border-white/10 shadow-lg"
          >
            <Languages className="w-4 h-4" />
            <span>{t('lang_toggle')}</span>
          </button>
          <button 
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-white backdrop-blur-2xl border border-white/10 shadow-lg"
          >
            <Menu className="w-6 h-6" />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow p-6 flex flex-col relative z-10 max-w-6xl mx-auto w-full justify-center">
        <div className="mb-16 text-center">
          <motion.h2 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-6xl sm:text-7xl font-black text-white tracking-tighter mb-4 drop-shadow-2xl"
          >
            {t('welcome')}, <span className="text-emerald-400">مجد</span>
          </motion.h2>
          <p className="text-white/40 text-xs font-bold uppercase tracking-[0.5em]">{t('portal')}</p>
        </div>

        {/* Simplified Action Cards */}
        <div className="grid sm:grid-cols-3 gap-10">
          {actions.map((action, idx) => (
            <motion.div
              key={action.id}
              initial={{ opacity: 0, y: 40 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1, duration: 0.8 }}
              whileHover={{ y: -15, scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate(action.path)}
              className="relative group p-10 bg-white/5 backdrop-blur-3xl rounded-[3rem] border border-white/10 hover:border-emerald-500/50 transition-all text-center shadow-2xl cursor-pointer overflow-hidden"
            >
              <div className={`absolute inset-0 bg-gradient-to-br ${action.color} opacity-0 group-hover:opacity-10 transition-opacity`} />
              
              <div className="relative z-10 space-y-4">
                <h3 className={`text-3xl font-black text-white ${language === 'derja' ? 'font-sans' : ''}`}>{action.title}</h3>
                <p className="text-white/40 text-[11px] font-bold uppercase tracking-[0.2em]">
                  {action.desc}
                </p>
              </div>

              <div className="relative z-10 mt-12 flex items-center justify-center gap-4">
                <div
                  role="button"
                  tabIndex={0}
                  onClick={(e) => { e.stopPropagation(); handleTTS(action.title); }}
                  className="w-12 h-12 rounded-2xl bg-white/5 flex items-center justify-center text-white/30 hover:text-emerald-400 transition-colors border border-white/5"
                >
                  <Volume2 className="w-5 h-5" />
                </div>
                <div className="w-14 h-14 rounded-full bg-emerald-500 flex items-center justify-center text-white shadow-lg group-hover:bg-emerald-400 transition-all">
                  <ArrowRight className={`w-7 h-7 ${language === 'derja' ? 'rotate-180' : ''}`} />
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </main>

      {/* Unified AgriAgent */}
      <AgriAgent />
    </div>
  )
}

export default FarmerDashboard

