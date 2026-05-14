import React from 'react'
import { motion } from 'framer-motion'
import { Beaker, Scissors, Zap, Info } from 'lucide-react'

const DNAManipulation = () => {
  return (
    <div className="py-12 container mx-auto px-4">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12">
          <h1 className="text-4xl font-bold text-slate-900 mb-4">DNA Manipulation</h1>
          <p className="text-slate-600 text-lg">Advanced CRISPR and ODM tools for precise genomic editing.</p>
        </header>

        <div className="grid md:grid-cols-2 gap-8 mb-12">
          <ToolCard 
            title="CRISPR-Cas9"
            icon={<Scissors className="w-6 h-6 text-red-500" />}
            description="Site-specific double-strand breaks for gene knockout or knock-in."
            active={true}
          />
          <ToolCard 
            title="ODM (Oligonucleotide-Directed Mutagenesis)"
            icon={<Zap className="w-6 h-6 text-yellow-500" />}
            description="Non-transgenic method for precise single-nucleotide changes."
            active={false}
          />
        </div>

        <div className="bg-white rounded-3xl p-8 border border-slate-200 shadow-sm">
          <div className="flex items-center space-x-2 mb-6">
            <Beaker className="w-6 h-6 text-primary-600" />
            <h2 className="text-2xl font-bold text-slate-900">Sequence Editor</h2>
          </div>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Target Sequence</label>
              <textarea 
                className="w-full h-32 p-4 bg-slate-50 border border-slate-200 rounded-xl font-mono text-sm focus:ring-2 focus:ring-primary-500/20 focus:outline-none"
                placeholder="ATGCGTAGC..."
              />
            </div>
            
            <div className="flex flex-wrap gap-4">
              <button className="bg-primary-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-primary-700 transition-all flex items-center space-x-2">
                <Scissors className="w-4 h-4" />
                <span>Simulate CRISPR Cut</span>
              </button>
              <button className="border border-slate-200 bg-white text-slate-700 px-6 py-3 rounded-xl font-semibold hover:bg-slate-50 transition-all">
                Download Analysis
              </button>
            </div>
          </div>
        </div>

        <div className="mt-12 bg-blue-50 rounded-2xl p-6 flex items-start space-x-4 border border-blue-100">
          <Info className="w-6 h-6 text-blue-600 flex-shrink-0" />
          <div>
            <h4 className="font-bold text-blue-900">Research Note</h4>
            <p className="text-blue-800 text-sm">
              All CRISPR simulations are performed using the latest AGD-2026 database. Ensure your guide RNA sequences are validated for off-target effects.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

const ToolCard = ({ title, icon, description, active }) => (
  <div className={`p-6 rounded-3xl border ${active ? 'border-primary-200 bg-primary-50/50' : 'border-slate-200 bg-white'}`}>
    <div className="flex justify-between items-start mb-4">
      <div className="p-3 bg-white rounded-2xl shadow-sm border border-slate-100">
        {icon}
      </div>
      {active && (
        <span className="px-3 py-1 bg-primary-100 text-primary-700 text-xs font-bold rounded-full">ACTIVE</span>
      )}
    </div>
    <h3 className="text-xl font-bold text-slate-900 mb-2">{title}</h3>
    <p className="text-slate-600 text-sm leading-relaxed">{description}</p>
  </div>
)

export default DNAManipulation
