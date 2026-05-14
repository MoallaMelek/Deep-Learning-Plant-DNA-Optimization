import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useNavigate, useLocation } from 'react-router-dom'
import { Volume2, Mic, MessageSquare, Sparkles, X, Send, ChevronRight, VolumeX } from 'lucide-react'
import { useTranslation } from '../hooks/useTranslation'
import { speak } from '../utils/tts'

const AgriAgent = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { language, t } = useTranslation('derja')
  
  const [isOpen, setIsOpen] = useState(false)
  const [message, setMessage] = useState('')
  const [options, setOptions] = useState([])
  const [isSpeaking, setIsSpeaking] = useState(false)

  const getPageContent = () => {
    const path = location.pathname
    
    if (path === '/farmer-dashboard') {
      return {
        msg: language === 'derja' 
          ? 'مرحباً بك يا مجد! أنا رفيقتك الذكية. شنية تحب تعمل اليوم؟' 
          : 'Bienvenue Majd ! Je suis votre assistante intelligente. Que souhaitez-vous faire aujourd\'hui ?',
        opts: [
          { 
            label: language === 'derja' ? 'مراقبة صوت الزرع' : 'Monitorer le son des plantes', 
            path: '/plant-sound',
            desc: language === 'derja' ? 'تتبع الري الذكي' : 'Suivi irrigation intelligente'
          },
          { 
            label: language === 'derja' ? 'تصوير نبتة مريضة' : 'Analyser une plante malade', 
            path: '/plant-disease',
            desc: language === 'derja' ? 'كشف الأمراض بالصور' : 'Détection maladies par photo'
          },
          { 
            label: language === 'derja' ? 'كشف الحشرات' : 'Détecter des insectes', 
            path: '/insect-ai',
            desc: language === 'derja' ? 'تحليل الصوت والصورة' : 'Analyse son et image'
          }
        ]
      }
    }
    
    if (path === '/plant-sound') {
      return {
        msg: language === 'derja'
          ? 'هنا تنجم تتبع حالة الري متاعك. السيستم يستعمل مستشعرات صوتية باش يعرف وقتاش النبتة عطشانة.'
          : 'Ici vous pouvez suivre l\'irrigation. Le système utilise des capteurs acoustiques pour savoir quand la plante a soif.',
        opts: [
          { label: language === 'derja' ? 'كيفاش نخدم السيمولاتور؟' : 'Comment lancer le simulateur ?', action: 'explain_sim' },
          { label: language === 'derja' ? 'رجوع للرئيسية' : 'Retour au tableau de bord', path: '/farmer-dashboard' }
        ]
      }
    }

    if (path === '/plant-disease') {
      return {
        msg: language === 'derja'
          ? 'ابعثلي تصويرة للنبتة اللي شاكك فيها، وأنا نقلك شنية المرض الممكن وكيفاش تعالجو.'
          : 'Envoyez-moi une photo de la plante suspecte, et je vous dirai la maladie possible et comment la traiter.',
        opts: [
          { label: language === 'derja' ? 'نصائح للتصوير' : 'Conseils pour la photo', action: 'tips' },
          { label: language === 'derja' ? 'رجوع للرئيسية' : 'Retour au tableau de bord', path: '/farmer-dashboard' }
        ]
      }
    }

    if (path === '/insect-ai') {
      return {
        msg: language === 'derja'
          ? 'هنا نعاونك تعرف الحشرات اللي في حقلك. تنجم تبعثلي تصويرة وإلا تسجل صوتها.'
          : 'Ici je vous aide à identifier les insectes dans votre champ. Vous pouvez m\'envoyer une photo ou enregistrer leur son.',
        opts: [
          { label: language === 'derja' ? 'شنية الحشرات الخطيرة؟' : 'Quels sont les insectes dangereux ?', action: 'danger' },
          { label: language === 'derja' ? 'رجوع للرئيسية' : 'Retour au tableau de bord', path: '/farmer-dashboard' }
        ]
      }
    }

    return { msg: '', opts: [] }
  }

  useEffect(() => {
    const content = getPageContent()
    setMessage(content.msg)
    setOptions(content.opts)
    
    // Auto-open on dashboard if not already open
    if (location.pathname === '/farmer-dashboard') {
      const timer = setTimeout(() => setIsOpen(true), 1500)
      return () => clearTimeout(timer)
    }
  }, [location.pathname, language])

  const handleTTS = () => {
    if (isSpeaking) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
    } else {
      setIsSpeaking(true)
      speak(message, language === 'derja' ? 'derja' : 'fr-FR')
      // Simple timeout to reset icon (in a real app we'd use onend event)
      setTimeout(() => setIsSpeaking(false), message.length * 100)
    }
  }

  const handleOptionClick = (opt) => {
    if (opt.path) {
      navigate(opt.path)
    } else if (opt.action) {
      // Handle special explanations
      if (opt.action === 'explain_sim') {
        const expl = language === 'derja' 
          ? 'انزل على Start Sim باش تبدأ تتبع البيانات الحية. إذا VWC طاح برشة، السبالة تتحل وحدها!'
          : 'Cliquez sur Start Sim pour suivre les données en direct. Si le VWC chute, l\'irrigation s\'active seule !'
        setMessage(expl)
        speak(expl, language === 'derja' ? 'derja' : 'fr-FR')
      } else if (opt.action === 'tips') {
        const expl = language === 'derja'
          ? 'حاول تكون التصويرة واضحة وفيها ضوء باهي. صور الورقة من فوق ومن لوطة.'
          : 'Essayez d\'avoir une photo claire avec une bonne lumière. Prenez la feuille de dessus et de dessous.'
        setMessage(expl)
        speak(expl, language === 'derja' ? 'derja' : 'fr-FR')
      } else if (opt.action === 'danger') {
        const expl = language === 'derja'
          ? 'الحشرات الخطيرة هي اللي تاكل الأوراق بسرعة وإلا تنقل الأمراض. أنا ننصحك كيفاش تداويها.'
          : 'Les insectes dangereux sont ceux qui dévorent les feuilles ou transmettent des maladies. Je vous conseillerai sur le traitement.'
        setMessage(expl)
        speak(expl, language === 'derja' ? 'derja' : 'fr-FR')
      }
    }
  }

  return (
    <div className={`fixed bottom-10 ${language === 'derja' ? 'left-10' : 'right-10'} z-[100] flex flex-col items-end gap-4`} dir={language === 'derja' ? 'rtl' : 'ltr'}>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="w-[350px] bg-white/95 backdrop-blur-2xl rounded-[2.5rem] shadow-[0_20px_50px_rgba(0,0,0,0.2)] border border-white overflow-hidden p-6 mb-2"
          >
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-emerald-500 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-black text-slate-900">AgriAgent IA</h4>
                  <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest">En ligne</p>
                </div>
              </div>
              <button 
                onClick={() => setIsOpen(false)}
                className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="bg-slate-50 rounded-3xl p-5 mb-6 border border-slate-100 relative group">
              <p className="text-slate-800 text-sm font-bold leading-relaxed pr-8">
                {message}
              </p>
              <button 
                onClick={handleTTS}
                className={`absolute top-4 ${language === 'derja' ? 'left-4' : 'right-4'} w-8 h-8 rounded-xl flex items-center justify-center transition-all ${isSpeaking ? 'bg-emerald-500 text-white animate-pulse' : 'bg-white text-slate-400 border border-slate-100 hover:border-emerald-200 hover:text-emerald-500'}`}
              >
                {isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
            </div>

            <div className="space-y-3">
              {options.map((opt, idx) => (
                <motion.button
                  key={idx}
                  whileHover={{ x: language === 'derja' ? -5 : 5, backgroundColor: 'rgba(16,185,129,0.05)' }}
                  onClick={() => handleOptionClick(opt)}
                  className="w-full p-4 rounded-2xl border border-slate-100 bg-white flex items-center justify-between text-right group transition-all"
                >
                  <div className={language === 'derja' ? 'text-right' : 'text-left'}>
                    <p className="text-xs font-black text-slate-900 group-hover:text-emerald-600 transition-colors">{opt.label}</p>
                    {opt.desc && <p className="text-[9px] font-bold text-slate-400 uppercase tracking-tight mt-0.5">{opt.desc}</p>}
                  </div>
                  <ChevronRight className={`w-4 h-4 text-slate-300 group-hover:text-emerald-500 transition-all ${language === 'derja' ? 'rotate-180' : ''}`} />
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        animate={isOpen ? {} : { y: [0, -10, 0] }}
        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
        onClick={() => setIsOpen(!isOpen)}
        className="relative group cursor-pointer"
      >
        <div className="absolute -inset-4 bg-emerald-500/20 blur-3xl rounded-full animate-pulse opacity-50" />
        <div className={`w-20 h-20 rounded-[2rem] border-2 border-white shadow-2xl overflow-hidden relative z-10 bg-white/10 backdrop-blur-xl transition-all ${isOpen ? 'scale-90 opacity-50' : 'hover:scale-110'}`}>
          <img src="/assets/img/farmer_avatar.png" alt="AI Agent" className="w-full h-full object-cover" />
        </div>
        <div className={`absolute -bottom-1 -right-1 w-8 h-8 rounded-xl border-2 border-white flex items-center justify-center text-white z-20 shadow-lg transition-all ${isOpen ? 'bg-slate-400' : 'bg-emerald-500'}`}>
          {isOpen ? <X className="w-4 h-4" /> : <Sparkles className="w-4 h-4" />}
        </div>
      </motion.div>
    </div>
  )
}

export default AgriAgent
