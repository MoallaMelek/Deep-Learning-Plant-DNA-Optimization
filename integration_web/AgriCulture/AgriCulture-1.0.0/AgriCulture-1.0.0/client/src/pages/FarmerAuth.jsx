import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { Phone, Lock, ArrowRight, ArrowLeft, Languages, CheckCircle2, ShieldCheck, Sparkles, Volume2 } from 'lucide-react'
import { useTranslation } from '../hooks/useTranslation'
import { speak } from '../utils/tts'

const FarmerAuth = () => {
  const navigate = useNavigate()
  const { t, language, toggleLanguage } = useTranslation('derja')
  const [isLogin, setIsLogin] = useState(true)

  const handleTTS = (text) => {
    speak(text, language === 'derja' ? 'derja' : 'fr-FR')
  }

  return (
    <div className="min-h-screen w-full bg-white flex flex-col lg:flex-row font-sans selection:bg-emerald-100" dir={language === 'derja' ? 'rtl' : 'ltr'}>
      
      {/* Left Side: Visual/Branding (Immersive) */}
      <div className="lg:w-1/2 relative overflow-hidden hidden lg:block">
        <img 
          src="/assets/img/farmer_login_bg.png" 
          alt="Farmer working" 
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-900 via-slate-900/40 to-transparent" />
        
        <div className={`absolute bottom-20 left-12 right-12 text-white ${language === 'derja' ? 'text-right' : 'text-left'}`}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-6"
          >
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-emerald-500 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <h2 className="text-4xl font-black text-white tracking-tighter leading-none">AgriCulture</h2>
            </div>
            <p className="text-xl font-medium text-slate-200 leading-relaxed max-w-md">
              {language === 'derja' 
                ? 'مرحباً بك في عالم الفلاحة العصرية. تبع زرعك وحسن انتاجك بكل سهولة.' 
                : 'Bienvenue dans le monde de l\'agriculture moderne. Suivez vos cultures et améliorez votre production.'}
            </p>
            <div className="flex gap-4 mt-4">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-emerald-400 bg-emerald-500/10 px-4 py-2 rounded-full border border-emerald-500/20">
                <CheckCircle2 className="w-4 h-4" /> 100% Secure
              </div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-blue-400 bg-blue-500/10 px-4 py-2 rounded-full border border-blue-500/20">
                <Sparkles className="w-4 h-4" /> AI Powered
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Side: Auth Form */}
      <div className="flex-grow flex flex-col items-center justify-center p-8 sm:p-12 lg:p-24 bg-white relative">
        {/* Top Controls */}
        <div className={`absolute top-8 left-8 right-8 flex justify-between items-center ${language === 'derja' ? 'flex-row-reverse' : ''}`}>
          <button 
            onClick={() => navigate('/')}
            className="text-slate-400 hover:text-slate-900 transition-colors flex items-center gap-2 text-xs font-bold uppercase tracking-widest"
          >
            <ArrowLeft className={`w-4 h-4 ${language === 'derja' ? 'rotate-180' : ''}`} />
            {t('back')}
          </button>
          <button 
            onClick={toggleLanguage}
            className="text-slate-400 hover:text-slate-900 transition-colors flex items-center gap-2 text-xs font-bold uppercase tracking-widest bg-slate-50 px-4 py-2 rounded-full border border-slate-100"
          >
            <Languages className="w-4 h-4 text-emerald-600" />
            {t('lang_toggle')}
          </button>
        </div>

        <div className="w-full max-w-md">
          <div className={`mb-12 ${language === 'derja' ? 'text-right' : 'text-left'}`}>
            <motion.h3 
              key={isLogin ? 'login' : 'signup'}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="text-4xl font-black text-slate-900 mb-4 tracking-tighter"
            >
              {isLogin ? t('login') : t('signup')}
            </motion.h3>
            <p className="text-slate-400 font-medium text-lg leading-relaxed">
              {isLogin 
                ? (language === 'derja' ? 'ادخل باش تكمل الخدمة متاعك' : 'Connectez-vous pour continuer votre travail')
                : (language === 'derja' ? 'حل حساب جديد وابدا الخدمة' : 'Créez un nouveau compte pour commencer')}
            </p>
          </div>

          <form className="space-y-6" onSubmit={(e) => { e.preventDefault(); navigate('/farmer-dashboard'); }}>
            <div className="space-y-2">
              <label className={`block text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 ${language === 'derja' ? 'text-right' : 'text-left'}`}>
                {t('phone')}
              </label>
              <div className="relative group">
                <div className={`absolute inset-y-0 ${language === 'derja' ? 'right-4' : 'left-4'} flex items-center text-slate-400 group-focus-within:text-emerald-500 transition-colors`}>
                  <Phone className="w-5 h-5" />
                </div>
                <input 
                  type="tel" 
                  placeholder={language === 'derja' ? '55 555 555' : '06 12 34 56 78'}
                  className={`w-full bg-slate-50 border-2 border-slate-50 rounded-[1.5rem] py-5 ${language === 'derja' ? 'pr-14 pl-6 text-right' : 'pl-14 pr-6'} text-slate-900 font-bold focus:bg-white focus:border-emerald-500 outline-none transition-all`}
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className={`block text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 ${language === 'derja' ? 'text-right' : 'text-left'}`}>
                {t('password')}
              </label>
              <div className="relative group">
                <div className={`absolute inset-y-0 ${language === 'derja' ? 'right-4' : 'left-4'} flex items-center text-slate-400 group-focus-within:text-emerald-500 transition-colors`}>
                  <Lock className="w-5 h-5" />
                </div>
                <input 
                  type="password" 
                  placeholder="••••••••"
                  className={`w-full bg-slate-50 border-2 border-slate-50 rounded-[1.5rem] py-5 ${language === 'derja' ? 'pr-14 pl-6 text-right' : 'pl-14 pr-6'} text-slate-900 font-bold focus:bg-white focus:border-emerald-500 outline-none transition-all`}
                />
              </div>
            </div>

            <div className="pt-4 space-y-4">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="w-full bg-slate-900 text-white rounded-[1.5rem] py-5 font-black uppercase tracking-[0.3em] text-xs flex items-center justify-center gap-3 shadow-xl shadow-slate-900/10 hover:bg-slate-800 transition-all"
              >
                {isLogin ? t('login') : t('signup')}
                <ArrowRight className={`w-4 h-4 ${language === 'derja' ? 'rotate-180' : ''}`} />
              </motion.button>
              
              <button 
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="w-full py-4 text-slate-400 hover:text-emerald-600 font-bold text-sm transition-colors flex items-center justify-center gap-2"
              >
                {isLogin 
                  ? (language === 'derja' ? 'ما عندكش حساب؟ سجل هنا' : 'Pas de compte ? Inscrivez-vous')
                  : (language === 'derja' ? 'عندك حساب؟ ادخل هنا' : 'Déjà un compte ? Connectez-vous')}
              </button>
            </div>
          </form>

          {/* TTS Helper Toggle */}
          <div className="mt-12 flex justify-center">
            <button 
              onClick={() => handleTTS(isLogin ? t('login') : t('signup'))}
              className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center hover:bg-emerald-100 transition-colors shadow-sm"
            >
              <Volume2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Branding (Mobile) */}
        <div className="mt-auto lg:hidden pt-12">
          <p className="text-slate-300 text-[9px] font-black uppercase tracking-[0.4em]">© 2026 AgriCulture</p>
        </div>
      </div>
    </div>
  )
}

export default FarmerAuth
