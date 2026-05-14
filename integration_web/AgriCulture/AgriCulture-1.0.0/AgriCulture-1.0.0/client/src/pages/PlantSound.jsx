import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import { 
  Activity, 
  Droplets, 
  Thermometer, 
  Wind, 
  AlertTriangle, 
  Play, 
  Square, 
  BarChart3, 
  History,
  Volume2,
  ChevronLeft,
  Waves,
  Cpu,
  Zap,
  Info,
  TrendingUp,
  Download
} from 'lucide-react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { useNavigate } from 'react-router-dom';
import { speak } from '../utils/tts';
import AgriAgent from '../components/AgriAgent';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

const API_BASE = 'http://127.0.0.1:8000/cropdna/api/iot';
const CHART_DATASETS = ['confidence', 'vwc', 'temperature'];

// --- Shared Components ---

const WaveformVisualizer = ({ color = "#10b981" }) => {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.beginPath();
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.moveTo(0, canvas.height / 2);
      for (let i = 0; i < canvas.width; i++) {
        const y = (canvas.height / 2) + Math.sin(i * 0.1 + Date.now() * 0.01) * Math.random() * 20;
        ctx.lineTo(i, y);
      }
      ctx.stroke();
      requestAnimationFrame(draw);
    };
    const anim = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(anim);
  }, [color]);
  return <canvas ref={canvasRef} className="w-full h-16 opacity-50" width={400} height={60} />;
};

const FarmerIllustration = () => (
  <svg viewBox="0 0 400 300" className="w-full h-full max-w-[350px] drop-shadow-2xl">
    <circle cx="200" cy="150" r="120" fill="#ecfdf5" />
    <ellipse cx="200" cy="240" rx="100" ry="20" fill="#d1fae5" />
    <g transform="translate(240, 200)">
      <path d="M0 0 Q 10 -20 20 0" fill="none" stroke="#10b981" strokeWidth="3" />
      <circle cx="0" cy="-10" r="8" fill="#10b981" />
      <circle cx="20" cy="-5" r="6" fill="#10b981" />
    </g>
    <rect x="150" y="100" width="30" height="100" rx="15" fill="#064e3b" />
    <circle cx="165" cy="85" r="18" fill="#fda4af" />
    <path d="M150 75 Q 165 60 180 75 L 180 100 L 150 100 Z" fill="#1e293b" />
    <motion.g
      animate={{ rotate: [0, -10, 0] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      style={{ originX: "165px", originY: "115px" }}
    >
      <rect x="165" y="110" width="60" height="12" rx="6" fill="#064e3b" />
      <g transform="translate(210, 105)">
        <rect x="0" y="0" width="40" height="30" rx="8" fill="#059669" />
        <path d="M40 10 L 60 25" stroke="#059669" strokeWidth="8" strokeLinecap="round" />
        <motion.g animate={{ opacity: [0, 1, 0], y: [0, 20, 40] }} transition={{ duration: 1.5, repeat: Infinity }}>
          <circle cx="65" cy="30" r="2" fill="#60a5fa" />
          <circle cx="75" cy="35" r="2" fill="#60a5fa" />
        </motion.g>
      </g>
    </motion.g>
  </svg>
);

const BackgroundPatterns = () => (
  <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
    <div className="absolute inset-0 opacity-[0.1]" style={{ backgroundImage: `radial-gradient(#10b981 0.5px, transparent 0.5px)`, backgroundSize: '32px 32px' }} />
    <motion.div animate={{ scale: [1, 1.2, 1], x: [0, 30, 0] }} transition={{ duration: 20, repeat: Infinity }} className="absolute -top-1/4 -right-1/4 w-[800px] h-[800px] bg-emerald-100/40 rounded-full blur-[120px]" />
  </div>
);

const PlantSound = () => {
  const navigate = useNavigate();
  const [plants, setPlants] = useState([]);
  const [stats, setStats] = useState({ total_readings: 0, dry_detections: 0, irrigations_triggered: 0, water_saved: 0, simulation_active: true });
  const [selectedPlant, setSelectedPlant] = useState('plant_001');
  const [history, setHistory] = useState([]);
  const [alert, setAlert] = useState(null);
  const [chartMetric, setChartMetric] = useState('confidence');
  const [simLoading, setSimLoading] = useState(false);
  const [apiError, setApiError] = useState(false);
  const prevActionRef = useRef({});

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/dashboard/stats`);
      setStats(res.data);
      setApiError(false);
    } catch (err) { setApiError(true); }
  };

  const fetchPlants = async () => {
    try {
      const res = await axios.get(`${API_BASE}/plants`);
      setPlants(res.data);
      setApiError(false);
      res.data.forEach(plant => {
        if (plant.action === 'IRRIGATE_NOW' && prevActionRef.current[plant.plant_id] !== 'IRRIGATE_NOW') {
          setAlert(plant.plant_id);
          speak(`السبالة تحلت وحدها للنبتة ${plant.plant_id.replace('_', ' ')} لمدة عشرين دقيقة`, 'derja');
          setTimeout(() => setAlert(null), 30000);
        }
        prevActionRef.current[plant.plant_id] = plant.action;
      });
    } catch (err) { setApiError(true); }
  };

  const fetchHistory = async (plantId) => {
    try {
      const res = await axios.get(`${API_BASE}/plants/${plantId}/history`);
      setHistory(res.data);
    } catch (err) { console.error(err); }
  };

  const toggleSimulation = async () => {
    setSimLoading(true);
    try {
      const action = stats.simulation_active ? 'stop' : 'start';
      const res = await axios.post(`${API_BASE}/simulate/${action}`);
      setStats(prev => ({ ...prev, simulation_active: res.data.simulation_active }));
    } catch (err) { console.error(err); }
    setSimLoading(false);
  };

  useEffect(() => {
    let controller = new AbortController();

    const poll = async () => {
      controller.abort();          // cancel any previous in-flight
      controller = new AbortController();
      const signal = controller.signal;
      try {
        const [statsRes, plantsRes, histRes] = await Promise.all([
          axios.get(`${API_BASE}/dashboard/stats`,              { signal }),
          axios.get(`${API_BASE}/plants`,                       { signal }),
          axios.get(`${API_BASE}/plants/${selectedPlant}/history`, { signal }),
        ]);
        setStats(statsRes.data);
        setApiError(false);
        setHistory(histRes.data);
        const data = plantsRes.data;
        setPlants(data);
        data.forEach(plant => {
          if (plant.action === 'IRRIGATE_NOW' && prevActionRef.current[plant.plant_id] !== 'IRRIGATE_NOW') {
            setAlert(plant.plant_id);
            speak(`السبالة تحلت وحدها للنبتة ${plant.plant_id.replace('_', ' ')} لمدة عشرين دقيقة`, 'derja');
            setTimeout(() => setAlert(null), 30000);
          }
          prevActionRef.current[plant.plant_id] = plant.action;
        });
      } catch (err) {
        if (axios.isCancel(err) || err.name === 'CanceledError') return;
        setApiError(true);
      }
    };

    poll(); // initial fetch immediately
    const interval = setInterval(poll, 8000);
    return () => {
      clearInterval(interval);
      controller.abort();
    };
  }, [selectedPlant]);

  const METRIC_CONFIG = {
    confidence:  { label: 'Acoustic Confidence (%)', color: '#10b981', bg: 'rgba(16,185,129,0.1)', max: 100 },
    vwc:         { label: 'VWC (m³/m³)',             color: '#3b82f6', bg: 'rgba(59,130,246,0.1)', max: 0.15 },
    temperature: { label: 'Temperature (°C)',         color: '#f59e0b', bg: 'rgba(245,158,11,0.1)', max: 40 },
  };
  const mc = METRIC_CONFIG[chartMetric];
  const chartData = {
    labels: history.map(h => new Date(h.timestamp).toLocaleTimeString()),
    datasets: [{
      label: mc.label,
      data: history.map(h => h[chartMetric] ?? 0),
      borderColor: mc.color,
      borderWidth: 3,
      backgroundColor: mc.bg,
      tension: 0.5,
      fill: true,
    }],
  };
  const chartOptions = { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 0, max: mc.max } } };

  const selectedPlantData = plants.find(p => p.plant_id === selectedPlant) || {};

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900 p-4 sm:p-12 font-sans selection:bg-emerald-500/30 overflow-x-hidden relative" dir="rtl">
      <BackgroundPatterns />
      
      {/* Alert Overlay */}
      <AnimatePresence>
        {alert && (
          <motion.div initial={{ y: -100 }} animate={{ y: 0 }} exit={{ y: -100 }} className="fixed top-0 left-0 right-0 z-[100] p-6 bg-white text-red-600 text-center font-black shadow-2xl border-b-4 border-red-500">
             <div className="flex items-center justify-center gap-6 text-2xl">
                <AlertTriangle className="w-10 h-10 animate-bounce" />
                <span>السبالة تحلت وحدها — {alert} — المدة : 20 دقيقة</span>
             </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="max-w-7xl mx-auto mb-20 relative z-10">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <div className="space-y-8">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-emerald-50 text-emerald-600 rounded-full text-[10px] font-black uppercase tracking-widest border border-emerald-100">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              نظام الاستشعار الصوتي (IoT)
            </div>
            <h1 className="text-6xl sm:text-7xl font-black tracking-tighter leading-[0.95] text-slate-900">
              مراقبة <span className="text-emerald-500 italic">صوت</span> <br />
              النباتات الذكية.
            </h1>
            <p className="text-slate-500 text-xl font-medium max-w-lg leading-relaxed">
              نظام متصل بالمستشعرات الحقلية (Simulator) يكتشف عطش النباتات عبر الترددات فوق الصوتية (Ultrasonic Cavitation) ويفعل الري التلقائي.
            </p>
            <div className="flex gap-6">
              <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm flex items-center gap-4">
                 <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center"><Activity className="w-6 h-6" /></div>
                 <div><p className="text-2xl font-black">{stats.total_readings}</p><p className="text-[10px] font-bold text-slate-400">قراءات مباشرة</p></div>
              </div>
              <div className="bg-white p-6 rounded-3xl border border-slate-100 shadow-sm flex items-center gap-4">
                 <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center"><Droplets className="w-6 h-6" /></div>
                 <div><p className="text-2xl font-black">{stats.water_saved}%</p><p className="text-[10px] font-bold text-slate-400">توفير المياه</p></div>
              </div>
            </div>
          </div>

          <div className="relative">
            <div className="hidden lg:block absolute -top-20 -right-20 opacity-20"><FarmerIllustration /></div>
            <div className="bg-white rounded-[3.5rem] p-10 shadow-2xl border border-slate-100 relative overflow-hidden group">
               <div className="flex justify-between items-center mb-8">
                   <h3 className="text-2xl font-black">تحليل حقيقي (IoT)</h3>
                   <button
                     onClick={toggleSimulation}
                     disabled={simLoading || apiError}
                     className={`px-4 py-1.5 rounded-full text-[10px] font-black uppercase transition-all flex items-center gap-2 ${
                       stats.simulation_active
                         ? 'bg-red-50 text-red-600 hover:bg-red-100'
                         : 'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'
                     } disabled:opacity-50`}
                   >
                     <span className={`w-1.5 h-1.5 rounded-full ${stats.simulation_active ? 'bg-red-500 animate-pulse' : 'bg-slate-400'}`} />
                     {simLoading ? '...' : stats.simulation_active ? 'Stop Sim' : 'Start Sim'}
                   </button>
                </div>
                {apiError && (
                  <div className="mb-4 px-4 py-2 bg-red-50 border border-red-200 text-red-600 text-xs font-bold rounded-2xl">
                    ⚠️ Cannot reach backend on port 8000 — start the server first.
                  </div>
                )}
               <div className="space-y-8">
                  <div className="p-8 bg-slate-50 rounded-[2.5rem] border border-slate-100 relative overflow-hidden">
                    <WaveformVisualizer color="#10b981" />
                    <div className="absolute inset-0 flex items-center justify-center">
                       <p className="text-4xl font-black text-slate-900 font-mono">49.6 <span className="text-lg opacity-30">kHz</span></p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                     <div className="p-4 bg-white rounded-2xl border border-slate-100">
                        <p className="text-[10px] font-black text-slate-400 uppercase">تردد القمة</p>
                        <p className="text-lg font-black text-emerald-500">Khait Baseline ✓</p>
                     </div>
                     <div className="p-4 bg-white rounded-2xl border border-slate-100">
                        <p className="text-[10px] font-black text-slate-400 uppercase">دقة الـ CNN</p>
                        <p className="text-lg font-black text-slate-800">84.7%</p>
                     </div>
                  </div>
               </div>
            </div>
            <button onClick={() => navigate('/farmer-dashboard')} className="absolute -top-6 -left-6 w-14 h-14 bg-white rounded-2xl shadow-xl border border-slate-100 flex items-center justify-center text-slate-400 hover:text-emerald-500 transition-all z-20"><ChevronLeft className="w-6 h-6 rotate-180" /></button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto mb-10 flex items-center gap-6 relative z-10">
        <h2 className="text-3xl font-black tracking-tight text-slate-800">حالة النباتات الآن (IoT Simulator)</h2>
        <div className="h-px flex-1 bg-slate-100" />
      </div>

      <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6 mb-20 relative z-10">
        {plants.map((plant) => (
          <motion.div 
            key={plant.plant_id}
            onClick={() => setSelectedPlant(plant.plant_id)}
            whileHover={{ y: -5 }}
            className={`p-6 rounded-[2.5rem] border transition-all cursor-pointer bg-white ${selectedPlant === plant.plant_id ? 'border-emerald-500 ring-4 ring-emerald-500/5 shadow-xl' : 'border-slate-100 shadow-sm'}`}
          >
            <div className="flex justify-between items-center mb-6">
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${selectedPlant === plant.plant_id ? 'bg-emerald-500 text-white' : 'bg-slate-50 text-slate-400'}`}><Activity className="w-5 h-5" /></div>
              <div className={`px-3 py-1 rounded-full text-[9px] font-black uppercase ${plant.stress_type === 'DRY' ? 'bg-red-50 text-red-500' : 'bg-emerald-50 text-emerald-500'}`}>{plant.stress_type}</div>
            </div>
            <h3 className="font-black text-slate-900 mb-1">{plant.plant_id}</h3>
            <p className="text-[9px] text-slate-400 font-medium mb-4 truncate">{plant.species || '—'}</p>
            <div className="space-y-3">
              <div className="h-1.5 bg-slate-50 rounded-full overflow-hidden">
                 <motion.div animate={{ width: `${plant.confidence}%` }} className="h-full bg-emerald-500" />
              </div>
              {/* Live sensor chips */}
              <div className="grid grid-cols-3 gap-1 text-center">
                <div className="bg-blue-50 rounded-xl p-1.5">
                  <Droplets className="w-3 h-3 text-blue-400 mx-auto mb-0.5" />
                  <p className="text-[8px] font-black text-blue-600">{plant.vwc ?? '—'}</p>
                </div>
                <div className="bg-amber-50 rounded-xl p-1.5">
                  <Thermometer className="w-3 h-3 text-amber-400 mx-auto mb-0.5" />
                  <p className="text-[8px] font-black text-amber-600">{plant.temperature ?? '—'}°</p>
                </div>
                <div className="bg-sky-50 rounded-xl p-1.5">
                  <Wind className="w-3 h-3 text-sky-400 mx-auto mb-0.5" />
                  <p className="text-[8px] font-black text-sky-600">{plant.humidity ?? '—'}%</p>
                </div>
              </div>
              <div className={`py-3 rounded-xl text-center text-[9px] font-black uppercase ${plant.action === 'IRRIGATE_NOW' ? 'bg-red-500 text-white animate-pulse' : 'bg-slate-50 text-slate-400'}`}>
                {plant.action.replace('_', ' ')}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="max-w-7xl mx-auto mb-20 relative z-10">
        <div className="grid lg:grid-cols-3 gap-12">
          <div className="lg:col-span-1 bg-white rounded-[3rem] p-10 border border-slate-100 shadow-sm space-y-8">
            <div className="flex justify-between items-start">
               <div className="w-16 h-16 bg-emerald-50 text-emerald-600 rounded-3xl flex items-center justify-center"><Volume2 className="w-8 h-8" /></div>
               <div className="flex gap-1 h-12 items-end">{[...Array(10)].map((_, i) => <motion.div key={i} animate={{ height: [5, Math.random() * 40, 5] }} transition={{ duration: 1, repeat: Infinity, delay: i * 0.1 }} className="w-1 bg-emerald-500/20 rounded-full" />)}</div>
            </div>
            <h2 className="text-3xl font-black text-slate-900">تحليل <span className="text-emerald-500">البصمة</span> الصوتية.</h2>
            <p className="text-slate-500 font-medium leading-relaxed">
              النبضات الصوتية المكتشفة للنبتة <b>({selectedPlant})</b> تتبع نمط Cavitation الصادر عن انهيار فقاعات الهواء في أنابيب الخشب (Xylem).
            </p>
            <div className="space-y-4">
               <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-between">
                  <span className="text-[10px] font-black text-slate-400">تردد الذروة</span>
                  <span className="font-black text-emerald-600">49.6 kHz</span>
               </div>
               <div className="p-4 bg-slate-50 rounded-2xl border border-slate-100 flex items-center justify-between">
                  <span className="text-[10px] font-black text-slate-400">التفسير</span>
                  <span className="font-black text-slate-900">{selectedPlantData.stress_type === 'DRY' ? 'إجهاد مائي' : 'حالة صحية'}</span>
               </div>
            </div>
            <button onClick={() => speak(`تحليل البصمة الصوتية للنبتة ${selectedPlant.replace('_', ' ')} يظهر إجهاداً مائياً، تم تفعيل الري التلقائي`, 'derja')} className="w-full py-5 bg-slate-900 text-white rounded-2xl font-black text-sm flex items-center justify-center gap-3"><Volume2 className="w-5 h-5" /> استمع للتقرير (Derja)</button>
          </div>

          <div className="lg:col-span-2 bg-white rounded-[4rem] p-10 sm:p-14 border border-slate-100 shadow-2xl">
             <div className="flex flex-wrap justify-between items-center mb-10 gap-4">
               <div>
                 <h3 className="text-xl font-black">مراقبة حية (IoT Simulation)</h3>
                 <p className="text-[10px] font-black text-slate-400">LIVE DATA STREAM — {selectedPlant}</p>
               </div>
               <div className="flex items-center gap-2">
                 {CHART_DATASETS.map(m => (
                   <button
                     key={m}
                     onClick={() => setChartMetric(m)}
                     className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase transition-all ${
                       chartMetric === m
                         ? 'bg-emerald-500 text-white shadow-md'
                         : 'bg-slate-50 text-slate-400 hover:bg-slate-100'
                     }`}
                   >
                     {m === 'confidence' ? 'ثقة' : m === 'vwc' ? 'VWC' : 'Temp'}
                   </button>
                 ))}
                 <div className="px-4 py-1 bg-emerald-50 text-emerald-600 rounded-full text-[10px] font-black animate-pulse ml-2">LIVE</div>
               </div>
             </div>
             <div className="h-[400px]">
               {history.length === 0
                 ? <div className="h-full flex items-center justify-center text-slate-300 font-black text-sm">جارٍ تحميل البيانات...</div>
                 : <Line data={chartData} options={chartOptions} />}
             </div>
          </div>
        </div>
      </div>

      <footer className="max-w-7xl mx-auto pt-20 border-t border-slate-100 text-center relative z-10"><p className="text-slate-400 text-sm font-medium">© 2026 IRA Agriculture Monitor — منصة الفلاحة الذكية بتونس (IoT Simulation Mode)</p></footer>
      
      <AgriAgent />
    </div>
  );
};

export default PlantSound;
