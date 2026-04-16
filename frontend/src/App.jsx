import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
  ShieldCheck, 
  LayoutDashboard, 
  Activity, 
  Settings, 
  LogOut, 
  Menu, 
  X,
  CreditCard,
  Target,
  Zap,
  ChevronRight,
  Server,
  Cpu,
  AlertTriangle
} from 'lucide-react';

import { api } from './api/client';
import Form from './components/Form';
import ResultsPanel from './components/ResultsPanel';

const App = () => {
  const [activePage, setActivePage] = useState('landing');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [analysisType, setAnalysisType] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState({ status: 'loading' });
  const [formData, setFormData] = useState({
    transaction_id: "TX_" + Math.random().toString(36).substr(2, 9).toUpperCase(),
    transaction_amount: 15000,
    currency: "MAD",
    hour: 2,
    minute: 0,
    transaction_type: "transfer",
    merchant_category: "crypto",
    city: "Casablanca",
    country: "Maroc",
    device_type: "Mobile App",
    kyc_verified: true,
    otp_used: false,
    avg_amount_30d: 1000,
    txn_count_today: 2,
    selected_model: "xgboost"
  });
  const [elapsedTime, setElapsedTime] = useState(0);
  const formDataRef = useRef(formData);
  formDataRef.current = formData;

  useEffect(() => {
    if (isLoading) return;
    const fetchHealth = async () => {
      try {
        const data = await api.checkHealth();
        setHealth(prev => prev.status === data.status ? prev : data);
      } catch {
        setHealth(prev => prev.status === 'unhealthy' ? prev : { status: 'unhealthy' });
      }
    };
    fetchHealth();
    const interval = setInterval(fetchHealth, 60000);
    return () => clearInterval(interval);
  }, [isLoading]);

  useEffect(() => {
    if (!isLoading) { setElapsedTime(0); return; }
    const t = setInterval(() => setElapsedTime(p => p + 1), 1000);
    return () => clearInterval(t);
  }, [isLoading]);

  const [llmLoading, setLlmLoading] = useState(false);

  const handleAnalysis = useCallback(async (type) => {
    const currentFormData = formDataRef.current;
    setIsLoading(true);
    setAnalysisType(type);
    setResult(null);
    setError(null);
    setElapsedTime(0);
    setLlmLoading(false);
    try {
      if (type === 'full') {
        // Phase 1: SHAP (rapide ~2-3s) → affiche score + features immédiatement
        const shapData = await api.explainShap(currentFormData);
        setResult({ ...shapData, explanation: null, llm_model: null });
        setIsLoading(false);

        // Phase 2: LLM (lent ~15-40s) → charge en arrière-plan
        setLlmLoading(true);
        try {
          const llmData = await api.explainLlm({
            transaction_id: currentFormData.transaction_id,
            transaction_amount: currentFormData.transaction_amount,
            currency: currentFormData.currency,
            hour: currentFormData.hour,
            transaction_type: currentFormData.transaction_type,
            merchant_category: currentFormData.merchant_category,
            city: currentFormData.city,
            country: currentFormData.country,
            device_type: currentFormData.device_type,
            fraud_probability: shapData.fraud_probability,
            top_features: shapData.top_features,
            threshold: shapData.threshold_used,
          });
          setResult(prev => prev ? { ...prev, explanation: llmData.explanation, llm_model: llmData.llm_model, processing_time_ms: prev.processing_time_ms + llmData.processing_time_ms } : prev);
        } catch (llmErr) {
          console.warn('LLM explanation failed, SHAP results still shown', llmErr);
        } finally {
          setLlmLoading(false);
        }
      } else {
        const data = await api.predict(currentFormData);
        setResult(data);
        setIsLoading(false);
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : "Erreur de connexion au serveur Backend (Port 8000). V\u00e9rifiez que l'API est lanc\u00e9e.");
      setError(message);
      setIsLoading(false);
    }
  }, []);

  const handleQuickAnalysis = useCallback(() => handleAnalysis('quick'), [handleAnalysis]);
  const handleFullAnalysis = useCallback(() => handleAnalysis('full'), [handleAnalysis]);

  // --- Views ---

  const landingView = useMemo(() => (
    <div className="min-h-screen relative overflow-hidden">
      {/* Abstract Background Shapes */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-primary/10 rounded-full blur-[120px] animate-pulse-slow"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-accent/10 rounded-full blur-[120px]"></div>

      <nav className="fixed top-0 w-full z-50 px-8 py-6 flex justify-between items-center backdrop-blur-md border-b border-white/5">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-8 h-8 text-primary" />
          <span className="text-xl font-bold tracking-tighter">FraudIA</span>
        </div>
        <div className="hidden md:flex gap-8 text-sm font-medium text-slate-400">
          <a href="#" className="hover:text-white transition-colors">Vision</a>
          <a href="#" className="hover:text-white transition-colors">Tech Stack</a>
          <a href="#" className="hover:text-white transition-colors">Documentation</a>
        </div>
        <button 
          onClick={() => setActivePage('dashboard')}
          className="cyber-button cyber-button-primary text-sm"
        >
          Développer le Dashboard
        </button>
      </nav>

      <main className="container mx-auto px-6 pt-40 pb-20 relative z-10">
        <div className="max-w-4xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
          >
            <span className="inline-block px-4 py-1.5 mb-6 rounded-full border border-primary/20 bg-primary/5 text-primary text-xs font-bold uppercase tracking-widest">
              Sécurité Financière Nouvelle Génération
            </span>
            <h1 className="text-6xl md:text-8xl font-extrabold tracking-tight leading-[1.1] mb-8">
              Détectez l'invisible. <br />
              <span className="text-gradient">Anticipez la fraude.</span>
            </h1>
            <p className="text-xl text-slate-400 mb-12 max-w-2xl mx-auto leading-relaxed">
              Propulsé par des moteurs de Machine Learning multi-modèles et une explicabilité SHAP avancée. FraudIA transforme les données brutes en décisions critiques ultra-précises.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button 
                onClick={() => setActivePage('dashboard')}
                className="cyber-button cyber-button-primary px-10 h-14 flex items-center justify-center gap-2"
              >
                Explorer la Plateforme <ChevronRight className="w-5 h-5" />
              </button>
              <button className="cyber-button cyber-button-outline px-10 h-14">
                Architecture Technique
              </button>
            </div>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5, duration: 1 }}
            className="mt-32 grid grid-cols-2 lg:grid-cols-4 gap-6"
          >
            {[
              { label: "Précision", val: "99.2%", icon: Target },
              { label: "Latence", val: "< 150ms", icon: Zap },
              { label: "Volume Quotidien", val: "14k+", icon: Activity },
              { label: "Moteurs IA", val: "LLaMA/XGB", icon: Cpu }
            ].map((stat, i) => (
              <div key={i} className="glass-card p-6 text-left group">
                <stat.icon className="w-6 h-6 text-primary mb-4 group-hover:scale-110 transition-transform" />
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">{stat.label}</p>
                <p className="text-2xl font-bold text-white">{stat.val}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </main>
    </div>
  ), []);

  const dashboardView = (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-72 bg-surface backdrop-blur-xl border-r border-white/5 transition-transform duration-300 lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-8 h-full flex flex-col">
          <div className="flex items-center gap-3 mb-12">
            <ShieldCheck className="w-8 h-8 text-primary shadow-[0_0_15px_rgba(56,189,248,0.5)]" />
            <span className="text-xl font-bold tracking-tighter">FraudIA</span>
          </div>

          <nav className="flex-1 space-y-2">
            {[
              { id: 'home', icon: LayoutDashboard, label: 'Analytiques' },
              { id: 'logs', icon: Activity, label: 'Flux en Direct' },
              { id: 'settings', icon: Settings, label: 'Configuration' }
            ].map(item => (
              <button 
                key={item.id}
                className={`w-full flex items-center gap-4 px-4 py-3 rounded-xl transition-all ${item.id === 'home' ? 'bg-primary/10 text-primary' : 'text-slate-400 hover:text-white hover:bg-white/5'}`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </button>
            ))}
          </nav>

          <div className="mt-auto pt-8 border-t border-white/5">
            <div className="flex items-center gap-3 p-4 glass-card mb-4">
              <div className={`w-2 h-2 rounded-full ${health.status === 'healthy' ? 'bg-success' : 'bg-danger animate-pulse'}`}></div>
              <span className="text-xs font-bold uppercase tracking-widest text-slate-400">
                Moteur IA : {health.status === 'healthy' ? 'EN LIGNE' : 'ERREUR'}
              </span>
            </div>
            <button 
              onClick={() => setActivePage('landing')}
              className="w-full flex items-center gap-4 px-4 py-3 rounded-xl text-slate-500 hover:text-danger hover:bg-danger/5 transition-all"
            >
              <LogOut className="w-5 h-5" />
              <span className="font-medium text-sm">Quitter</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 lg:ml-72 bg-gradient-to-b from-background to-black">
        <header className="px-8 py-6 flex justify-between items-center border-b border-white/5 sticky top-0 z-40 bg-background/80 backdrop-blur-lg">
          <div className="flex items-center gap-4">
            <button onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden text-white">
              {sidebarOpen ? <X /> : <Menu />}
            </button>
            <h2 className="text-2xl font-bold text-white tracking-tight">Analyse en Temps Réel</h2>
          </div>
          <div className="flex items-center gap-6">
            <div className="flex gap-2">
               <span className="px-3 py-1 bg-slate-800 rounded-lg text-xs font-bold text-slate-400 uppercase">Modèle : {formData.selected_model}</span>
               <span className="px-3 py-1 bg-primary/10 rounded-lg text-xs font-bold text-primary uppercase">v2.1 Stable</span>
            </div>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent p-[1px]">
              <div className="w-full h-full bg-slate-900 rounded-[11px] flex items-center justify-center font-bold text-xs">PF</div>
            </div>
          </div>
        </header>

        <main className="p-8 pb-20">
          <div className="grid grid-cols-12 gap-8 max-w-[1400px] mx-auto">
            {error && (
              <motion.div 
                initial={{ opacity: 0, y: -10 }} 
                animate={{ opacity: 1, y: 0 }}
                className="col-span-12 p-4 bg-danger/10 border border-danger/20 rounded-2xl flex items-center gap-3 text-danger text-sm font-bold"
              >
                <AlertTriangle className="w-5 h-5" />
                <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
              </motion.div>
            )}
            
            {/* Form Column */}
            <div className="col-span-12 xl:col-span-4 space-y-6">
              <div className="glass-card p-8 border-l-4 border-l-primary/50 relative overflow-hidden group">
                <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
                  <CreditCard className="w-20 h-20 text-white" />
                </div>
                <h3 className="text-lg font-bold text-white mb-6">Paramètres Transaction</h3>
                <Form 
                   formData={formData} 
                   setFormData={setFormData}
                   onSubmit={handleQuickAnalysis}
                   onFullAnalysis={handleFullAnalysis}
                   isLoading={isLoading}
                />
              </div>

              <div className="glass-card p-6 bg-accent/5 border-white/10">
                <div className="flex gap-4 items-center">
                  <div className="w-12 h-12 rounded-2xl bg-accent/20 flex items-center justify-center text-accent">
                    <Server className="w-6 h-6" />
                  </div>
                  <div>
                    <h4 className="font-bold text-white text-sm">Système d'Inférence</h4>
                    <p className="text-xs text-slate-500">Node: LocalHost.8000 · Morocco-CAS</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Content Column */}
            <div className="col-span-12 xl:col-span-8">
              <ResultsPanel
                result={result}
                isLoading={isLoading}
                analysisType={analysisType}
                elapsedTime={elapsedTime}
                llmLoading={llmLoading}
                formData={formData}
              />
            </div>
          </div>
        </main>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen">
      {activePage === 'landing' ? landingView : dashboardView}
    </div>
  );
};

export default App;
