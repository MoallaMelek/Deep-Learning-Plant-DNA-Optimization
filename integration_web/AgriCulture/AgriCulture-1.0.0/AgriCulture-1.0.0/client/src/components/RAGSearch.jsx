import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Dna, Hash, Tag, Sprout, MessageSquare, FileCode, ChevronDown, Loader2 } from 'lucide-react';

const INPUT_TYPES = [
  { id: 'dna', label: 'DNA', icon: Dna, placeholder: 'ATCGATCG...', type: 'textarea' },
  { id: 'accession', label: 'Accession', icon: Hash, placeholder: 'MZ935738.1', type: 'text' },
  { id: 'gene', label: 'Gene', icon: Tag, placeholder: 'DREB', type: 'text' },
  { id: 'trait', label: 'Trait', icon: Sprout, placeholder: 'Select a trait', type: 'select', options: ['Drought', 'Heat', 'Salt', 'Disease'] },
  { id: 'natural', label: 'Natural', icon: MessageSquare, placeholder: 'Find genes for...', type: 'text' },
  { id: 'fasta', label: 'FASTA', icon: FileCode, placeholder: '>ID description\nATCG...', type: 'textarea' },
];

const RAGSearch = ({ onSearch, loading }) => {
  const [selectedType, setSelectedType] = useState(INPUT_TYPES[4]); // Default to Natural Language
  const [inputValue, setInputValue] = useState('');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const handleSearch = () => {
    if (onSearch) {
      onSearch({ type: selectedType.id, query: inputValue });
    }
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(16, 185, 129, 0.2);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(16, 185, 129, 0.4);
        }
      `}</style>
      {/* Container Principal */}
      <div className="relative bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl overflow-visible">
        <div className="flex flex-col md:flex-row items-stretch p-2 gap-2">
          
          {/* Sélecteur de Type (Dropdown) */}
          <div className="relative">
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="h-full px-4 py-3 bg-white/5 hover:bg-white/10 rounded-2xl flex items-center gap-2.5 text-white transition-all min-w-[150px] border border-white/5"
            >
              <selectedType.icon className="w-4 h-4 text-white/70" />
              <span className="font-bold text-xs">{selectedType.label}</span>
              <ChevronDown className={`w-3.5 h-3.5 ml-auto opacity-30 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {isDropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute top-full left-0 mt-3 w-64 bg-slate-900/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl z-[100] overflow-y-auto max-h-[250px] custom-scrollbar"
                >
                  <div className="p-1.5 space-y-0.5">
                    {INPUT_TYPES.map((type) => (
                      <button
                        key={type.id}
                        onClick={() => {
                          setSelectedType(type);
                          setIsDropdownOpen(false);
                          setInputValue('');
                        }}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all text-left group ${
                          selectedType.id === type.id 
                          ? 'bg-white/20 text-white' 
                          : 'text-white/60 hover:bg-white/5 hover:text-white'
                        }`}
                      >
                        <type.icon className={`w-4 h-4 transition-transform group-hover:scale-110 ${selectedType.id === type.id ? 'text-white' : 'text-white/40'}`} />
                        <span className="text-sm font-bold tracking-tight">{type.label}</span>
                      </button>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Champ de Saisie */}
          <div className="flex-1 flex items-center min-h-[50px]">
            {selectedType.type === 'select' ? (
              <select
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="w-full bg-transparent px-4 py-2 text-white text-base font-medium outline-none appearance-none cursor-pointer"
              >
                <option value="" disabled className="bg-slate-900">{selectedType.placeholder}</option>
                {selectedType.options.map((opt) => (
                  <option key={opt} value={opt} className="bg-slate-900">{opt}</option>
                ))}
              </select>
            ) : selectedType.type === 'textarea' ? (
              <textarea
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={selectedType.placeholder}
                className="w-full bg-transparent px-4 py-2 text-white text-base font-medium outline-none placeholder:text-white/20 resize-none scrollbar-hide"
                rows={1}
                style={{ minHeight: '36px' }}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSearch())}
              />
            ) : (
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={selectedType.placeholder}
                className="w-full bg-transparent px-4 py-2 text-white text-base font-medium outline-none placeholder:text-white/20"
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
            )}
          </div>

          {/* Bouton de Recherche */}
          <button 
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-3 bg-emerald-600/90 hover:bg-emerald-600 text-white rounded-2xl font-bold flex items-center gap-2 transition-all shadow-lg active:scale-95 text-sm disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4 opacity-80" />}
            <span>{loading ? 'Searching...' : 'Search'}</span>
          </button>
        </div>
      </div>
      
      {/* Petit indicateur de type en dessous */}
      <div className="mt-3 px-6">
        <p className="text-white/30 text-[10px] font-bold uppercase tracking-widest">
          Search mode: {selectedType.label}
        </p>
      </div>
    </div>
  );
};

export default RAGSearch;
