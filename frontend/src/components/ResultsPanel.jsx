import React from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  AlertTriangle,
  Microscope,
  Loader2,
  BrainCircuit,
  ScanSearch,
} from 'lucide-react';

import Gauge from './Gauge';
import SHAPBarChart from './SHAPBarChart';
import AgentReport from './AgentReport';

const ResultsPanel = React.memo(({ result, isLoading, analysisType, elapsedTime, llmLoading, formData, llmProvider }) => {
  if (isLoading) {
    return (
      <div className="h-[650px] card bg-white flex flex-col items-center justify-center p-12 text-center">
        <div className="relative mb-8">
          <div className="w-24 h-24 rounded-2xl bg-surface flex items-center justify-center relative border border-border">
            {analysisType === 'full' ? (
              <BrainCircuit className="w-10 h-10 text-primary animate-pulse" />
            ) : (
              <ScanSearch className="w-10 h-10 text-primary animate-pulse" />
            )}
          </div>
        </div>

        <Loader2 className="w-6 h-6 text-primary animate-spin mb-6" />

        <h3 className="text-2xl font-serif text-content mb-2">
          {analysisType === 'full' ? 'Expertise IA en cours...' : 'Vérification en cours...'}
        </h3>
        <p className="text-content-muted max-w-sm mx-auto text-sm mb-4">
          {analysisType === 'full'
            ? 'Analyse prédictive et génération de rapport (15-30s)...'
            : 'Calcul du score de fraude...'}
        </p>
        <span className="text-primary font-mono font-bold text-lg">{elapsedTime}s</span>

        <div className="mt-8 w-full max-w-sm">
          <div className="flex justify-between text-[11px] font-bold text-content-muted uppercase tracking-widest mb-2">
            <span>Scan</span>
            <span>{analysisType === 'full' ? 'LLM' : 'Inférence'}</span>
            <span>Résultat</span>
          </div>
          <div className="h-1.5 w-full bg-surface rounded-full overflow-hidden border border-border">
            <div
              className="h-full bg-primary rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${Math.min(5 + elapsedTime * (analysisType === 'full' ? 2.5 : 15), 95)}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  if (result) {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} 
        className="space-y-6"
      >
        {/* Row 1: Score + Verdict */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-4 card bg-white p-6 flex flex-col items-center justify-center min-h-[280px]">
             <Gauge value={result.fraud_probability} isFraud={result.is_fraud} />
          </div>

          <div className="col-span-12 md:col-span-8 card bg-white p-8 flex flex-col justify-between">
            <div className="relative">
              <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest border mb-4 w-fit ${result.is_fraud ? 'bg-danger-light text-danger border-danger/20' : 'bg-success-light text-success border-success/20'}`}>
                {result.is_fraud ? <AlertTriangle className="w-3.5 h-3.5"/> : <ShieldCheck className="w-3.5 h-3.5"/>}
                {result.is_fraud ? 'Fraude Suspecte' : 'Transaction Valide'}
              </div>
              <h2 className="text-3xl font-serif text-content leading-tight mb-2">
                {result.is_fraud ? 'Alerte Critique' : 'Transaction Approuvée'}
              </h2>
              <p className="text-content-muted text-sm leading-relaxed max-w-lg">
                La transaction a été qualifiée de niveau de risque <strong className="text-content">{result.risk_level}</strong> avec un score prédictif de <strong className={result.is_fraud ? 'text-danger' : 'text-success'}>{(result.fraud_probability * 100).toFixed(1)}%</strong>.
              </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-8 pt-6 border-t border-border">
              <div>
                <p className="text-[11px] font-bold text-content-muted uppercase tracking-widest mb-1">Confiance</p>
                <p className="text-xl font-bold font-mono text-content">{(Math.abs(0.5 - result.fraud_probability) * 200).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-[11px] font-bold text-content-muted uppercase tracking-widest mb-1">Moteur ML</p>
                <p className="text-sm mt-1 font-bold text-primary uppercase">{(result.model_name || result.llm_model || 'N/A').split('_')[0]}</p>
              </div>
              <div>
                <p className="text-[11px] font-bold text-content-muted uppercase tracking-widest mb-1">Seuil Alerte</p>
                <p className="text-xl font-bold font-mono text-content">{((result.threshold_used || 0.37) * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-[11px] font-bold text-content-muted uppercase tracking-widest mb-1">Latence</p>
                <p className="text-xl font-bold font-mono text-content">{(result.processing_time_ms / 1000).toFixed(1)}s</p>
              </div>
            </div>
          </div>
        </div>

        {/* Row 2: SHAP + Agent Report */}
        {(result.top_features?.length > 0 || result.explanation || llmLoading) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {result.top_features?.length > 0 && (
          <div className="card bg-white p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-lg bg-surface border border-border flex items-center justify-center">
                <Microscope className="w-5 h-5 text-content" />
              </div>
              <div>
                <h3 className="text-lg font-serif text-content">Variables d'influence</h3>
                <p className="text-[11px] font-bold text-content-muted uppercase tracking-widest">Analyse SHAP</p>
              </div>
            </div>
            <SHAPBarChart features={result.top_features} />
          </div>
          )}
          {result.explanation ? (
          <div className={`card bg-white p-8 ${!result.top_features?.length ? 'lg:col-span-2' : ''}`}>
            <AgentReport report={result.explanation} llmProvider={llmProvider} />
          </div>
          ) : llmLoading ? (
          <div className="card bg-white p-8 flex flex-col items-center justify-center text-center min-h-[250px]">
            <div className="w-14 h-14 rounded-full bg-secondary-light flex items-center justify-center mb-4">
               <BrainCircuit className="w-6 h-6 text-secondary animate-pulse" />
            </div>
            <Loader2 className="w-5 h-5 text-secondary animate-spin mb-3" />
            <h4 className="font-medium text-content mb-1">Génération du rapport IA en cours...</h4>
            <p className="text-sm text-content-muted">Le LLM synthétise l'explicabilité du modèle</p>
          </div>
          ) : null}
        </div>
        )}

        {/* Row 3: Transaction Summary */}
        <TransactionSummary formData={formData} />
      </motion.div>
    );
  }

  return null;
});

ResultsPanel.displayName = 'ResultsPanel';

const TransactionSummary = React.memo(({ formData }) => (
  <div className="card bg-white p-6">
    <p className="text-[11px] font-bold text-content-muted uppercase tracking-widest mb-4">Détails de la transaction simulée</p>
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-y-6 gap-x-4">
      {[
        { label: 'ID', value: formData.transaction_id },
        { label: 'Montant', value: `${formData.transaction_amount} ${formData.currency}` },
        { label: 'Heure', value: `${String(formData.hour).padStart(2, '0')}:${String(formData.minute).padStart(2, '0')}` },
        { label: 'Type', value: formData.transaction_type },
        { label: 'Secteur', value: formData.merchant_category },
        { label: 'Ville', value: formData.city },
        { label: 'Pays', value: formData.country },
        { label: 'Format Base', value: formData.device_type },
        { label: 'Facteur 2FA', value: formData.otp_used ? '✅ Oui' : '❌ Non' },
        { label: 'Moyenne / 30j', value: formData.avg_amount_30d != null ? `${formData.avg_amount_30d} ${formData.currency || 'BDT'}` : 'N/A' },
      ].map((item, i) => (
        <div key={i} className="flex flex-col gap-1">
          <p className="text-[10px] font-bold text-content-muted uppercase tracking-widest">{item.label}</p>
          <p className="text-sm font-medium text-content truncate">{item.value}</p>
        </div>
      ))}
    </div>
  </div>
));

TransactionSummary.displayName = 'TransactionSummary';

export default ResultsPanel;
