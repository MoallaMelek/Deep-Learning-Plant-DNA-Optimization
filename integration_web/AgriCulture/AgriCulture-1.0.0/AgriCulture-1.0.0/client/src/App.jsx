import React from 'react'
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import Navbar from './components/Navbar'
import CustomCursor from './components/CustomCursor'
import Home from './pages/Home'
import DNAManipulation from './pages/DNAManipulation'
import DirectedCrossing from './pages/DirectedCrossing'
import Pharmaceutical from './pages/Pharmaceutical'
import OCRAnalysis from './pages/OCRAnalysis'
import RAGAnalysis from './pages/RAGAnalysis'
import EthicAnalysis from './pages/EthicAnalysis'
import ArticleGenerator from './pages/ArticleGenerator'
import PlantGrowthStudio from './pages/PlantGrowthStudio'
import Auth from './pages/Auth'
import RoleSelection from './pages/RoleSelection'
import FarmerAuth from './pages/FarmerAuth'
import FarmerDashboard from './pages/FarmerDashboard'
import PlantSound from './pages/PlantSound'
import ODMAnalysis from './pages/ODMAnalysis'
import CrisprEfficiency from './pages/CrisprEfficiency'
import InsectAI from './pages/InsectAI'
import PlantDisease from './pages/PlantDisease'

function AppContent() {
  const location = useLocation()
  const isAuthPage = location.pathname === '/auth'
  const isFarmerPage = location.pathname.startsWith('/farmer') || location.pathname === '/plant-sound' || location.pathname === '/insect-ai' || location.pathname === '/plant-disease'
  const isRolePage = location.pathname === '/'
  const hideNavAndFooter = isAuthPage || isFarmerPage || isRolePage

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <CustomCursor />
      {!hideNavAndFooter && <Navbar />}
      <main className="flex-grow">
        <Routes>
          <Route path="/" element={<RoleSelection />} />
          <Route path="/researcher" element={<Home />} />
          <Route path="/dna-manipulation" element={<DNAManipulation />} />
          <Route path="/directed-crossing" element={<DirectedCrossing />} />
          <Route path="/pharmaceutical" element={<Pharmaceutical />} />
          <Route path="/ocr-analysis" element={<OCRAnalysis />} />
          <Route path="/rag-search" element={<RAGAnalysis />} />
          <Route path="/ethical-analysis" element={<EthicAnalysis />} />
          <Route path="/article-generator" element={<ArticleGenerator />} />
          <Route path="/plant-growth" element={<PlantGrowthStudio />} />
          <Route path="/auth" element={<Auth />} />
          <Route path="/farmer-auth" element={<FarmerAuth />} />
          <Route path="/farmer-dashboard" element={<FarmerDashboard />} />
          <Route path="/plant-sound" element={<PlantSound />} />
          <Route path="/odm-design" element={<ODMAnalysis />} />
          <Route path="/crispr-cas9" element={<CrisprEfficiency />} />
          <Route path="/insect-ai" element={<InsectAI />} />
          <Route path="/plant-disease" element={<PlantDisease />} />
        </Routes>
      </main>
      {!hideNavAndFooter && (
        <footer className="bg-white border-t py-8 text-center text-slate-500 text-sm">
          <p>© 2026 CropDNA Platform. Bridging Genetics and Agriculture.</p>
        </footer>
      )}
    </div>
  )
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  )
}

export default App
