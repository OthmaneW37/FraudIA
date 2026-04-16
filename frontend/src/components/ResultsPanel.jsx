import React from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheck,
  AlertTriangle,
  Microscope,
  Zap,
  Loader2,
  BrainCircuit,
  ScanSearch,
} from 'lucide-react';

import Gauge from './Gauge';
import SHAPBarChart from './SHAPBarChart';
import AgentReport from './AgentReport';

const ResultsPanel = React.memo(({ result, isLoading, analysisType, elapsedTime, llmLoading, formData }) => {
  if (isLoading) {
    return (
      <div className="h-[650px] glass-card flex flex-col items-center justify-center p-12 text-center">
        <div className="relative mb-8">
          <div className="absolute inset-0 bg-primary/30 blur-3xl rounded-full scale-150 animate-pulse"></div>
          <div className="w-28 h-28 rounded-3xl bg-slate-800/80 flex items-center justify-center relative border border-primary/20">
            {analysisType === 'full' ? (
              <BrainCircuit className="w-12 h-12 text-primary animate-pulse" />
            ) : (
              <ScanSearch className="w-12 h-12 text-primary animate-pulse" />
            )}
          </div>
        </div>

        <Loader2 className="w-8 h-8 text-primary animate-spin mb-6" />

        <h3 className="text-2xl font-bold text-white mb-3">
          {analysisType === 'full' ? 'Expertise IA en cours...' : 'V\u00e9rification rapide...'}
        </h3>
        <p className="text-slate-500 max-w-sm mx-auto leading-relaxed text-sm mb-2">
          {analysisType === 'full'
            ? 'Analyse SHAP + g\u00e9n\u00e9ration du rapport LLM par LLaMA. Cela peut prendre 15 \u00e0 30 secondes.'
            : 'Calcul du score de fraude en cours...'}
        </p>
        <span className="text-primary font-mono text-lg font-bold">{elapsedTime}s</span>

        <div className="mt-8 w-full max-w-xs">
          <div className="flex justify-between text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">
            <span>Pr\u00e9traitement</span>
            <span>{analysisType === 'full' ? 'SHAP + LLM' : 'Inf\u00e9rence'}</span>
            <span>R\u00e9sultat</span>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary to-accent rounded-full transition-all duration-1000 ease-out"
              style={{ width: `${Math.min(5 + elapsedTime * (analysisType === 'full' ? 2.5 : 15), 95)}%` }}
            />
          </div>
        </div>
      </div>
    );
  }

  if (result) {
    return (
      <div className="space-y-6">
        {/* Row 1: Score + Verdict */}
        <div className="grid grid-cols-12 gap-6">
          <div className="col-span-12 md:col-span-5 glass-card p-6 flex flex-col items-center justify-center min-h-[300px]">
            <Gauge value={result.fraud_probability} isFraud={result.is_fraud} />
          </div>

          <div className="col-span-12 md:col-span-7 glass-card p-8 flex flex-col justify-between relative overflow-hidden">
            <div className={`absolute top-0 right-0 w-48 h-48 blur-[100px] -mr-24 -mt-24 ${result.is_fraud ? 'bg-danger/30' : 'bg-success/30'}`}></div>
            
            <div className="relative">
              <div className={`inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest border mb-5 w-fit ${result.is_fraud ? 'bg-danger/10 text-danger border-danger/20' : 'bg-success/10 text-success border-success/20'}`}>
                {result.is_fraud ? <AlertTriangle className="w-3.5 h-3.5"/> : <ShieldCheck className="w-3.5 h-3.5"/>}
                {result.is_fraud ? 'Fraude Suspecte' : 'Transaction Valide'}
              </div>
              <h2 className="text-4xl font-black text-white mb-3 tracking-tight">
                {result.is_fraud ? 'Alerte Critique' : 'Transaction Approuv\u00e9e'}
              </h2>
              <p className="text-slate-400 text-sm leading-relaxed max-w-lg">
                {'Cette transaction a \u00e9t\u00e9 class\u00e9e \u00e0 risque '}
                <strong className="text-white">{result.risk_level}</strong>
                {' avec un score de fraude de '}
                <strong className={result.is_fraud ? 'text-danger' : 'text-success'}>{(result.fraud_probability * 100).toFixed(1)}%</strong>.
              </p>
            </div>

            <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/5">
              <div>
                <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest mb-1">Confiance</p>
                <p className="text-2xl font-black text-white">{(Math.abs(0.5 - result.fraud_probability) * 200).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest mb-1">Moteur</p>
                <p className="text-lg font-bold text-primary uppercase">{(result.model_name || result.llm_model || 'N/A').split('_')[0]}</p>
              </div>
              <div>
                <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest mb-1">Seuil</p>
                <p className="text-lg font-bold text-white">{((result.threshold_used || 0.8) * 100).toFixed(0)}%</p>
              </div>
              <div>
                <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest mb-1">Latence</p>
                <p className="text-lg font-bold text-white">{(result.processing_time_ms / 1000).toFixed(1)}s</p>
              </div>
            </div>
          </div>
        </div>

        {/* Row 2: SHAP + Agent Report */}
        {(result.top_features?.length > 0 || result.explanation || llmLoading) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {result.top_features?.length > 0 && (
          <div className="glass-card p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center">
                <Microscope className="w-5 h-5 text-primary" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Variables Cl\u00e9s</h3>
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest">Analyse SHAP</p>
              </div>
            </div>
            <SHAPBarChart features={result.top_features} />
          </div>
          )}
          {result.explanation ? (
          <div className={`glass-card p-8 overflow-hidden border-accent/20 ${!result.top_features?.length ? 'md:col-span-2' : ''}`}>
            <AgentReport report={result.explanation} />
          </div>
          ) : llmLoading ? (
          <div className="glass-card p-8 flex flex-col items-center justify-center text-center min-h-[250px]">
            <div className="relative mb-4">
              <div className="absolute inset-0 bg-accent/20 blur-2xl rounded-full scale-150 animate-pulse"></div>
              <div className="w-16 h-16 rounded-2xl bg-slate-800/80 flex items-center justify-center relative border border-accent/20">
                <BrainCircuit className="w-8 h-8 text-accent animate-pulse" />
              </div>
            </div>
            <Loader2 className="w-6 h-6 text-accent animate-spin mb-3" />
            <h4 className="text-base font-bold text-white mb-1">G\u00e9n\u00e9ration du rapport IA...</h4>
            <p className="text-xs text-slate-500">Le mod\u00e8le LLM analyse les r\u00e9sultats SHAP</p>
          </div>
          ) : null}
        </div>
        )}

        {/* Row 3: Transaction Summary */}
        <TransactionSummary formData={formData} />
      </div>
    );
  }

  // Empty state
  return (
    <div className="h-[650px] glass-card flex flex-col items-center justify-center p-12 text-center border-dashed border-white/10">
      <div className="relative mb-8">
        <div className="absolute inset-0 bg-primary/20 blur-2xl rounded-full scale-150 animate-pulse"></div>
        <div className="w-24 h-24 rounded-3xl bg-slate-800 flex items-center justify-center relative">
          <Zap className="w-10 h-10 text-primary" />
        </div>
      </div>
      <h3 className="text-3xl font-bold text-white mb-4">Syst\u00e8me pr\u00eat pour l'analyse</h3>
      <p className="text-slate-500 max-w-md mx-auto leading-relaxed text-sm">
        Saisissez les param\u00e8tres de la transaction suspecte sur le panneau de gauche. Utilisez l'analyse compl\u00e8te (AI Explain) pour une expertise robotis\u00e9e d\u00e9taill\u00e9e.
      </p>
      <div className="mt-12 flex gap-8">
        <div className="flex flex-col items-center">
          <div className="w-2 h-2 rounded-full bg-success mb-2"></div>
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Inf\u00e9rence Active</span>
        </div>
        <div className="flex flex-col items-center">
          <div className="w-2 h-2 rounded-full bg-primary mb-2"></div>
          <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">LLaMA 3.2 Actif</span>
        </div>
      </div>
    </div>
  );
});

ResultsPanel.displayName = 'ResultsPanel';

const TransactionSummary = React.memo(({ formData }) => (
  <div className="glass-card p-6">
    <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">R\u00e9sum\u00e9 de la transaction</p>
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
      {[
        { label: 'ID', value: formData.transaction_id },
        { label: 'Montant', value: `${formData.transaction_amount} ${formData.currency}` },
        { label: 'Heure', value: `${String(formData.hour).padStart(2, '0')}:${String(formData.minute).padStart(2, '0')}` },
        { label: 'Type', value: formData.transaction_type },
        { label: 'Ville', value: formData.city },
        { label: 'Device', value: formData.device_type },
        { label: 'Secteur', value: formData.merchant_category },
        { label: 'OTP', value: formData.otp_used ? '\u2705 Utilis\u00e9' : '\u274c Non' },
        { label: 'Moy. 30j', value: `${formData.avg_amount_30d} MAD` },
        { label: 'Pays', value: formData.country },
      ].map((item, i) => (
        <div key={i} className="text-center py-2">
          <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest mb-1">{item.label}</p>
          <p className="text-sm font-semibold text-slate-300 truncate">{item.value}</p>
        </div>
      ))}
    </div>
  </div>
));

TransactionSummary.displayName = 'TransactionSummary';

export default ResultsPanel;
