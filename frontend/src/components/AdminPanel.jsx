import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../api/client';
import {
  ShieldCheck, AlertTriangle, Users, Activity, LogOut, CheckCircle2, MessageSquare, Star,
  Brain, Zap, RefreshCw, Clock, TrendingUp, Database, AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Composant Panneau HITL ─────────────────────────────────────────────────
function HitlPanel() {
  const [hitlStats, setHitlStats] = useState(null);
  const [hitlHistory, setHitlHistory] = useState([]);
  const [retraining, setRetraining] = useState(false);
  const [retrainResult, setRetrainResult] = useState(null);
  const [loadingStats, setLoadingStats] = useState(true);

  const loadHitlData = useCallback(async () => {
    setLoadingStats(true);
    try {
      const [stats, history] = await Promise.all([
        api.getHitlStatus(),
        api.getHitlHistory(),
      ]);
      setHitlStats(stats);
      setHitlHistory(history.reverse() || []);
    } catch (e) {
      console.warn('HITL data load failed', e);
    } finally {
      setLoadingStats(false);
    }
  }, []);

  useEffect(() => { loadHitlData(); }, [loadHitlData]);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainResult(null);
    try {
      const result = await api.triggerRetrain();
      setRetrainResult({ success: true, message: result.message, details: result.details });
      await loadHitlData();
    } catch (e) {
      const msg = e.response?.data?.detail || "Erreur inconnue lors du fine-tuning.";
      setRetrainResult({ success: false, message: msg });
    } finally {
      setRetraining(false);
    }
  };

  const pendingCount = hitlStats?.pending_feedback ?? 0;
  const canRetrain = hitlStats?.can_retrain ?? false;
  const minRequired = hitlStats?.min_feedback_required ?? 5;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between mb-2">
        <div>
          <h2 className="text-2xl font-serif text-content flex items-center gap-3">
            <Brain className="w-7 h-7 text-primary" /> IA Learning — Human-in-the-Loop
          </h2>
          <p className="text-content-muted text-sm mt-1">
            Chaque annotation des analystes améliore progressivement la précision du modèle de détection.
          </p>
        </div>
        <button onClick={loadHitlData} className="p-2 hover:bg-surface rounded-lg text-content-muted hover:text-content transition-colors" title="Actualiser">
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* KPI Cards */}
      {loadingStats ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
        </div>
      ) : hitlStats ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card bg-white p-5">
              <p className="text-[10px] uppercase font-bold text-content-muted tracking-widest mb-2 flex items-center gap-1">
                <Database className="w-3 h-3" /> Total Annotations
              </p>
              <p className="text-3xl font-mono font-bold text-content">{hitlStats.total_feedback}</p>
              <p className="text-xs text-content-muted mt-1">{hitlStats.fraud_confirmed} fraudes · {hitlStats.valid_confirmed} valides</p>
            </div>
            <div className={`card p-5 ${pendingCount >= minRequired ? 'bg-primary/5 border-primary/20' : 'bg-white'}`}>
              <p className="text-[10px] uppercase font-bold text-content-muted tracking-widest mb-2 flex items-center gap-1">
                <Clock className="w-3 h-3" /> En Attente
              </p>
              <p className={`text-3xl font-mono font-bold ${pendingCount >= minRequired ? 'text-primary' : 'text-content'}`}>
                {pendingCount}
              </p>
              <p className="text-xs text-content-muted mt-1">Seuil : {minRequired} pour déclencher</p>
            </div>
            <div className="card bg-white p-5">
              <p className="text-[10px] uppercase font-bold text-content-muted tracking-widest mb-2 flex items-center gap-1">
                <TrendingUp className="w-3 h-3" /> Cycles Effectués
              </p>
              <p className="text-3xl font-mono font-bold text-content">{hitlStats.retrain_count}</p>
              <p className="text-xs text-content-muted mt-1">{hitlStats.used_feedback} annotations intégrées</p>
            </div>
            <div className="card bg-white p-5">
              <p className="text-[10px] uppercase font-bold text-content-muted tracking-widest mb-2 flex items-center gap-1">
                <Activity className="w-3 h-3" /> Dernier Retrain
              </p>
              <p className="text-sm font-medium text-content">
                {hitlStats.last_retrain
                  ? new Date(hitlStats.last_retrain).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
                  : 'Jamais'}
              </p>
              <p className="text-xs text-content-muted mt-1">Warm-start XGBoost</p>
            </div>
          </div>

          {/* Barre de progression vers le prochain retrain */}
          <div className="card bg-white p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-content">Progression vers le prochain fine-tuning</h3>
                <p className="text-xs text-content-muted mt-0.5">
                  {pendingCount < minRequired
                    ? `Il manque ${minRequired - pendingCount} annotation(s) pour déclencher le retrain.`
                    : `${pendingCount} annotations prêtes — fine-tuning disponible !`}
                </p>
              </div>
              <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${canRetrain ? 'bg-success/10 text-success' : 'bg-surface text-content-muted'}`}>
                {pendingCount}/{minRequired}
              </span>
            </div>
            <div className="h-2 bg-surface rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${canRetrain ? 'bg-success' : 'bg-primary'}`}
                style={{ width: `${Math.min((pendingCount / minRequired) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Résultat du dernier retrain */}
          {retrainResult && (
            <motion.div
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }}
              className={`p-4 rounded-xl border flex items-start gap-3 ${
                retrainResult.success
                  ? 'bg-success/5 border-success/20 text-success'
                  : 'bg-danger/5 border-danger/20 text-danger'
              }`}
            >
              {retrainResult.success ? <CheckCircle2 className="w-5 h-5 mt-0.5 flex-shrink-0" /> : <AlertCircle className="w-5 h-5 mt-0.5 flex-shrink-0" />}
              <div>
                <p className="text-sm font-bold">{retrainResult.success ? 'Fine-tuning réussi !' : 'Échec du fine-tuning'}</p>
                <p className="text-xs opacity-80 mt-0.5">{retrainResult.message}</p>
                {retrainResult.success && retrainResult.details && (
                  <p className="text-xs opacity-70 mt-1">
                    {retrainResult.details.fraud_confirmed} fraudes + {retrainResult.details.valid_confirmed} valides intégrées
                    {retrainResult.details.reloaded_live && ' · Modèle rechargé à chaud ✓'}
                  </p>
                )}
              </div>
            </motion.div>
          )}

          {/* Bouton de déclenchement */}
          <button
            onClick={handleRetrain}
            disabled={!canRetrain || retraining}
            className={`w-full py-4 rounded-xl font-semibold text-sm flex items-center justify-center gap-3 transition-all ${
              canRetrain && !retraining
                ? 'bg-primary text-white hover:bg-primary/90 shadow-lg shadow-primary/25 hover:shadow-primary/40 hover:-translate-y-0.5'
                : 'bg-surface text-content-muted cursor-not-allowed'
            }`}
          >
            {retraining ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                Fine-tuning en cours... (peut prendre 30-60s)
              </>
            ) : (
              <>
                <Zap className="w-5 h-5" />
                Lancer le Fine-tuning Incrémental
                {pendingCount > 0 && <span className="bg-white/20 text-xs px-2 py-0.5 rounded-full">{pendingCount} exemples</span>}
              </>
            )}
          </button>

          {/* Explication du processus */}
          <div className="card bg-surface border border-border p-4 rounded-xl">
            <h4 className="text-xs font-bold text-content-muted uppercase tracking-widest mb-3 flex items-center gap-2">
              <Brain className="w-3.5 h-3.5" /> Comment fonctionne le HITL ?
            </h4>
            <div className="space-y-2">
              {[
                { step: '1', text: "Un analyste annote une transaction (\"Fraude Confirmée\" ou \"Transaction Valide\") dans l'interface." },
                { step: '2', text: "Les données de cette transaction sont automatiquement enregistrées comme exemple d'entraînement dans le système." },
                { step: '3', text: "Dès que 5 annotations sont disponibles, vous pouvez déclencher un fine-tuning du modèle XGBoost." },
                { step: '4', text: "XGBoost ajoute de nouveaux arbres de décision (warm-start) en apprenant des confirmations humaines, sans oublier l'entraînement initial." },
              ].map(({ step, text }) => (
                <div key={step} className="flex gap-3">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-primary/10 text-primary text-xs font-bold flex items-center justify-center">{step}</span>
                  <p className="text-xs text-content-muted leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Historique des cycles */}
          {hitlHistory.length > 0 && (
            <div className="card bg-white overflow-hidden">
              <div className="p-4 border-b border-border">
                <h3 className="text-sm font-bold text-content">Historique des cycles de fine-tuning</h3>
              </div>
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="bg-surface/50 text-[10px] font-bold text-content-muted uppercase tracking-widest">
                    <th className="p-3">Date</th>
                    <th className="p-3">Modèle</th>
                    <th className="p-3">Exemples</th>
                    <th className="p-3">Fraudes</th>
                    <th className="p-3">Valides</th>
                    <th className="p-3">Statut</th>
                  </tr>
                </thead>
                <tbody>
                  {hitlHistory.slice(0, 10).map((h, i) => (
                    <tr key={i} className="border-t border-border hover:bg-surface/30 transition-colors">
                      <td className="p-3 font-mono text-xs text-content-muted">
                        {new Date(h.timestamp).toLocaleString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="p-3 uppercase text-xs font-bold text-content">{h.model_name}</td>
                      <td className="p-3 font-mono">{h.feedback_count}</td>
                      <td className="p-3"><span className="text-danger font-medium">{h.fraud_confirmed}</span></td>
                      <td className="p-3"><span className="text-success font-medium">{h.valid_confirmed}</span></td>
                      <td className="p-3">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${h.reloaded_live ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'}`}>
                          {h.reloaded_live ? '✓ Live' : 'Redém. requis'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      ) : (
        <div className="card bg-white p-12 text-center">
          <AlertTriangle className="w-10 h-10 text-warning mx-auto mb-4" />
          <p className="text-content-muted text-sm">Impossible de charger les statistiques HITL.</p>
        </div>
      )}
    </div>
  );
}

// ── Composant Principal AdminPanel ─────────────────────────────────────────
export default function AdminPanel({ user, health, onLogout, onNavigate }) {
  const [analysts, setAnalysts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [selectedAnalyst, setSelectedAnalyst] = useState(null);
  const [activeTab, setActiveTab] = useState('team'); // 'team' | 'hitl'
  
  // Modal state
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadAnalysts = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const data = await api.getAnalysts();
      setAnalysts(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Failed to load analysts', e);
      setLoadError(e?.response?.data?.detail || e?.message || 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAnalysts(); }, []);

  const openModal = (analyst) => {
    setSelectedAnalyst(analyst);
    setRating(analyst.rating || 5);
    setComment(analyst.admin_comment || "");
  };

  const closeModal = () => {
    setSelectedAnalyst(null);
    setRating(5);
    setComment("");
  };

  const handleGradeSubmit = async () => {
    if (!selectedAnalyst) return;
    setSubmitting(true);
    try {
      await api.gradeAnalyst(selectedAnalyst.id, { rating, admin_comment: comment });
      await loadAnalysts();
      closeModal();
    } catch (e) {
      console.error('Failed to submit grade', e);
      alert("Erreur lors de l'enregistrement de la note.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => onNavigate('landing')}>
              <ShieldCheck className="w-6 h-6 text-primary" />
              <span className="font-bold text-lg">FraudIA</span>
            </div>
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-content-muted">
              <span onClick={() => onNavigate('dashboard')} className="hover:text-content transition-colors cursor-pointer">Supervision Globale</span>
              <span onClick={() => onNavigate('analytics')} className="hover:text-content transition-colors cursor-pointer">Analytiques</span>
              <span className="text-content pb-1 border-b-2 border-primary cursor-pointer flex items-center gap-2">
                <Users className="w-4 h-4"/> Équipe
              </span>
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 text-xs font-bold uppercase ${health?.status === 'healthy' ? 'text-success' : 'text-danger'}`}>
              <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-success' : 'bg-danger animate-pulse'}`}></div>
              {health?.status === 'healthy' ? 'API Active' : 'API Injoignable'}
            </div>
            {user && (
              <div className="flex items-center gap-3 ml-2 pl-4 border-l border-border">
                <div className="text-right hidden md:block">
                  <p className="text-xs font-bold text-primary">👑 {user.full_name}</p>
                  <p className="text-[10px] text-content-muted">{user.email}</p>
                </div>
                <button onClick={onLogout} className="p-2 hover:bg-danger-light rounded-lg transition-colors text-content-muted hover:text-danger" title="Déconnexion">
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Tab Navigation */}
        <div className="flex gap-1 p-1 bg-surface rounded-xl mb-8 w-fit border border-border">
          <button
            onClick={() => setActiveTab('team')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'team'
                ? 'bg-white text-primary shadow-sm border border-border'
                : 'text-content-muted hover:text-content'
            }`}
          >
            <Users className="w-4 h-4" /> Gestion de l'Équipe
          </button>
          <button
            onClick={() => setActiveTab('hitl')}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === 'hitl'
                ? 'bg-white text-primary shadow-sm border border-border'
                : 'text-content-muted hover:text-content'
            }`}
          >
            <Brain className="w-4 h-4" /> IA Learning
          </button>
        </div>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          {activeTab === 'team' ? (
            <motion.div key="team" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <div className="mb-6">
                <h1 className="text-3xl font-serif mb-2 text-content flex items-center gap-3">
                  <Users className="w-8 h-8 text-primary"/> Gestion de l'Équipe
                </h1>
                <p className="text-content-muted text-sm">Supervisez et évaluez les performances des analystes utilisant la plateforme.</p>
              </div>
              {loading ? (
                <div className="flex items-center justify-center py-20">
                  <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
                </div>
              ) : loadError ? (
                <div className="card bg-danger/5 border border-danger/20 p-8 text-center rounded-xl">
                  <AlertCircle className="w-10 h-10 text-danger mx-auto mb-3" />
                  <p className="text-sm font-bold text-danger mb-1">Impossible de charger les analystes</p>
                  <p className="text-xs text-content-muted mb-4">{loadError}</p>
                  <button onClick={loadAnalysts} className="btn-primary text-sm">Réessayer</button>
                </div>
              ) : analysts.length === 0 ? (
                <div className="card bg-white p-12 text-center rounded-xl">
                  <Users className="w-10 h-10 text-content-muted mx-auto mb-4" />
                  <p className="text-sm font-bold text-content mb-1">Aucun analyste trouvé</p>
                  <p className="text-xs text-content-muted">Aucun compte analyste n'est encore enregistré dans le système.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {analysts.map((analyst) => (
                    <div key={analyst.id} className="card bg-white p-6 relative flex flex-col justify-between">
                      <div>
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h3 className="text-lg font-bold text-content">{analyst.full_name}</h3>
                            <p className="text-xs text-content-muted">{analyst.email}</p>
                          </div>
                          {analyst.rating != null && (
                            <div className="flex items-center gap-1 bg-yellow-50 text-warning px-2 py-1 rounded-md text-xs font-bold border border-yellow-100">
                              <Star className="w-3.5 h-3.5 fill-warning"/>
                              {analyst.rating}/10
                            </div>
                          )}
                        </div>
                        <div className="grid grid-cols-2 gap-4 mb-6 pt-4 border-t border-border">
                          <div>
                            <p className="text-[10px] uppercase font-bold text-content-muted tracking-wide mb-1">Volume traité</p>
                            <p className="text-xl font-medium font-mono text-content">{analyst.tx_count}</p>
                          </div>
                          <div>
                            <p className="text-[10px] uppercase font-bold text-content-muted tracking-wide mb-1">Score moyen ciblé</p>
                            <p className="text-xl font-medium font-mono text-content">{analyst.avg_score != null ? (analyst.avg_score * 100).toFixed(1) + '%' : 'N/A'}</p>
                          </div>
                        </div>
                        {analyst.admin_comment && (
                          <div className="mb-6 bg-surface p-3 rounded-lg border border-border">
                            <p className="text-[10px] uppercase font-bold text-content-muted flex items-center gap-1 mb-1">
                              <MessageSquare className="w-3 h-3"/> Note de direction
                            </p>
                            <p className="text-xs text-content italic leading-relaxed line-clamp-3">"{analyst.admin_comment}"</p>
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => openModal(analyst)}
                        className="w-full py-2.5 rounded-lg border border-border hover:bg-surface text-sm font-medium transition-colors text-content flex items-center justify-center gap-2"
                      >
                        Évaluer ce profil
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div key="hitl" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <HitlPanel />
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Modal d'évaluation */}
      <AnimatePresence>
        {selectedAnalyst && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
              className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden border border-border flex flex-col"
            >
              <div className="p-6 border-b border-border bg-surface/50">
                <h2 className="text-xl font-serif text-content">Évaluation des performances</h2>
                <p className="text-sm text-content-muted mt-1">Analyste : <span className="font-bold text-content">{selectedAnalyst.full_name}</span></p>
              </div>
              <div className="p-6 space-y-6 flex-1 overflow-y-auto">
                <div>
                  <label className="block text-sm font-bold text-content mb-2 flex items-center justify-between">
                    <span>Score (sur 10)</span>
                    <span className="text-lg text-primary font-mono">{rating}</span>
                  </label>
                  <input
                    type="range" min="1" max="10" step="0.5" value={rating}
                    onChange={(e) => setRating(Number(e.target.value))}
                    className="w-full accent-primary"
                  />
                  <div className="flex justify-between text-xs text-content-muted mt-1 font-medium">
                    <span>1 (À revoir)</span>
                    <span>5 (Moyen)</span>
                    <span>10 (Excellent)</span>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-bold text-content mb-2">Commentaire de suivi</label>
                  <textarea
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Rédigez vos observations sur la qualité des analyses..."
                    className="w-full h-32 px-4 py-3 bg-surface border border-border rounded-xl text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary outline-none resize-none transition-all"
                  ></textarea>
                </div>
              </div>
              <div className="p-4 border-t border-border bg-surface/50 flex justify-end gap-3">
                <button onClick={closeModal} className="px-4 py-2 text-sm font-medium text-content-muted hover:text-content hover:bg-black/5 rounded-lg transition-colors">
                  Annuler
                </button>
                <button onClick={handleGradeSubmit} disabled={submitting} className="btn-primary flex items-center gap-2 text-sm">
                  {submitting ? 'Validation...' : <><CheckCircle2 className="w-4 h-4"/> Valider l'évaluation</>}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
