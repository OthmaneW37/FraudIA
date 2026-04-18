import React, { useCallback, useRef, useState } from 'react';
import {
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  ClipboardList,
  Loader2,
  ShieldCheck,
  Target,
  Zap,
} from 'lucide-react';

const buildTransactionId = () => `TX_${Math.random().toString(36).slice(2, 11).toUpperCase()}`;

const FRAUD_PRESET = {
  transaction_amount: 32.25,
  transaction_type: 'purchase',
  merchant_category: 'travel',
  payment_method: 'nagad',
  card_type: 'credit',
  kyc_verified: true,
  otp_used: true,
  user_account_age_days: 393,
  txn_count_24h: 1,
  txn_sum_24h: 32.25,
  time_since_last_txn: 5109.67,
  is_new_city: 0,
  avg_amount_30d: 18,
  city: 'Khulna',
  country: 'Bangladesh',
  currency: 'BDT',
  device_type: 'tablet',
  hour: 5,
  selected_model: 'xgboost',
};

const Form = React.memo(({ formData, setFormData, onSubmit, isLoading, onFullAnalysis }) => {
  const debounceRef = useRef({});
  const [isSecondaryOpen, setIsSecondaryOpen] = useState(false);

  const handleChange = useCallback((event) => {
    const { name, value, type, checked } = event.target;
    let nextValue = type === 'checkbox' ? checked : value;

    if (type === 'number') {
      nextValue = value === '' ? 0 : parseFloat(value);
      if (debounceRef.current[name]) {
        clearTimeout(debounceRef.current[name]);
      }
      debounceRef.current[name] = setTimeout(() => {
        setFormData((prev) => ({ ...prev, [name]: nextValue }));
      }, 300);
      return;
    }

    setFormData((prev) => ({ ...prev, [name]: nextValue }));
  }, [setFormData]);

  const loadFraudPreset = useCallback(() => {
    setFormData((prev) => ({
      ...prev,
      ...FRAUD_PRESET,
      transaction_id: buildTransactionId(),
    }));
    setIsSecondaryOpen(true);
  }, [setFormData]);

  const labelClasses =
    'block text-[10px] font-bold text-content-muted uppercase tracking-wider mb-1.5 ml-0.5';

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-danger/20 bg-danger-light/40 p-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-danger">Test rapide</p>
            <p className="text-xs text-content-muted">
              Charge un cas frauduleux reellement compatible avec le dataset pour verifier le score et l’email.
            </p>
          </div>
          <button
            type="button"
            onClick={loadFraudPreset}
            className="inline-flex items-center gap-2 rounded-lg border border-danger/20 bg-white px-3 py-2 text-xs font-bold text-danger hover:bg-danger-light/60"
          >
            <ShieldCheck className="h-4 w-4" />
            Charger un cas frauduleux
          </button>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2 rounded-lg border border-primary/10 bg-primary/5 p-2">
          <Target className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-bold uppercase tracking-tight text-content">
            Variables critiques
          </h3>
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
                className="input-field w-full pr-12 tabular-nums"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-content-muted">
                BDT
              </span>
            </div>
          </div>

          <div>
            <label className={labelClasses}>Moyen de paiement</label>
            <select
              name="payment_method"
              value={formData.payment_method}
              onChange={handleChange}
              className="input-field w-full"
            >
              <option value="bkash">bKash</option>
              <option value="nagad">Nagad</option>
              <option value="card">Carte bancaire</option>
              <option value="bank">Virement direct</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClasses}>Type de transaction</label>
            <select
              name="transaction_type"
              value={formData.transaction_type}
              onChange={handleChange}
              className="input-field w-full"
            >
              <option value="purchase">Achat en ligne</option>
              <option value="transfer">Transfert</option>
              <option value="withdrawal">Retrait</option>
            </select>
          </div>
          <div>
            <label className={labelClasses}>Secteur marchand</label>
            <select
              name="merchant_category"
              value={formData.merchant_category}
              onChange={handleChange}
              className="input-field w-full"
            >
              <option value="electronics">Electronique</option>
              <option value="fashion">Mode</option>
              <option value="grocery">Epicerie</option>
              <option value="travel">Voyage</option>
            </select>
          </div>
        </div>

        <div className="space-y-3 rounded-xl border border-border bg-surface p-3">
          <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-content-muted">
            <Zap className="h-3 w-3 text-warning" />
            Velocite & historique
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={labelClasses}>Nb Txn (24h)</label>
              <input
                type="number"
                name="txn_count_24h"
                defaultValue={formData.txn_count_24h}
                onChange={handleChange}
                className="input-field h-9 w-full text-xs"
              />
            </div>
            <div>
              <label className={labelClasses}>Somme (24h)</label>
              <input
                type="number"
                name="txn_sum_24h"
                defaultValue={formData.txn_sum_24h}
                onChange={handleChange}
                className="input-field h-9 w-full text-xs"
              />
            </div>
            <div>
              <label className={labelClasses}>Anciennete (jours)</label>
              <input
                type="number"
                name="user_account_age_days"
                defaultValue={formData.user_account_age_days}
                onChange={handleChange}
                className="input-field h-9 w-full text-xs"
              />
            </div>
            <div>
              <label className={labelClasses}>Derniere Tx (min)</label>
              <input
                type="number"
                name="time_since_last_txn"
                defaultValue={formData.time_since_last_txn}
                onChange={handleChange}
                className="input-field h-9 w-full text-xs"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-6 p-1">
          <label className="group flex cursor-pointer items-center gap-3">
            <div className="relative">
              <input
                type="checkbox"
                name="kyc_verified"
                checked={formData.kyc_verified}
                onChange={handleChange}
                className="peer sr-only"
              />
              <div className="h-5 w-9 rounded-full border border-border bg-surface transition-colors peer-checked:bg-success" />
              <div className="absolute left-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4" />
            </div>
            <span className="text-xs font-bold text-content transition-colors group-hover:text-success">
              Client KYC
            </span>
          </label>
          <label className="group flex cursor-pointer items-center gap-3">
            <div className="relative">
              <input
                type="checkbox"
                name="otp_used"
                checked={formData.otp_used}
                onChange={handleChange}
                className="peer sr-only"
              />
              <div className="h-5 w-9 rounded-full border border-border bg-surface transition-colors peer-checked:bg-primary" />
              <div className="absolute left-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4" />
            </div>
            <span className="text-xs font-bold text-content transition-colors group-hover:text-primary">
              OTP utilise
            </span>
          </label>
        </div>
      </div>

      <div className="flex flex-col overflow-hidden rounded-xl border border-border">
        <button
          type="button"
          onClick={() => setIsSecondaryOpen((prev) => !prev)}
          className="flex w-full items-center justify-between bg-surface p-4 transition-colors hover:bg-surface/80"
        >
          <div className="flex items-center gap-2">
            <ClipboardList className="h-4 w-4 text-content-muted" />
            <span className="text-xs font-bold uppercase tracking-widest text-content-muted">
              Details compatibles dataset
            </span>
          </div>
          {isSecondaryOpen ? (
            <ChevronUp className="h-4 w-4 text-content-muted" />
          ) : (
            <ChevronDown className="h-4 w-4 text-content-muted" />
          )}
        </button>

        {isSecondaryOpen && (
          <div className="space-y-4 border-t border-border bg-white p-4">
            <div>
              <label className={labelClasses}>ID transaction</label>
              <input
                name="transaction_id"
                value={formData.transaction_id}
                onChange={handleChange}
                className="input-field w-full font-mono text-xs"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClasses}>Ville</label>
                <select name="city" value={formData.city} onChange={handleChange} className="input-field w-full">
                  <option value="Dhaka">Dhaka</option>
                  <option value="Chittagong">Chittagong</option>
                  <option value="Khulna">Khulna</option>
                  <option value="Rajshahi">Rajshahi</option>
                </select>
              </div>
              <div>
                <label className={labelClasses}>Heure locale</label>
                <select
                  name="hour"
                  value={formData.hour}
                  onChange={handleChange}
                  className="input-field w-full tabular-nums"
                >
                  {[...Array(24)].map((_, hour) => (
                    <option key={hour} value={hour}>
                      {hour.toString().padStart(2, '0')}:00
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelClasses}>Type appareil</label>
                <select
                  name="device_type"
                  value={formData.device_type}
                  onChange={handleChange}
                  className="input-field w-full"
                >
                  <option value="mobile">Mobile</option>
                  <option value="desktop">Desktop</option>
                  <option value="tablet">Tablet</option>
                </select>
              </div>
              <div>
                <label className={labelClasses}>Type de carte</label>
                <select
                  name="card_type"
                  value={formData.card_type}
                  onChange={handleChange}
                  className="input-field w-full"
                >
                  <option value="debit">Debit</option>
                  <option value="credit">Credit</option>
                </select>
              </div>
            </div>

            <div className="rounded bg-surface p-2 text-[10px] italic text-content-muted">
              Ces valeurs sont volontairement limitees aux categories connues du dataset afin de garder des scores coherents.
            </div>
          </div>
        )}
      </div>

      <div className="space-y-3">
        <div>
          <label className={labelClasses}>Modele predictif</label>
          <select
            name="selected_model"
            value={formData.selected_model}
            onChange={handleChange}
            className="input-field w-full border-primary/20 bg-primary/5"
          >
            <option value="xgboost">XGBoost (Champion)</option>
            <option value="random_forest">Random Forest</option>
            <option value="logistic_regression">Logistic Regression</option>
          </select>
        </div>
      </div>

      <div className="space-y-3 pt-4">
        <button
          onClick={onSubmit}
          disabled={isLoading}
          className="h-12 w-full rounded-lg border border-border bg-white text-sm font-bold text-content transition-colors hover:bg-surface disabled:opacity-50"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              Analyse...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <Zap className="h-4 w-4" />
              Verification rapide
            </span>
          )}
        </button>

        <button
          onClick={onFullAnalysis}
          disabled={isLoading}
          className="btn-primary h-12 w-full justify-center gap-2 shadow-soft disabled:opacity-50"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Expertise en cours...
            </span>
          ) : (
            <span className="flex items-center justify-center gap-2">
              <BrainCircuit className="h-5 w-5" />
              Analyse experte IA
            </span>
          )}
        </button>
      </div>
    </div>
  );
});

Form.displayName = 'Form';
export default Form;
