import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Microscope, Beaker, Dna, FileText, Activity, Search, ChevronDown, Leaf } from 'lucide-react'

const Navbar = () => {
  return (
    <nav className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center">
            <Link to="/researcher" className="flex items-center space-x-3 group">
              <div className="relative flex items-center justify-center w-12 h-12">
                <Dna className="h-10 w-10 text-emerald-500 absolute animate-[spin_4s_linear_infinite] opacity-80" />
                <Dna className="h-8 w-8 text-blue-500 absolute animate-[spin_3s_linear_infinite_reverse] opacity-60" />
                <Dna className="h-6 w-6 text-purple-500 absolute animate-pulse opacity-40" />
                <div className="absolute inset-0 bg-emerald-500/20 blur-xl rounded-full group-hover:bg-emerald-500/40 transition-colors" />
              </div>
              <div className="flex flex-col">
                <span className="text-3xl font-black tracking-tighter leading-none bg-clip-text text-transparent bg-gradient-to-r from-emerald-600 via-blue-600 to-purple-600">
                  CropDNA
                </span>
                <span className="text-[10px] uppercase tracking-[0.2em] font-bold text-slate-400 group-hover:text-emerald-600 transition-colors">
                  CropDNA Project
                </span>
              </div>
            </Link>
          </div>
          
          <div className="hidden md:flex items-center space-x-6">
            <NavDropdown 
              label="Manipulation" 
              icon={<Beaker className="w-4 h-4" />} 
              items={[
                { label: "CRISPR-Cas9", to: "/crispr-cas9" },
                { label: "ODM", to: "/odm-design" }
              ]} 
            />
            <NavLink to="/directed-crossing" icon={<Activity className="w-4 h-4" />} label="Crossing" />
            <NavLink to="/pharmaceutical" icon={<Microscope className="w-4 h-4" />} label="Pharma" />
            <NavDropdown 
              label="Analysis" 
              icon={<Search className="w-4 h-4" />} 
              items={[
                { label: "OCR", to: "/ocr-analysis" },
                { label: "Ethics", to: "/ethical-analysis" }
              ]} 
            />
            <NavLink to="/article-generator" icon={<FileText className="w-4 h-4" />} label="Writing" />
            <NavLink to="/plant-growth" icon={<Leaf className="w-4 h-4" />} label="Growth" />
          </div>

          <div className="flex items-center space-x-4">
            <Link to="/auth" className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-2 rounded-full text-sm font-bold transition-all shadow-lg shadow-emerald-200">
              Get Started
            </Link>
          </div>
        </div>
      </div>
    </nav>
  )
}

const NavDropdown = ({ icon, label, items }) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div 
      className="relative group"
      onMouseEnter={() => setIsOpen(true)}
      onMouseLeave={() => setIsOpen(false)}
    >
      <button className="flex items-center space-x-1.5 text-slate-600 hover:text-emerald-600 font-medium text-sm transition-colors py-4">
        {icon}
        <span>{label}</span>
        <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2 }}
            className="absolute left-0 w-48 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 z-50"
          >
            {items.map((item, idx) => (
              <Link
                key={idx}
                to={item.to}
                className="block px-4 py-2.5 text-sm text-slate-600 hover:text-emerald-600 hover:bg-slate-50 transition-colors"
              >
                {item.label}
              </Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const NavLink = ({ to, icon, label }) => (
  <Link 
    to={to} 
    className="flex items-center space-x-1.5 text-slate-600 hover:text-emerald-600 font-medium text-sm transition-colors"
  >
    {icon}
    <span>{label}</span>
  </Link>
)

export default Navbar
