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
  Filter,
  User,
  Search,
  XCircle,
  Download,
  FileText,
  FileSpreadsheet,
  Upload,
  Loader2,
  CheckCircle2,
  XOctagon,
  HelpCircle,
  Trash2
} from 'lucide-react';

import { api } from './api/client';
import Form from './components/Form';
import ResultsPanel from './components/ResultsPanel';
import LoginPage from './components/LoginPage';
import AnalyticsPage from './components/AnalyticsPage';

const App = () => {
  // Auth state
  const [user, setUser] = useState(() => api.getStoredUser());
  const [userTransactions, setUserTransactions] = useState([]);

  const [activePage, setActivePage] = useState('landing');
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Analysis State
  const [isLoading, setIsLoading] = useState(false);
  const [analysisType, setAnalysisType] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState({ status: 'loading' });
  const [elapsedTime, setElapsedTime] = useState(0);
  const [llmLoading, setLlmLoading] = useState(false);
  const [llmProvider, setLlmProvider] = useState('perplexity');

  // Modals & Navigation
  const [isNewAnalysisModalOpen, setIsNewAnalysisModalOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState(null);

  // Filters
  const [showFilters, setShowFilters] = useState(false);
  const [filterRisk, setFilterRisk] = useState('all');
  const [filterModel, setFilterModel] = useState('all');
  const [filterSearch, setFilterSearch] = useState('');

  // Export dropdown
  const [exportDropdownTx, setExportDropdownTx] = useState(null);

  // Batch upload
  const [batchLoading, setBatchLoading] = useState(false);
  const [batchResults, setBatchResults] = useState(null);
  const batchFileRef = useRef(null);

  const [formData, setFormData] = useState({
    transaction_id: "TX_" + Math.random().toString(36).substr(2, 9).toUpperCase(),
    // ── Champs Critiques (Alidgnés avec le Modèle) ─────────────────────────
    transaction_amount: 250,
    transaction_type: "purchase",
    merchant_category: "grocery",
    payment_method: "bkash",
    card_type: "debit",
    kyc_verified: true,
    otp_used: true,
    user_account_age_days: 365,
    txn_count_24h: 1,
    txn_sum_24h: 250,
    time_since_last_txn: 720,
    is_new_city: 0,
    
    // ── Détails & Métadonnées (Contexte uniquement - Secondaire) ──────────
    avg_amount_30d: 220,
    city: "Dhaka",
    country: "Bangladesh",
    currency: "BDT",
    device_type: "mobile",
    hour: 14,
    selected_model: "xgboost"
  });

  const formDataRef = useRef(formData);
  formDataRef.current = formData;
  const llmProviderRef = useRef(llmProvider);
  llmProviderRef.current = llmProvider;
  const userRef = useRef(user);
  userRef.current = user;

  // ── Auth handlers ──
  const handleLogin = useCallback((data) => {
    setUser(data.user);
    setActivePage('dashboard');
  }, []);

  const handleLogout = useCallback(() => {
    api.logout();
    setUser(null);
    setUserTransactions([]);
    setActivePage('landing');
    setResult(null);
  }, []);

  // Load user transactions when user is set and on dashboard
  useEffect(() => {
    if (!user) return;
    const loadTx = async () => {
      try {
        const txs = await api.getTransactions();
        setUserTransactions(txs);
      } catch (e) {
        console.warn('Could not load transactions', e);
      }
    };
    loadTx();
  }, [user, activePage]);

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

  const reloadTransactions = useCallback(async () => {
    if (!userRef.current) return;
    try {
      const txs = await api.getTransactions();
      setUserTransactions(txs);
    } catch (_) { }
  }, []);

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

        // Sauvegarder la transaction avec les résultats SHAP
        let savedRowId = null;
        if (userRef.current) {
          try {
            const saveResp = await api.saveTransaction({
              transaction_id: currentFormData.transaction_id,
              fraud_probability: shapData.fraud_probability,
              risk_level: shapData.risk_level,
              is_fraud: shapData.is_fraud,
              model_name: shapData.model_name || currentFormData.selected_model,
              form_data: currentFormData,
              result_data: shapData,
            });
            savedRowId = saveResp.id;
            reloadTransactions();
          } catch (e) { console.warn('Save tx failed', e); }
        }

        setLlmLoading(true);
        try {
          const llmData = await api.explainLlm({
            ...currentFormData,
            fraud_probability: shapData.fraud_probability,
            top_features: shapData.top_features,
            threshold: shapData.threshold_used,
            llm_provider: llmProviderRef.current,
          });
          const fullResult = {
            ...shapData,
            explanation: llmData.explanation,
            llm_model: llmData.llm_model,
            llm_provider: llmData.llm_provider || 'local',
            processing_time_ms: shapData.processing_time_ms + llmData.processing_time_ms
          };
          setResult(fullResult);

          // Mettre à jour la transaction avec l'explication LLM
          if (userRef.current && savedRowId) {
            try {
              await api.updateTransaction(savedRowId, {
                explanation: llmData.explanation,
                result_data: fullResult,
              });
              reloadTransactions();
            } catch (_) { }
          }
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

  const startAnalysisFromHistory = useCallback((tx) => {
    // Restaurer le formulaire
    const raw = typeof tx.form_data === 'string' ? JSON.parse(tx.form_data) : (tx.raw || tx.form_data || tx);
    setFormData(raw);

    // Si on a le résultat complet sauvegardé, on le restaure directement
    let savedResult = tx.result_data;
    if (typeof savedResult === 'string') {
      try { savedResult = JSON.parse(savedResult); } catch (_) { savedResult = null; }
    }

    if (savedResult && savedResult.fraud_probability !== undefined) {
      setSelectedTx({ id: tx.transaction_id, raw, dbId: tx.id, annotation: tx.annotation || null });
      setActivePage('detail');
      setResult(savedResult);
      setIsLoading(false);
      setLlmLoading(false);
      setError(null);
      setAnalysisType('full');
    } else {
      // Pas de résultat sauvegardé, relancer l'analyse
      handleAnalysis('full', raw);
    }
  }, [handleAnalysis]);

  // ── Export PDF/CSV ──
  const exportTransaction = useCallback((tx, format) => {
    setExportDropdownTx(null);
    const form = typeof tx.form_data === 'string' ? JSON.parse(tx.form_data) : tx.form_data || {};
    let savedResult = tx.result_data;
    if (typeof savedResult === 'string') {
      try { savedResult = JSON.parse(savedResult); } catch (_) { savedResult = {}; }
    }
    savedResult = savedResult || {};

    const featureLabels = {
      is_night: 'Heure nocturne', transaction_amount: 'Montant', merchant_category: 'Catégorie marchand',
      otp_used: 'OTP utilisé', kyc_verified: 'KYC vérifié', device_type: 'Type appareil',
      transaction_type: 'Type transaction', hour: 'Heure', city: 'Ville', country: 'Pays',
    };

    if (format === 'csv') {
      const lines = [
        ['Rapport FraudIA - Transaction ' + tx.transaction_id],
        [''],
        ['== Informations Générales =='],
        ['ID Transaction', tx.transaction_id],
        ['Date Analyse', new Date(tx.created_at).toLocaleString('fr-FR')],
        ['Modèle', tx.model_name?.toUpperCase()],
        [''],
        ['== Résultat =='],
        ['Score de Fraude', (tx.fraud_probability * 100).toFixed(1) + '%'],
        ['Niveau de Risque', tx.risk_level],
        ['Décision', tx.is_fraud ? 'Fraude Suspecte' : 'Transaction Valide'],
        ['Annotation', tx.annotation || 'Non annotée'],
        [''],
        ['== Détails Transaction =='],
        ['Montant', form.transaction_amount + ' ' + (form.currency || 'MAD')],
        ['Heure', (form.hour ?? '') + 'h' + (form.minute ?? '00')],
        ['Type', form.transaction_type],
        ['Catégorie', form.merchant_category],
        ['Ville', form.city],
        ['Pays', form.country],
        ['Appareil', form.device_type],
        ['KYC Vérifié', form.kyc_verified ? 'Oui' : 'Non'],
        ['OTP Utilisé', form.otp_used ? 'Oui' : 'Non'],
      ];

      if (savedResult.top_features?.length) {
        lines.push([''], ['== Facteurs SHAP =='], ['Variable', 'Impact SHAP', 'Direction']);
        savedResult.top_features.forEach(f => {
          lines.push([featureLabels[f.feature] || f.feature, f.shap_value?.toFixed(3), f.direction]);
        });
      }

      if (savedResult.explanation) {
        lines.push([''], ['== Rapport LLM =='], [savedResult.explanation]);
      }

      const csv = lines.map(l => l.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
      const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FraudIA_${tx.transaction_id}_${new Date().toISOString().slice(0, 10)}.csv`;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } else if (format === 'pdf') {
      import('jspdf').then(({ default: jsPDF }) => {
        import('jspdf-autotable').then((autoTableModule) => {
          const autoTable = autoTableModule.default || autoTableModule;
          const doc = new jsPDF();
          const pageW = doc.internal.pageSize.getWidth();

          // Header
          doc.setFillColor(15, 23, 42);
          doc.rect(0, 0, pageW, 35, 'F');
          doc.setTextColor(255, 255, 255);
          doc.setFontSize(20);
          doc.setFont('helvetica', 'bold');
          doc.text('FraudIA', 14, 18);
          doc.setFontSize(10);
          doc.setFont('helvetica', 'normal');
          doc.text('Rapport d\'analyse de transaction', 14, 27);
          doc.text(new Date().toLocaleString('fr-FR'), pageW - 14, 27, { align: 'right' });

          let y = 45;
          doc.setTextColor(0, 0, 0);

          // Transaction ID
          doc.setFontSize(14);
          doc.setFont('helvetica', 'bold');
          doc.text('Transaction : ' + tx.transaction_id, 14, y);
          y += 10;

          // Result box
          const riskColors = { FAIBLE: [34, 197, 94], MOYEN: [234, 179, 8], 'ÉLEVÉ': [239, 68, 68], ELEVÉ: [239, 68, 68], CRITIQUE: [220, 38, 38] };
          const rc = riskColors[tx.risk_level] || [100, 100, 100];
          doc.setFillColor(rc[0], rc[1], rc[2]);
          doc.roundedRect(14, y, pageW - 28, 22, 3, 3, 'F');
          doc.setTextColor(255, 255, 255);
          doc.setFontSize(12);
          doc.setFont('helvetica', 'bold');
          doc.text(`Score : ${(tx.fraud_probability * 100).toFixed(1)}%  |  Risque : ${tx.risk_level}  |  ${tx.is_fraud ? 'FRAUDE SUSPECTE' : 'TRANSACTION VALIDE'}`, 20, y + 14);
          y += 32;
          doc.setTextColor(0, 0, 0);

          // Details table
          doc.setFontSize(11);
          doc.setFont('helvetica', 'bold');
          doc.text('Détails de la transaction', 14, y);
          y += 4;
          autoTable(doc, {
            startY: y,
            head: [['Champ', 'Valeur']],
            body: [
              ['Montant', `${form.transaction_amount} ${form.currency || 'MAD'}`],
              ['Heure', `${form.hour ?? ''}h${String(form.minute ?? 0).padStart(2, '0')}`],
              ['Type', form.transaction_type || ''],
              ['Catégorie', form.merchant_category || ''],
              ['Ville', form.city || ''],
              ['Pays', form.country || ''],
              ['Appareil', form.device_type || ''],
              ['KYC', form.kyc_verified ? 'Oui' : 'Non'],
              ['OTP', form.otp_used ? 'Oui' : 'Non'],
              ['Modèle ML', tx.model_name?.toUpperCase() || ''],
              ['Annotation', tx.annotation || 'Non annotée'],
            ],
            theme: 'striped',
            headStyles: { fillColor: [15, 23, 42] },
            margin: { left: 14, right: 14 },
          });
          y = doc.lastAutoTable.finalY + 10;

          // SHAP features
          if (savedResult.top_features?.length) {
            doc.setFontSize(11);
            doc.setFont('helvetica', 'bold');
            doc.text('Facteurs d\'influence (SHAP)', 14, y);
            y += 4;
            autoTable(doc, {
              startY: y,
              head: [['Variable', 'Impact SHAP', 'Direction', 'Importance']],
              body: savedResult.top_features.map(f => [
                featureLabels[f.feature] || f.feature,
                f.shap_value?.toFixed(3),
                f.direction === 'fraude' ? '↑ Fraude' : '↓ Légitime',
                f.impact || '',
              ]),
              theme: 'striped',
              headStyles: { fillColor: [15, 23, 42] },
              margin: { left: 14, right: 14 },
            });
            y = doc.lastAutoTable.finalY + 10;
          }

          // LLM explanation
          if (savedResult.explanation) {
            if (y > 240) { doc.addPage(); y = 20; }
            doc.setFontSize(11);
            doc.setFont('helvetica', 'bold');
            doc.text('Rapport d\'analyse IA', 14, y);
            y += 6;
            doc.setFontSize(9);
            doc.setFont('helvetica', 'normal');
            const lines = doc.splitTextToSize(savedResult.explanation, pageW - 28);
            lines.forEach(line => {
              if (y > 280) { doc.addPage(); y = 20; }
              doc.text(line, 14, y);
              y += 4.5;
            });
          }

          // Footer
          const pages = doc.internal.getNumberOfPages();
          for (let i = 1; i <= pages; i++) {
            doc.setPage(i);
            doc.setFontSize(8);
            doc.setTextColor(150, 150, 150);
            doc.text(`FraudIA - Page ${i}/${pages}`, pageW / 2, doc.internal.pageSize.getHeight() - 8, { align: 'center' });
          }

          doc.save(`FraudIA_${tx.transaction_id}_${new Date().toISOString().slice(0, 10)}.pdf`);
        });
      });
    }
  }, []);

  // ── Annotation update ──
  const updateAnnotation = useCallback(async (tx, annotation) => {
    if (!tx?.dbId) return;
    try {
      await api.updateTransaction(tx.dbId, { annotation });
      await reloadTransactions();
    } catch (e) {
      console.warn('Annotation update failed', e);
    }
  }, [reloadTransactions]);

  // ── Batch upload handler ──
  const handleBatchUpload = useCallback(async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = '';
    setBatchLoading(true);
    setBatchResults(null);
    setActivePage('batch');
    try {
      const data = await api.batchUpload(file);
      setBatchResults(data);
      reloadTransactions();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setBatchResults({ error: typeof detail === 'string' ? detail : 'Erreur lors du traitement du fichier.' });
    } finally {
      setBatchLoading(false);
    }
  }, [reloadTransactions]);

  // --- Views ---

  const landingView = useMemo(() => (
    <div className="min-h-screen bg-background relative flex flex-col">
      <nav className="w-full px-8 py-6 flex justify-between items-center bg-background/90 backdrop-blur-md border-b border-border z-40 sticky top-0">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-7 h-7 text-primary" />
          <span className="text-xl font-bold tracking-tight text-content">FraudIA</span>
        </div>
        <button
          onClick={() => user ? setActivePage('dashboard') : setActivePage('login')}
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
              onClick={() => user ? setActivePage('dashboard') : setActivePage('login')}
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
              { label: "Transactions Analysées", val: health.model_metrics ? (health.model_metrics.training_samples / 1000000).toFixed(1) + "M+" : "24.5M", icon: Activity },
              { label: "Vitesse d'Inférence", val: "2ms", icon: Target },
              { label: "Précision Modèle", val: health.model_metrics ? (health.model_metrics.accuracy * 100).toFixed(1) + "%" : "99.4%", icon: Zap }
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
              <span onClick={() => setActivePage('analytics')} className="hover:text-content transition-colors cursor-pointer">Analytiques</span>
              {health.model_metrics && (
                <div className="flex items-center gap-4 ml-4 px-4 py-1.5 bg-surface border border-border rounded-full shadow-inner">
                   <div className="flex flex-col">
                      <span className="text-[9px] font-bold text-content-muted uppercase leading-none">Accuracy</span>
                      <span className="text-xs font-mono font-bold text-success">{(health.model_metrics.accuracy * 100).toFixed(1)}%</span>
                   </div>
                   <div className="w-px h-6 bg-border"></div>
                   <div className="flex flex-col">
                      <span className="text-[9px] font-bold text-content-muted uppercase leading-none">AUC-PR (Banque)</span>
                      <span className="text-xs font-mono font-bold text-primary">{(health.model_metrics.auc_pr).toFixed(2)}</span>
                   </div>
                </div>
              )}
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
            <button
              onClick={() => batchFileRef.current?.click()}
              className="flex items-center gap-2 text-sm px-3 py-2 border border-border rounded-lg font-medium text-content hover:bg-surface transition-colors"
            >
              <Upload className="w-4 h-4" /> Import CSV
            </button>
            <input
              ref={batchFileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={handleBatchUpload}
            />
            {user && (
              <div className="flex items-center gap-3 ml-2 pl-4 border-l border-border">
                <div className="text-right hidden md:block">
                  <p className="text-xs font-bold text-content">{user.full_name}</p>
                  <p className="text-[10px] text-content-muted">{user.email}</p>
                </div>
                <button
                  onClick={handleLogout}
                  className="p-2 hover:bg-danger-light rounded-lg transition-colors text-content-muted hover:text-danger"
                  title="Déconnexion"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-6 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-serif mb-2 text-content">Mes Analyses</h1>
            <p className="text-content-muted text-sm">Historique de vos transactions analysées — données cloisonnées par analyste.</p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowFilters(f => !f)}
              className={`px-3 py-1.5 border rounded-md text-sm font-medium flex items-center gap-2 transition-colors ${showFilters ? 'border-primary bg-primary/5 text-primary' : 'border-border text-content hover:bg-surface'
                }`}
            >
              <Filter className="w-4 h-4" /> Filtrer
              {(filterRisk !== 'all' || filterModel !== 'all' || filterSearch) && (
                <span className="w-2 h-2 rounded-full bg-primary"></span>
              )}
            </button>
          </div>
        </div>

        {/* Barre de filtres */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden mb-4"
            >
              <div className="card bg-white p-4 flex flex-wrap items-center gap-4">
                <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                  <Search className="w-4 h-4 text-content-muted" />
                  <input
                    type="text"
                    placeholder="Rechercher par ID transaction..."
                    value={filterSearch}
                    onChange={(e) => setFilterSearch(e.target.value)}
                    className="flex-1 bg-transparent text-sm text-content placeholder:text-content-muted outline-none"
                  />
                  {filterSearch && (
                    <button onClick={() => setFilterSearch('')} className="text-content-muted hover:text-content">
                      <XCircle className="w-4 h-4" />
                    </button>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-content-muted font-medium">Risque :</label>
                  <select
                    value={filterRisk}
                    onChange={(e) => setFilterRisk(e.target.value)}
                    className="text-sm border border-border rounded-md px-2 py-1 bg-white text-content"
                  >
                    <option value="all">Tous</option>
                    <option value="FAIBLE">Faible</option>
                    <option value="MOYEN">Moyen</option>
                    <option value="ÉLEVÉ">Élevé</option>
                    <option value="CRITIQUE">Critique</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-content-muted font-medium">Modèle :</label>
                  <select
                    value={filterModel}
                    onChange={(e) => setFilterModel(e.target.value)}
                    className="text-sm border border-border rounded-md px-2 py-1 bg-white text-content"
                  >
                    <option value="all">Tous</option>
                    <option value="xgboost">XGBoost</option>
                    <option value="random_forest">Random Forest</option>
                    <option value="logistic_regression">Logistic Regression</option>
                  </select>
                </div>
                {(filterRisk !== 'all' || filterModel !== 'all' || filterSearch) && (
                  <button
                    onClick={() => { setFilterRisk('all'); setFilterModel('all'); setFilterSearch(''); }}
                    className="text-xs text-danger hover:underline font-medium"
                  >
                    Réinitialiser
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="card overflow-hidden bg-white" onClick={() => exportDropdownTx && setExportDropdownTx(null)}>
          {(() => {
            const filtered = userTransactions.filter(tx => {
              if (filterRisk !== 'all' && tx.risk_level !== filterRisk && !(filterRisk === 'ÉLEVÉ' && tx.risk_level === 'ELEVÉ')) return false;
              if (filterModel !== 'all' && tx.model_name !== filterModel) return false;
              if (filterSearch && !tx.transaction_id.toLowerCase().includes(filterSearch.toLowerCase())) return false;
              return true;
            });
            const hasActiveFilter = filterRisk !== 'all' || filterModel !== 'all' || filterSearch;
            return filtered.length === 0 ? (
              <div className="p-12 text-center">
                <Activity className="w-10 h-10 text-border mx-auto mb-4" />
                {hasActiveFilter ? (
                  <>
                    <p className="text-content-muted text-sm">Aucune transaction ne correspond à vos filtres.</p>
                    <button onClick={() => { setFilterRisk('all'); setFilterModel('all'); setFilterSearch(''); }} className="text-primary text-xs mt-2 hover:underline">Réinitialiser les filtres</button>
                  </>
                ) : (
                  <>
                    <p className="text-content-muted text-sm">Aucune analyse effectuée pour l'instant.</p>
                    <p className="text-content-muted text-xs mt-1">Cliquez sur "Nouvelle Analyse" pour commencer.</p>
                  </>
                )}
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-surface/50 text-xs font-bold text-content-muted uppercase tracking-widest">
                    <th className="p-4 font-medium">ID Transaction</th>
                    <th className="p-4 font-medium">Date</th>
                    <th className="p-4 font-medium">Modèle</th>
                    <th className="p-4 font-medium">Score</th>
                    <th className="p-4 font-medium">État</th>
                    <th className="p-4 font-medium text-right">Statut</th>
                    <th className="p-4 font-medium w-10"></th>
                    <th className="p-4 font-medium w-10"></th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((tx) => {
                    const riskBadge = tx.risk_level === 'CRITIQUE' || tx.risk_level === 'ELEVÉ' || tx.is_fraud
                      ? <span className="badge badge-danger">{tx.risk_level}</span>
                      : tx.risk_level === 'MOYEN'
                        ? <span className="badge badge-warning">{tx.risk_level}</span>
                        : <span className="badge badge-success">{tx.risk_level}</span>;

                    const annotationBadge = tx.annotation === 'frauduleuse'
                      ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-danger"><XOctagon className="w-3 h-3" /> Fraude</span>
                      : tx.annotation === 'valide'
                        ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-success"><CheckCircle2 className="w-3 h-3" /> Valide</span>
                        : <span className="inline-flex items-center gap-1 text-xs text-content-muted"><HelpCircle className="w-3 h-3" /> —</span>;

                    return (
                      <tr
                        key={tx.id}
                        onClick={() => startAnalysisFromHistory(tx)}
                        className="border-b border-border hover:bg-surface/50 transition-colors cursor-pointer group"
                      >
                        <td className="p-4 font-mono text-sm font-medium text-content">{tx.transaction_id}</td>
                        <td className="p-4 text-sm text-content-muted">{new Date(tx.created_at).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</td>
                        <td className="p-4 text-sm text-content-muted uppercase">{tx.model_name}</td>
                        <td className="p-4 text-sm font-mono text-content tabular-nums">{(tx.fraud_probability * 100).toFixed(1)}%</td>
                        <td className="p-4">{annotationBadge}</td>
                        <td className="p-4 text-right">
                          <div className="flex items-center justify-end gap-3">
                            {riskBadge}
                            <ChevronRight className="w-4 h-4 text-border group-hover:text-primary transition-colors" />
                          </div>
                        </td>
                        <td className="p-4 relative">
                          <button
                            onClick={(e) => { e.stopPropagation(); setExportDropdownTx(exportDropdownTx === tx.id ? null : tx.id); }}
                            className="p-1.5 rounded-md hover:bg-surface text-content-muted hover:text-primary transition-colors"
                            title="Télécharger"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          {exportDropdownTx === tx.id && (
                            <div className="absolute right-4 top-12 z-30 bg-white border border-border rounded-lg shadow-lg py-1 min-w-[140px]">
                              <button
                                onClick={(e) => { e.stopPropagation(); exportTransaction(tx, 'pdf'); }}
                                className="w-full px-3 py-2 text-left text-sm hover:bg-surface flex items-center gap-2 text-content"
                              >
                                <FileText className="w-4 h-4 text-danger" /> Export PDF
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); exportTransaction(tx, 'csv'); }}
                                className="w-full px-3 py-2 text-left text-sm hover:bg-surface flex items-center gap-2 text-content"
                              >
                                <FileSpreadsheet className="w-4 h-4 text-success" /> Export CSV
                              </button>
                            </div>
                          )}
                        </td>
                        <td className="p-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (window.confirm('Supprimer cette transaction ?')) {
                                api.deleteTransaction(tx.id).then(() => {
                                  setUserTransactions(prev => prev.filter(t => t.id !== tx.id));
                                });
                              }
                            }}
                            className="p-1.5 rounded-md hover:bg-red-50 text-content-muted hover:text-red-600 transition-colors"
                            title="Supprimer"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            );
          })()}
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

        {/* Annotation Section */}
        {selectedTx?.dbId && !isLoading && result && (
          <div className="card bg-white p-6 mt-6">
            <h3 className="text-sm font-bold text-content-muted uppercase tracking-widest mb-4">Annotation de l'analyste</h3>
            <p className="text-sm text-content-muted mb-4">Confirmez le statut de cette transaction après votre investigation :</p>
            <div className="flex items-center gap-3 flex-wrap">
              <button
                onClick={() => {
                  updateAnnotation(selectedTx, 'valide');
                  setSelectedTx(prev => ({ ...prev, annotation: 'valide' }));
                }}
                className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 border transition-colors ${selectedTx.annotation === 'valide'
                    ? 'bg-success/10 border-success text-success'
                    : 'border-border text-content-muted hover:border-success hover:text-success'
                  }`}
              >
                <CheckCircle2 className="w-4 h-4" /> Transaction Valide
              </button>
              <button
                onClick={() => {
                  updateAnnotation(selectedTx, 'frauduleuse');
                  setSelectedTx(prev => ({ ...prev, annotation: 'frauduleuse' }));
                }}
                className={`px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 border transition-colors ${selectedTx.annotation === 'frauduleuse'
                    ? 'bg-danger/10 border-danger text-danger'
                    : 'border-border text-content-muted hover:border-danger hover:text-danger'
                  }`}
              >
                <XOctagon className="w-4 h-4" /> Fraude Confirmée
              </button>
              {selectedTx.annotation && (
                <button
                  onClick={() => {
                    updateAnnotation(selectedTx, null);
                    setSelectedTx(prev => ({ ...prev, annotation: null }));
                  }}
                  className="px-3 py-2 text-xs text-content-muted hover:text-content hover:underline"
                >
                  Retirer l'annotation
                </button>
              )}
            </div>
            {selectedTx.annotation && (
              <p className="mt-3 text-sm text-content">
                Statut actuel : <strong className={selectedTx.annotation === 'valide' ? 'text-success' : 'text-danger'}>
                  {selectedTx.annotation === 'valide' ? 'Validée par l\'analyste' : 'Fraude confirmée par l\'analyste'}
                </strong>
              </p>
            )}
          </div>
        )}
      </main>
    </div>
  );

  const batchView = (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => { setActivePage('dashboard'); setBatchResults(null); }}
              className="p-2 hover:bg-border/50 rounded-full transition-colors text-content-muted hover:text-content"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h2 className="text-lg font-bold text-content">Analyse en lot (CSV)</h2>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {batchLoading && (
          <div className="card bg-white p-12 text-center">
            <Loader2 className="w-10 h-10 text-primary animate-spin mx-auto mb-4" />
            <h3 className="text-xl font-serif text-content mb-2">Analyse du fichier en cours...</h3>
            <p className="text-content-muted text-sm">Chaque transaction est analysée individuellement par le modèle ML.</p>
          </div>
        )}

        {batchResults?.error && (
          <div className="card bg-white p-8 text-center">
            <AlertTriangle className="w-10 h-10 text-danger mx-auto mb-4" />
            <p className="text-danger font-bold mb-2">Erreur</p>
            <p className="text-content-muted text-sm">{batchResults.error}</p>
            <button onClick={() => { setActivePage('dashboard'); setBatchResults(null); }} className="mt-4 btn-primary text-sm">Retour</button>
          </div>
        )}

        {batchResults && !batchResults.error && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            {/* Summary KPIs */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="card bg-white p-4 text-center">
                <p className="text-3xl font-bold font-mono text-content">{batchResults.total}</p>
                <p className="text-xs font-bold text-content-muted uppercase tracking-widest mt-1">Transactions</p>
              </div>
              <div className="card bg-white p-4 text-center">
                <p className="text-3xl font-bold font-mono text-success">{batchResults.analyzed}</p>
                <p className="text-xs font-bold text-content-muted uppercase tracking-widest mt-1">Analysées</p>
              </div>
              <div className="card bg-white p-4 text-center">
                <p className="text-3xl font-bold font-mono text-danger">{batchResults.results.filter(r => r.is_fraud).length}</p>
                <p className="text-xs font-bold text-content-muted uppercase tracking-widest mt-1">Fraudes détectées</p>
              </div>
              <div className="card bg-white p-4 text-center">
                <p className="text-3xl font-bold font-mono text-content">{(batchResults.processing_time_ms / 1000).toFixed(1)}s</p>
                <p className="text-xs font-bold text-content-muted uppercase tracking-widest mt-1">Temps total</p>
              </div>
            </div>

            {/* Results table */}
            <div className="card bg-white overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-surface/50 text-xs font-bold text-content-muted uppercase tracking-widest">
                    <th className="p-4 font-medium">ID Transaction</th>
                    <th className="p-4 font-medium">Score</th>
                    <th className="p-4 font-medium">Risque</th>
                    <th className="p-4 font-medium">Décision</th>
                    <th className="p-4 font-medium">Modèle</th>
                    <th className="p-4 font-medium">Top Facteur</th>
                  </tr>
                </thead>
                <tbody>
                  {batchResults.results.map((r, i) => {
                    const riskBadge = r.risk_level === 'CRITIQUE' || r.risk_level === 'ELEVÉ'
                      ? <span className="badge badge-danger">{r.risk_level}</span>
                      : r.risk_level === 'MOYEN'
                        ? <span className="badge badge-warning">{r.risk_level}</span>
                        : r.risk_level === 'ERREUR'
                          ? <span className="badge badge-danger">ERREUR</span>
                          : <span className="badge badge-success">{r.risk_level}</span>;

                    const topFeat = r.top_features?.[0];
                    const featLabels = {
                      is_night: 'Nocturne', transaction_amount: 'Montant', merchant_category: 'Catégorie',
                      otp_used: 'OTP', kyc_verified: 'KYC', device_type: 'Appareil',
                      transaction_type: 'Type', hour: 'Heure',
                    };

                    return (
                      <tr key={i} className="border-b border-border hover:bg-surface/50 transition-colors">
                        <td className="p-4 font-mono text-sm font-medium text-content">{r.transaction_id}</td>
                        <td className="p-4 text-sm font-mono text-content tabular-nums">{(r.fraud_probability * 100).toFixed(1)}%</td>
                        <td className="p-4">{riskBadge}</td>
                        <td className="p-4">
                          {r.error ? (
                            <span className="text-xs text-danger">{r.error}</span>
                          ) : r.is_fraud ? (
                            <span className="text-xs font-bold text-danger flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Suspecte</span>
                          ) : (
                            <span className="text-xs font-bold text-success flex items-center gap-1"><ShieldCheck className="w-3 h-3" /> Valide</span>
                          )}
                        </td>
                        <td className="p-4 text-sm text-content-muted uppercase">{r.model_name}</td>
                        <td className="p-4 text-xs text-content-muted">
                          {topFeat ? `${featLabels[topFeat.feature] || topFeat.feature} (${topFeat.shap_value?.toFixed(2)})` : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => { setActivePage('dashboard'); setBatchResults(null); }}
                className="btn-primary text-sm"
              >
                Retour à l'historique
              </button>
              <button
                onClick={() => batchFileRef.current?.click()}
                className="flex items-center gap-2 text-sm px-4 py-2 border border-border rounded-lg font-medium text-content hover:bg-surface"
              >
                <Upload className="w-4 h-4" /> Charger un autre fichier
              </button>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );

  return (
    <div className="min-h-screen font-sans text-content selection:bg-primary/20">
      {activePage === 'landing' && landingView}
      {activePage === 'login' && <LoginPage onLogin={handleLogin} />}
      {activePage === 'dashboard' && dashboardView}
      {activePage === 'analytics' && (
        <AnalyticsPage
          user={user}
          health={health}
          onLogout={handleLogout}
          onNavigate={setActivePage}
          onNewAnalysis={() => setIsNewAnalysisModalOpen(true)}
        />
      )}
      {activePage === 'detail' && detailView}
      {activePage === 'batch' && batchView}

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
