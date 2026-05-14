import React from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { User, Sprout, ArrowRight, Dna } from 'lucide-react'

const RoleSelection = () => {
  const navigate = useNavigate()

  const roles = [
    {
      id: 'researcher',
      title: 'Researcher',
      subtitle: 'Scientist',
      desc: 'Access advanced genomic analysis and DNA manipulation tools.',
      icon: <User className="w-6 h-6" />,
      img: '/assets/img/researcher_avatar.png',
      color: 'from-emerald-500 to-teal-600',
      bgColor: 'bg-emerald-50/30',
      borderColor: 'border-emerald-100/50',
      path: '/auth'
    },
    {
      id: 'farmer',
      title: 'فلاّح (Agriculteur)',
      subtitle: 'فضاء الفلاح',
      desc: 'تفقد الزرع متاعك، شوف المرض و اسمع النصيحة.',
      icon: <Sprout className="w-6 h-6" />,
      img: '/assets/img/farmer_avatar.png',
      color: 'from-slate-500 to-slate-700',
      bgColor: 'bg-slate-50/50',
      borderColor: 'border-slate-100',
      path: '/farmer-auth'
    }
  ]

  return (
    <div className="h-screen w-full bg-white flex items-center justify-center p-4 font-sans relative overflow-hidden selection:bg-emerald-100">
      {/* Subtle Background Contours */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.02]">
        <Dna className="absolute -top-24 -left-24 w-[30rem] h-[30rem] rotate-12" />
        <Dna className="absolute -bottom-48 -right-48 w-[40rem] h-[40rem] -rotate-12" />
      </div>

      <div className="max-w-6xl w-full relative z-10 flex flex-col justify-center h-full">
        <div className="text-center mb-8 sm:mb-12">
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-4xl sm:text-7xl font-black text-slate-900 mb-2 sm:mb-4 tracking-tight"
          >
            CropDNA <span className="text-emerald-600">Platform</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-slate-400 text-sm sm:text-lg font-bold uppercase tracking-[0.3em]"
          >
            Portal Selection
          </motion.p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 lg:gap-10 items-center">
          {roles.map((role, idx) => (
            <motion.div
              key={role.id}
              initial={{ opacity: 0, x: idx === 0 ? -30 : 30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.8, delay: 0.3 + idx * 0.1 }}
              whileHover={{ y: -5 }}
              onClick={() => navigate(role.path)}
              className="relative cursor-pointer group bg-white border border-slate-100 rounded-[2.5rem] p-6 sm:p-10 transition-all hover:shadow-2xl hover:shadow-emerald-500/10 flex flex-col items-center text-center overflow-hidden"
            >
              <div className={`absolute inset-3 rounded-[2rem] border-2 border-dashed ${role.id === 'farmer' ? 'border-slate-100' : 'border-emerald-100/50'} opacity-0 group-hover:opacity-100 transition-opacity duration-500`} />

              <div className="relative mb-6 sm:mb-8">
                <motion.div
                  className="w-40 h-40 sm:w-48 sm:h-48 rounded-full overflow-hidden border-4 border-white shadow-lg relative z-10"
                  whileHover={{ 
                    rotate: [0, -5, 5, -5, 5, 0],
                    transition: { duration: 0.5, repeat: Infinity }
                  }}
                >
                  <img src={role.img} alt={role.title} className="w-full h-full object-cover" />
                </motion.div>
                
                <motion.div 
                  className="absolute -top-2 -right-2 w-12 h-12 rounded-xl bg-white shadow-lg flex items-center justify-center text-emerald-600 z-20 scale-75 sm:scale-100"
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.8 }}
                >
                  {role.icon}
                </motion.div>
              </div>

              <div className="relative z-10">
                <span className={`text-[10px] font-black uppercase tracking-[0.4em] ${role.id === 'farmer' ? 'text-slate-400' : 'text-emerald-600'} mb-2 block`}>
                  {role.subtitle}
                </span>
                <h2 className={`text-2xl sm:text-3xl font-black text-slate-900 mb-3 tracking-tight ${role.id === 'farmer' ? 'font-sans' : ''}`}>{role.title}</h2>
                <p className={`text-slate-500 leading-relaxed text-sm sm:text-base max-w-[280px] mx-auto font-medium ${role.id === 'farmer' ? 'text-lg' : ''}`}>
                  {role.desc}
                </p>
              </div>

              <div className={`mt-6 flex items-center gap-2 font-black uppercase tracking-widest text-[10px] ${role.id === 'farmer' ? 'text-slate-400' : 'text-emerald-600'} group-hover:gap-4 transition-all`}>
                <span>Enter</span>
                <ArrowRight className="w-4 h-4" />
              </div>
            </motion.div>
          ))}
        </div>

        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="mt-8 sm:mt-12 text-center"
        >
          <p className="text-slate-300 text-[9px] font-black uppercase tracking-[0.4em]">
            © 2026 CropDNA R&D
          </p>
        </motion.div>
      </div>
    </div>
  )
}

export default RoleSelection
