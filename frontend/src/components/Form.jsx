import React, { useRef, useCallback, useState } from 'react';
import { Zap, BrainCircuit, Loader2, Target, ClipboardList, ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react';

const Form = React.memo(({ formData, setFormData, onSubmit, isLoading, onFullAnalysis }) => {
  const debounceRef = useRef({});
  const [isSecondaryOpen, setIsSecondaryOpen] = useState(false);

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    let val = type === 'checkbox' ? checked : value;

    if (type === 'number') {
      val = value === '' ? 0 : parseFloat(value);
      if (debounceRef.current[name]) clearTimeout(debounceRef.current[name]);
      debounceRef.current[name] = setTimeout(() => {
        setFormData(prev => ({ ...prev, [name]: val }));
      }, 300);
    } else {
      setFormData(prev => ({ ...prev, [name]: val }));
    }
  }, [setFormData]);

  const labelClasses = "block text-[10px] font-bold text-content-muted uppercase tracking-wider mb-1.5 ml-0.5";

  return (
    <div className="space-y-6">
      
      {/* ── SECTION 1 : VARIABLES PRIMORDIALES (Modèle) ─────────────────────── */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-2 p-2 bg-primary/5 rounded-lg border border-primary/10">
          <Target className="w-4 h-4 text-primary" />
          <h3 className="text-sm font-bold text-content uppercase tracking-tight">Variables Critiques (Prédiction)</h3>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClasses}>Montant (BDT)</label>
            <div className="relative">
              <input
                type="number"
                name="transaction_amount"
                defaultValue={formData.transaction_amount}
                onChange={handleChange}
                className="input-field pr-12 w-full tabular-nums"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-content-muted">BDT</span>
            </div>
          </div>

          <div>
            <label className={labelClasses}>Moyen de paiement</label>
            <select name="payment_method" value={formData.payment_method} onChange={handleChange} className="input-field w-full">
              <option value="bkash">bKash</option>
              <option value="nagad">Nagad</option>
              <option value="rocket">Rocket</option>
              <option value="upay">Upay</option>
              <option value="card">Carte Bancaire</option>
              <option value="bank">Virement Direct</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClasses}>Type de Transaction</label>
            <select name="transaction_type" value={formData.transaction_type} onChange={handleChange} className="input-field w-full">
              <option value="transfer">Transfert</option>
              <option value="payment">Paiement Marchand</option>
              <option value="withdrawal">Retrait (Cash Out)</option>
              <option value="deposit">Dépôt (Cash In)</option>
              <option value="purchase">Achat en ligne</option>
            </select>
          </div>
          <div>
            <label className={labelClasses}>Secteur Marchand</label>
            <select name="merchant_category" value={formData.merchant_category} onChange={handleChange} className="input-field w-full">
              <option value="electronics">Électronique</option>
              <option value="fashion">Mode / Vêtements</option>
              <option value="grocery">Épicerie / Food</option>
              <option value="travel">Voyage / Transport</option>
              <option value="entertainment">Divertissement</option>
              <option value="crypto">Cryptodevises</option>
              <option value="services">Services / Factures</option>
            </select>
          </div>
        </div>

        {/* Vélocité & Ancienneté (Sequential Features) */}
        <div className="p-3 rounded-xl bg-surface border border-border space-y-3">
          <p className="text-[10px] font-bold text-content-muted uppercase tracking-widest flex items-center gap-2">
            <Zap className="w-3 h-3 text-warning" /> Vélocité & Historique
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClasses}>Nb Txn (24h)</label>
              <input type="number" name="txn_count_24h" defaultValue={formData.txn_count_24h} onChange={handleChange} className="input-field w-full h-9 text-xs" />
            </div>
            <div>
              <label className={labelClasses}>Somme (24h)</label>
              <input type="number" name="txn_sum_24h" defaultValue={formData.txn_sum_24h} onChange={handleChange} className="input-field w-full h-9 text-xs" />
            </div>
            <div>
              <label className={labelClasses}>Ancienneté (Jours)</label>
              <input type="number" name="user_account_age_days" defaultValue={formData.user_account_age_days} onChange={handleChange} className="input-field w-full h-9 text-xs" />
            </div>
            <div>
              <label className={labelClasses}>Dernière Tx (Min)</label>
              <input type="number" name="time_since_last_txn" defaultValue={formData.time_since_last_txn} onChange={handleChange} className="input-field w-full h-9 text-xs" />
            </div>
          </div>
        </div>


        <div className="flex items-center gap-6 p-1">
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className="relative">
              <input type="checkbox" name="kyc_verified" checked={formData.kyc_verified} onChange={handleChange} className="sr-only peer" />
              <div className="w-9 h-5 bg-surface border border-border rounded-full peer peer-checked:bg-success transition-colors"></div>
              <div className="absolute left-1 top-1 w-3 h-3 bg-white shadow-sm rounded-full transition-transform peer-checked:translate-x-4"></div>
            </div>
            <span className="text-xs font-bold text-content group-hover:text-success transition-colors">Client KYC</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className="relative">
              <input type="checkbox" name="otp_used" checked={formData.otp_used} onChange={handleChange} className="sr-only peer" />
              <div className="w-9 h-5 bg-surface border border-border rounded-full peer peer-checked:bg-primary transition-colors"></div>
              <div className="absolute left-1 top-1 w-3 h-3 bg-white shadow-sm rounded-full transition-transform peer-checked:translate-x-4"></div>
            </div>
            <span className="text-xs font-bold text-content group-hover:text-primary transition-colors">OTP Utilisé</span>
          </label>
        </div>
      </div>

      {/* ── SECTION 2 : VARIABLES SECONDAIRES ───────────────────────────────── */}
      <div className="border border-border rounded-xl flex flex-col overflow-hidden">
        <button 
          onClick={() => setIsSecondaryOpen(!isSecondaryOpen)}
          className="w-full flex items-center justify-between p-4 bg-surface hover:bg-surface/80 transition-colors"
        >
          <div className="flex items-center gap-2">
            <ClipboardList className="w-4 h-4 text-content-muted" />
            <span className="text-xs font-bold text-content-muted uppercase tracking-widest">Détails & Métadonnées (Secondaires)</span>
          </div>
          {isSecondaryOpen ? <ChevronUp className="w-4 h-4 text-content-muted" /> : <ChevronDown className="w-4 h-4 text-content-muted" />}
        </button>

        {isSecondaryOpen && (
          <div className="p-4 space-y-4 bg-white border-t border-border">
            <div>
              <label className={labelClasses}>ID Transaction</label>
              <input name="transaction_id" value={formData.transaction_id} onChange={handleChange} className="input-field w-full font-mono text-xs" />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClasses}>Ville</label>
                <select name="city" value={formData.city} onChange={handleChange} className="input-field w-full">
                  <option value="Casablanca">Casablanca</option>
                  <option value="Rabat">Rabat</option>
                  <option value="Marrakech">Marrakech</option>
                  <option value="Fès">Fès</option>
                  <option value="Tanger">Tanger</option>
                  <option value="Agadir">Agadir</option>
                  <option value="Autre">Autre</option>
                </select>
              </div>
              <div>
                <label className={labelClasses}>Heure locale</label>
                <select name="hour" value={formData.hour} onChange={handleChange} className="input-field w-full tabular-nums">
                  {[...Array(24)].map((_, i) => (
                    <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClasses}>Type Appareil</label>
                <select name="device_type" value={formData.device_type} onChange={handleChange} className="input-field w-full">
                  <option value="Mobile App">Mobile App</option>
                  <option value="Desktop Web">Desktop Web</option>
                  <option value="Tablet">Tablette</option>
                  <option value="API">API / Bot</option>
                  <option value="POS">Terminal POS</option>
                  <option value="ATM">Distributeur ATM</option>
                </select>
              </div>
              <div>
                <label className={labelClasses}>Type de carte</label>
                <select name="card_type" value={formData.card_type} onChange={handleChange} className="input-field w-full">
                  <option value="debit">Débit</option>
                  <option value="credit">Crédit</option>
                  <option value="prepaid">Prépayée</option>
                </select>
              </div>
            </div>

            <div className="mt-2 text-[10px] text-content-muted bg-surface p-2 rounded italic">
              * Ces informations servent au contexte mais ont un impact minimal sur le score de fraude pur.
            </div>
          </div>
        )}
      </div>

      {/* ── MOTEURS ───────────────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div>
          <label className={labelClasses}>Modèle Prédictif</label>
          <select name="selected_model" value={formData.selected_model} onChange={handleChange} className="input-field w-full border-primary/20 bg-primary/5">
            <option value="xgboost">XGBoost (Champion v2.0)</option>
            <option value="random_forest">Random Forest (Baseline)</option>
            <option value="logistic_regression">Logistic Regression (Interprétable)</option>
          </select>
        </div>
      </div>

      {/* Boutons d'Action */}
      <div className="pt-4 space-y-3">
        <button
          onClick={onSubmit}
          disabled={isLoading}
          className="w-full h-12 flex items-center justify-center gap-2 rounded-lg font-bold text-sm border border-border bg-white text-content hover:bg-surface transition-colors disabled:opacity-50"
        >
          {isLoading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /><span>Analyse...</span></>
          ) : (
            <><Zap className="w-4 h-4" /><span>Vérification Rapide</span></>
          )}
        </button>

        <button
          onClick={onFullAnalysis}
          disabled={isLoading}
          className="btn-primary w-full h-12 flex items-center justify-center gap-2 shadow-soft disabled:opacity-50"
        >
          {isLoading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /><span>Expertise en cours...</span></>
          ) : (
            <><BrainCircuit className="w-5 h-5" /><span>Analyse Experte IA</span></>
          )}
        </button>
      </div>
    </div>
  );
});

Form.displayName = 'Form';
export default Form;

