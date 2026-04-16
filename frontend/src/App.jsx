import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
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
  AlertTriangle,
  Plus,
  ArrowLeft,
  Filter
} from 'lucide-react';

import { api } from './api/client';
import Form from './components/Form';
import ResultsPanel from './components/ResultsPanel';

// --- Simulation de données ---
const MOCK_TRANSACTIONS = [
  { id: 'TX_A1B2C3D4E', amount: 15400, currency: 'MAD', date: 'Aujourd\'hui, 14:32', location: 'Casablanca, MA', type: 'Virement', risk: 'high', score: 0.89, raw: { transaction_id: 'TX_A1B2C3D4E', transaction_amount: 15400, currency: 'MAD', hour: 14, minute: 32, transaction_type: 'transfer', merchant_category: 'wallet', city: 'Casablanca', country: 'Maroc', device_type: 'Mobile App', kyc_verified: false, otp_used: false, avg_amount_30d: 2000, txn_count_today: 4, selected_model: 'xgboost' } },
  { id: 'TX_X9Y8Z7W6V', amount: 450, currency: 'MAD', date: 'Aujourd\'hui, 11:15', location: 'Rabat, MA', type: 'Paiement', risk: 'low', score: 0.05, raw: { transaction_id: 'TX_X9Y8Z7W6V', transaction_amount: 450, currency: 'MAD', hour: 11, minute: 15, transaction_type: 'payment', merchant_category: 'retail', city: 'Rabat', country: 'Maroc', device_type: 'POS', kyc_verified: true, otp_used: true, avg_amount_30d: 600, txn_count_today: 1, selected_model: 'xgboost' } },
  { id: 'TX_M5P4O3N2M', amount: 8900, currency: 'MAD', date: 'Hier, 23:45', location: 'Paris, FR', type: 'Achat en ligne', risk: 'medium', score: 0.55, raw: { transaction_id: 'TX_M5P4O3N2M', transaction_amount: 8900, currency: 'MAD', hour: 23, minute: 45, transaction_type: 'online_purchase', merchant_category: 'electronics', city: 'Paris', country: 'France', device_type: 'Browser', kyc_verified: true, otp_used: false, avg_amount_30d: 4000, txn_count_today: 2, selected_model: 'random_forest' } },
  { id: 'TX_J1K2L3M4N', amount: 120, currency: 'MAD', date: 'Hier, 09:10', location: 'Marrakech, MA', type: 'Paiement', risk: 'low', score: 0.02, raw: { transaction_id: 'TX_J1K2L3M4N', transaction_amount: 120, currency: 'MAD', hour: 9, minute: 10, transaction_type: 'payment', merchant_category: 'food', city: 'Marrakech', country: 'Maroc', device_type: 'POS', kyc_verified: true, otp_used: true, avg_amount_30d: 1500, txn_count_today: 1, selected_model: 'xgboost' } },
  { id: 'TX_D9F8E7C6B', amount: 25000, currency: 'MAD', date: '14 Avril, 03:20', location: 'Inconnue', type: 'Virement', risk: 'high', score: 0.94, raw: { transaction_id: 'TX_D9F8E7C6B', transaction_amount: 25000, currency: 'MAD', hour: 3, minute: 20, transaction_type: 'transfer', merchant_category: 'crypto', city: 'Unknown', country: 'Unknown', device_type: 'Mobile App', kyc_verified: false, otp_used: false, avg_amount_30d: 500, txn_count_today: 5, selected_model: 'xgboost' } },
];

const App = () => {
  const [activePage, setActivePage] = useState('landing'); // landing, dashboard, detail
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  // Analysis State
  const [isLoading, setIsLoading] = useState(false);
  const [analysisType, setAnalysisType] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState({ status: 'loading' });
  const [elapsedTime, setElapsedTime] = useState(0);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmProvider, setLlmProvider] = useState('local');
  
  // Modals & Navigation
  const [isNewAnalysisModalOpen, setIsNewAnalysisModalOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState(null);

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

  const formDataRef = useRef(formData);
  formDataRef.current = formData;
  const llmProviderRef = useRef(llmProvider);
  llmProviderRef.current = llmProvider;

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

  const handleAnalysis = useCallback(async (type, customData = null) => {
    const currentFormData = customData || formDataRef.current;
    
    // Si on lance depuis la modale, on ferme la modale et on navigue vers detail
    setIsNewAnalysisModalOpen(false);
    setSelectedTx({ 
       id: currentFormData.transaction_id, 
       raw: currentFormData 
    });
    setActivePage('detail');
    
    setIsLoading(true);
    setAnalysisType(type);
    setResult(null);
    setError(null);
    setElapsedTime(0);
    setLlmLoading(false);

    try {
      if (type === 'full') {
        const shapData = await api.explainShap(currentFormData);
        setResult({ ...shapData, explanation: null, llm_model: null });
        setIsLoading(false);

        setLlmLoading(true);
        try {
          const llmData = await api.explainLlm({
            ...currentFormData,
            fraud_probability: shapData.fraud_probability,
            top_features: shapData.top_features,
            threshold: shapData.threshold_used,
            llm_provider: llmProviderRef.current,
          });
          setResult(prev => prev ? { 
            ...prev, 
            explanation: llmData.explanation, 
            llm_model: llmData.llm_model,
            llm_provider: llmData.llm_provider || 'local',
            processing_time_ms: prev.processing_time_ms + llmData.processing_time_ms 
          } : prev);
        } catch (llmErr) {
          console.warn('LLM explanation failed', llmErr);
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
      const message = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : "Erreur de connexion Backend.");
      setError(message);
      setIsLoading(false);
    }
  }, []);

  const handleQuickAnalysis = useCallback(() => handleAnalysis('quick'), [handleAnalysis]);
  const handleFullAnalysis = useCallback(() => handleAnalysis('full'), [handleAnalysis]);

  const startAnalysisFromHistory = (tx) => {
    setFormData(tx.raw);
    handleAnalysis('full', tx.raw);
  };

  // --- Views ---

  const landingView = useMemo(() => (
    <div className="min-h-screen bg-background relative flex flex-col">
      <nav className="w-full px-8 py-6 flex justify-between items-center bg-background/90 backdrop-blur-md border-b border-border z-40 sticky top-0">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-7 h-7 text-primary" />
          <span className="text-xl font-bold tracking-tight text-content">FraudIA</span>
        </div>
        <button 
          onClick={() => setActivePage('dashboard')}
          className="btn-primary text-sm font-semibold"
        >
          Accéder au dashboard
        </button>
      </nav>

      <main className="flex-1 flex flex-col justify-center items-center px-6 py-20">
        <div className="max-w-3xl mx-auto text-center">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            className="text-5xl md:text-7xl font-serif text-content leading-tight mb-6"
          >
            Chaque alerte mérite une <span className="text-primary italic">explication.</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.1 }}
            className="text-lg md:text-xl text-content-muted mb-12 max-w-2xl mx-auto"
          >
            Passez de la détection "boîte noire" à l'investigation IA transparente. Une plateforme analytique conçue pour les équipes de lutte contre la fraude financière.
          </motion.p>
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, delay: 0.2 }}>
            <button 
              onClick={() => setActivePage('dashboard')}
              className="bg-content text-white px-8 py-4 rounded-full font-medium text-lg hover:bg-content/90 transition-transform hover:scale-105 active:scale-95 shadow-soft flex items-center gap-2 mx-auto"
            >
              Démarrer l'investigation <ChevronRight className="w-5 h-5" />
            </button>
          </motion.div>

          <motion.div 
            initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.4 }}
            className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6"
          >
            {[
              { label: "Transactions Analysées", val: "24.5M", icon: Activity },
              { label: "Fraudes Détectées", val: "142k", icon: Target },
              { label: "Précision Modèle", val: "99.4%", icon: Zap }
            ].map((stat, i) => (
              <div key={i} className="card p-6 flex flex-col items-center text-center">
                <stat.icon className="w-6 h-6 text-primary mb-4" />
                <p className="text-4xl font-serif text-content mb-2">{stat.val}</p>
                <p className="text-xs font-bold text-content-muted uppercase tracking-widest">{stat.label}</p>
              </div>
            ))}
          </motion.div>
        </div>
      </main>
    </div>
  ), []);

  const dashboardView = (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => setActivePage('landing')}>
              <ShieldCheck className="w-6 h-6 text-primary" />
              <span className="font-bold text-lg">FraudIA</span>
            </div>
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-content-muted">
              <span className="text-content pb-1 border-b-2 border-primary cursor-pointer">Opérations</span>
              <span className="hover:text-content transition-colors cursor-pointer">Analytiques</span>
              <span className="hover:text-content transition-colors cursor-pointer">Modèles</span>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 text-xs font-bold uppercase ${health.status === 'healthy' ? 'text-success' : 'text-danger'}`}>
              <div className={`w-2 h-2 rounded-full ${health.status === 'healthy' ? 'bg-success' : 'bg-danger animate-pulse'}`}></div>
              {health.status === 'healthy' ? 'API Active' : 'API Injoignable'}
            </div>
            <button 
              onClick={() => setIsNewAnalysisModalOpen(true)}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Plus className="w-4 h-4" /> Nouvelle Analyse
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-serif mb-2 text-content">Transactions Récentes</h1>
            <p className="text-content-muted text-sm">Surveillance du pipeline d'inférence en temps réel.</p>
          </div>
          <div className="flex gap-2">
            <button className="px-3 py-1.5 border border-border rounded-md text-sm font-medium text-content flex items-center gap-2 hover:bg-surface">
              <Filter className="w-4 h-4" /> Filtrer
            </button>
          </div>
        </div>

        <div className="card overflow-hidden bg-white">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border bg-surface/50 text-xs font-bold text-content-muted uppercase tracking-widest">
                <th className="p-4 font-medium">ID Transaction</th>
                <th className="p-4 font-medium">Date & Heure</th>
                <th className="p-4 font-medium">Montant</th>
                <th className="p-4 font-medium">Localisation</th>
                <th className="p-4 font-medium text-right">Statut / Score</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_TRANSACTIONS.map((tx) => (
                <tr 
                  key={tx.id} 
                  onClick={() => startAnalysisFromHistory(tx)}
                  className="border-b border-border hover:bg-surface/50 transition-colors cursor-pointer group"
                >
                  <td className="p-4 font-mono text-sm font-medium text-content">{tx.id}</td>
                  <td className="p-4 text-sm text-content-muted">{tx.date}</td>
                  <td className="p-4 text-sm font-medium text-content">{tx.amount.toLocaleString()} {tx.currency}</td>
                  <td className="p-4 text-sm text-content-muted">{tx.location}</td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-3">
                      <span className="text-sm font-mono text-content tabular-nums">{(tx.score * 100).toFixed(1)}%</span>
                       {tx.risk === 'high' && <span className="badge badge-danger">Fraude Suspecte</span>}
                       {tx.risk === 'medium' && <span className="badge badge-warning">À Risque</span>}
                       {tx.risk === 'low' && <span className="badge badge-success">Sûre</span>}
                       <ChevronRight className="w-4 h-4 text-border group-hover:text-primary transition-colors" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
    </div>
  );

  const detailView = (
    <div className="min-h-screen bg-background">
       <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setActivePage('dashboard')}
              className="p-2 hover:bg-border/50 rounded-full transition-colors text-content-muted hover:text-content"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-mono font-bold text-content">{selectedTx?.id}</h2>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
         {error && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-danger-light border border-danger/20 rounded-lg flex items-center gap-3 text-danger text-sm font-bold"
            >
              <AlertTriangle className="w-5 h-5" />
              <span>{typeof error === 'string' ? error : JSON.stringify(error)}</span>
            </motion.div>
          )}

         <ResultsPanel
            result={result}
            isLoading={isLoading}
            analysisType={analysisType}
            elapsedTime={elapsedTime}
            llmLoading={llmLoading}
            formData={formData}
            llmProvider={result?.llm_provider || llmProvider}
          />
      </main>
    </div>
  );

  return (
    <div className="min-h-screen font-sans text-content selection:bg-primary/20">
      {activePage === 'landing' && landingView}
      {activePage === 'dashboard' && dashboardView}
      {activePage === 'detail' && detailView}

      {/* Modal / Sidebar pour Nouvelle Analyse */}
      <AnimatePresence>
        {isNewAnalysisModalOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setIsNewAnalysisModalOpen(false)}
              className="fixed inset-0 bg-content/20 backdrop-blur-sm z-50"
            />
            <motion.div 
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl border-l border-border z-50 flex flex-col"
            >
               <div className="p-6 border-b border-border flex justify-between items-center bg-surface">
                 <h2 className="text-xl font-serif text-content">Simuler une transaction</h2>
                 <button onClick={() => setIsNewAnalysisModalOpen(false)} className="p-2 hover:bg-border rounded-full text-content-muted">
                    <X className="w-5 h-5" />
                 </button>
               </div>
               <div className="flex-1 overflow-y-auto p-6 bg-content/5">
                 <Form 
                    formData={formData} 
                    setFormData={setFormData}
                    onSubmit={handleQuickAnalysis}
                    onFullAnalysis={handleFullAnalysis}
                    isLoading={isLoading}
                    llmProvider={llmProvider}
                    setLlmProvider={setLlmProvider}
                 />
               </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

export default App;
