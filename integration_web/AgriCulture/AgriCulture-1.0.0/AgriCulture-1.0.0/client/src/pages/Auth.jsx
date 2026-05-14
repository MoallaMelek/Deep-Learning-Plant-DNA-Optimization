import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import { Dna, Mail, Lock, User, ArrowRight, Fingerprint, ShieldCheck } from 'lucide-react'

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true)
  const navigate = useNavigate()

  const handleSubmit = (e) => {
    e.preventDefault()
    // Redirect to researcher home after successful "login"
    navigate('/researcher')
  }

  return (
    <div className="h-screen flex bg-white font-sans selection:bg-emerald-100 selection:text-emerald-900 overflow-hidden">
      {/* Left Side: Visual/Branding (40%) */}
      <div className="hidden lg:flex lg:w-2/5 relative overflow-hidden bg-slate-900">
        <motion.img 
          initial={{ scale: 1.1 }}
          animate={{ scale: 1 }}
          transition={{ duration: 20, repeat: Infinity, repeatType: "reverse" }}
          src="/scientist_researcher.png" 
          alt="Scientific Research" 
          className="absolute inset-0 w-full h-full object-cover opacity-60"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-900/40 to-transparent" />
        
        <div className="relative z-10 p-12 flex flex-col justify-end h-full">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <h2 className="text-4xl font-black text-white tracking-tighter mb-4 leading-none">CropDNA</h2>
            <p className="text-slate-300 text-lg leading-relaxed max-w-sm font-light">
              Advanced genomic sequencing and plant <span className="text-white font-medium italic">DNA manipulation</span> for the <span className="text-white font-medium italic">next generation</span> of agriculture.
            </p>
          </motion.div>
          
          <div className="mt-8 flex items-center justify-between pt-8 border-t border-white/10">
            <div className="flex gap-6 text-slate-500 text-[10px] font-bold uppercase tracking-[0.3em]">
              <span>© 2026</span>
              <span>AG-PROJECT</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-emerald-500 text-[9px] font-bold uppercase tracking-widest text-opacity-80">Systems Nominal</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side: Authentication Form (60%) */}
      <div className="w-full lg:w-3/5 flex items-center justify-center p-8 bg-slate-50/30">
        <motion.div 
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div className="mb-8">
            <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center mb-4 shadow-sm">
              <Fingerprint className="w-5 h-5 text-emerald-600" />
            </div>
            <h1 className="text-3xl font-black text-slate-900 tracking-tight mb-2">
              {isLogin ? 'Access Identity' : 'Register Researcher'}
            </h1>
            <p className="text-slate-500 font-medium text-base leading-relaxed">
              Welcome to the central research node.
            </p>
          </div>

          <div className="flex mb-8 border-b border-slate-200">
            <button 
              onClick={() => setIsLogin(true)}
              className={`pb-4 px-6 text-xs font-black uppercase tracking-widest transition-all relative ${isLogin ? 'text-emerald-600' : 'text-slate-400 hover:text-slate-600'}`}
            >
              Login
              {isLogin && <motion.div layoutId="tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 rounded-t-full shadow-[0_0_10px_rgba(16,185,129,0.5)]" />}
            </button>
            <button 
              onClick={() => setIsLogin(false)}
              className={`pb-4 px-6 text-xs font-black uppercase tracking-widest transition-all relative ${!isLogin ? 'text-emerald-600' : 'text-slate-400 hover:text-slate-600'}`}
            >
              Sign Up
              {!isLogin && <motion.div layoutId="tab" className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 rounded-t-full shadow-[0_0_10px_rgba(16,185,129,0.5)]" />}
            </button>
          </div>

          <AnimatePresence mode="wait">
            <motion.form 
              key={isLogin ? 'login' : 'signup'}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
              onSubmit={handleSubmit}
            >
              {!isLogin && (
                <div>
                  <label className="block text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5">Full Name</label>
                  <input 
                    type="text" 
                    placeholder="Researcher Name" 
                    className="w-full bg-white border border-slate-200 rounded-xl py-3 px-5 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500/40 transition-all shadow-sm"
                  />
                </div>
              )}

              <div>
                <label className="block text-[9px] font-black text-slate-400 uppercase tracking-[0.2em] mb-1.5">Researcher Email</label>
                <input 
                  type="email" 
                  placeholder="name@cropdna.lab" 
                  className="w-full bg-white border border-slate-200 rounded-xl py-3 px-5 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500/40 transition-all shadow-sm"
                />
              </div>

              <div>
                <div className="flex justify-between mb-1.5">
                  <label className="text-[9px] font-black text-slate-400 uppercase tracking-[0.2em]">Password</label>
                  {isLogin && <button type="button" className="text-[9px] text-emerald-600 hover:text-emerald-700 font-black uppercase tracking-widest">Forgot?</button>}
                </div>
                <input 
                  type="password" 
                  placeholder="••••••••" 
                  className="w-full bg-white border border-slate-200 rounded-xl py-3 px-5 text-sm text-slate-900 focus:outline-none focus:ring-4 focus:ring-emerald-500/10 focus:border-emerald-500/40 transition-all shadow-sm"
                />
              </div>

              <motion.button 
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                className="w-full bg-slate-900 hover:bg-emerald-950 text-white font-black uppercase tracking-[0.2em] text-[10px] py-4 rounded-xl transition-all shadow-lg shadow-slate-900/10 flex items-center justify-center space-x-3 group mt-4"
              >
                <span>{isLogin ? 'Enter Laboratory' : 'Create Identity'}</span>
                <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1.5 transition-transform" />
              </motion.button>
              
              <div className="flex items-center gap-3 my-4">
                <div className="flex-grow h-px bg-slate-100" />
                <span className="text-[9px] font-black text-slate-300 uppercase tracking-widest">OR</span>
                <div className="flex-grow h-px bg-slate-100" />
              </div>
              
              <button type="button" className="w-full border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 font-bold py-3 rounded-xl transition-all flex items-center justify-center gap-3 shadow-sm text-xs">
                <img src="https://www.google.com/favicon.ico" className="w-3.5 h-3.5 grayscale" alt="" />
                <span>Institutional ID</span>
              </button>
            </motion.form>
          </AnimatePresence>

          <div className="mt-8 pt-6 border-t border-slate-100 flex items-center justify-between">
            <Link to="/" className="text-slate-400 hover:text-slate-900 text-[9px] font-black uppercase tracking-widest transition-colors flex items-center gap-2">
              <ArrowRight className="w-3 h-3 rotate-180" />
              Portal Exit
            </Link>
            <div className="flex items-center gap-1.5 text-slate-300">
              <Lock className="w-2.5 h-2.5" />
              <span className="text-[9px] font-black uppercase tracking-widest">SSL Encrypted</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default Auth
