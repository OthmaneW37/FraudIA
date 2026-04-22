import React, { useCallback, useRef } from "react";
import { BrainCircuit, Loader2, ShieldAlert, ShieldCheck, Target, Zap } from "lucide-react";

const buildTxId = () => "TX_" + Math.random().toString(36).slice(2, 11).toUpperCase();

<<<<<<< HEAD
const LEGIT_PRESET = {
  transaction_amount: 850, transaction_type: "purchase", payment_method: "bkash",
  kyc_verified: true, otp_used: true, is_new_city: 0, hour: 11,
  txn_count_24h: 2, txn_sum_24h: 1500, time_since_last_txn: 480,
  merchant_category: "grocery", card_type: "debit", day_of_week: 2,
  city: "Dhaka", country: "Bangladesh", currency: "BDT",
  device_type: "mobile", operating_system: "Android", browser: "Chrome",
  selected_model: "xgboost",
=======
const FRAUD_PRESET = {
  transaction_amount: 10000,
  transaction_type: 'purchase',
  merchant_category: 'travel',
  payment_method: 'Orange Money',
  card_type: 'credit',
  kyc_verified: true,
  otp_used: false,
  user_account_age_days: 12,
  txn_count_24h: 5,
  txn_sum_24h: 15000,
  time_since_last_txn: 5,
  is_new_city: 1,
  avg_amount_30d: 500,
  city: 'Casablanca',
  country: 'Maroc',
  currency: 'MAD',
  device_type: 'mobile',
  hour: 5,
  selected_model: 'xgboost',
>>>>>>> 2c965fa (Correction bugs + Ajout fonctionnalités)
};

const FRAUD_PRESET = {
  transaction_amount: 50000, transaction_type: "transfer", payment_method: "bkash",
  kyc_verified: false, otp_used: false, is_new_city: 1, hour: 2,
  txn_count_24h: 15, txn_sum_24h: 200000, time_since_last_txn: 2,
  merchant_category: "electronics", card_type: "credit", day_of_week: 0,
  city: "Dhaka", country: "Bangladesh", currency: "BDT",
  device_type: "desktop", operating_system: "Windows", browser: "Chrome",
  selected_model: "xgboost",
};

const SH = ({ icon: Icon, label, ic = "text-primary", bg = "bg-primary/5", bd = "border-primary/10" }) => (
  <div className={`flex items-center gap-2 rounded-lg border ${bd} ${bg} p-2`}>
    <Icon className={`h-4 w-4 ${ic}`} />
    <h3 className="text-sm font-bold uppercase tracking-tight text-content">{label}</h3>
  </div>
);

const Toggle = ({ name, checked, onChange, ac, label, hint }) => (
  <label className="flex cursor-pointer items-start gap-3">
    <div className="relative mt-0.5 shrink-0">
      <input type="checkbox" name={name} checked={checked} onChange={onChange} className="peer sr-only" />
      <div className={"h-5 w-9 rounded-full border border-border bg-surface transition-colors " + ac} />
      <div className="absolute left-1 top-1 h-3 w-3 rounded-full bg-white shadow-sm transition-transform peer-checked:translate-x-4" />
    </div>
    <div>
      <p className="text-xs font-bold text-content">{label}</p>
      <p className="text-[10px] leading-relaxed text-content-muted">{hint}</p>
    </div>
  </label>
);

const TIME_OPTS = [
  { label: "< 5 min", value: 3, danger: true },
  { label: "< 30 min", value: 20, danger: false },
  { label: "< 3 h", value: 120, danger: false },
  { label: "> 6 h", value: 480, danger: false },
];

const Form = React.memo(({ formData, setFormData, onSubmit, isLoading, onFullAnalysis }) => {
  const db = useRef({});

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    let v = type === "checkbox" ? checked : value;
    if (type === "number") {
      v = value === "" ? 0 : parseFloat(value);
      clearTimeout(db.current[name]);
      db.current[name] = setTimeout(() => setFormData((p) => ({ ...p, [name]: v })), 280);
      return;
    }
    setFormData((p) => ({ ...p, [name]: v }));
  }, [setFormData]);

  const loadPreset = useCallback((preset) => {
    setFormData((p) => ({ ...p, ...preset, transaction_id: buildTxId() }));
  }, [setFormData]);

  const L = "block text-[10px] font-bold text-content-muted uppercase tracking-wider mb-1.5 ml-0.5";

  return (
    <div className="space-y-5">

<<<<<<< HEAD
      <div className="grid grid-cols-2 gap-2">
        <button type="button" onClick={() => loadPreset(LEGIT_PRESET)}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-success/30 bg-success/5 py-2.5 text-xs font-bold text-success hover:bg-success/10 transition-colors">
          <ShieldCheck className="h-3.5 w-3.5" /> Transaction legitime
        </button>
        <button type="button" onClick={() => loadPreset(FRAUD_PRESET)}
          className="flex items-center justify-center gap-1.5 rounded-lg border border-danger/30 bg-danger-light/40 py-2.5 text-xs font-bold text-danger hover:bg-danger-light/60 transition-colors">
          <ShieldAlert className="h-3.5 w-3.5" /> Fraude suspectee
        </button>
=======
      <div className="space-y-4">
        <div className="flex items-center gap-2 rounded-lg border border-primary/10 bg-primary/5 p-2">
          <Target className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-bold uppercase tracking-tight text-content">
            Variables critiques
          </h3>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClasses}>Montant (MAD)</label>
            <div className="relative">
              <input
                type="number"
                name="transaction_amount"
                defaultValue={formData.transaction_amount}
                onChange={handleChange}
                className="input-field w-full pr-12 tabular-nums"
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-content-muted">
                MAD
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
              <option value="Orange Money">Orange / inwi Money</option>
              <option value="Wafacash">Wafacash</option>
              <option value="Carte bancaire">Carte bancaire</option>
              <option value="Virement bancaire">Virement bancaire</option>
              <option value="Espèces">Espèces</option>
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
                  <option value="Casablanca">Casablanca</option>
                  <option value="Rabat">Rabat</option>
                  <option value="Marrakech">Marrakech</option>
                  <option value="Fès">Fès</option>
                  <option value="Tanger">Tanger</option>
                  <option value="Agadir">Agadir</option>
                  <option value="Meknès">Meknès</option>
                  <option value="Oujda">Oujda</option>
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
>>>>>>> 2c965fa (Correction bugs + Ajout fonctionnalités)
      </div>

      <div className="space-y-3">
        <SH icon={Target} label="Details de la transaction" />
        <div>
          <label className={L}>Montant (MAD)</label>
          <div className="relative">
            <input type="number" name="transaction_amount" defaultValue={formData.transaction_amount}
              onChange={handleChange} min="1"
              className="input-field w-full pr-14 text-sm font-bold tabular-nums" />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-bold text-content-muted">MAD</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={L}>Nature</label>
            <select name="transaction_type" value={formData.transaction_type} onChange={handleChange} className="input-field w-full">
              <option value="purchase">Paiement marchand</option>
              <option value="transfer">Virement / Transfert</option>
              <option value="withdrawal">Retrait especes</option>
            </select>
          </div>
          <div>
            <label className={L}>Heure</label>
            <select name="hour" value={formData.hour} onChange={handleChange} className="input-field w-full tabular-nums">
              {[...Array(24)].map((_, h) => (
                <option key={h} value={h}>
                  {h.toString().padStart(2, "0")}h {h < 6 || h >= 22 ? "— Nuit 🌙" : h < 9 ? "— Matin 🌅" : h >= 20 ? "— Soir" : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <label className={L}>Canal de paiement</label>
          <select name="payment_method" value={formData.payment_method} onChange={handleChange} className="input-field w-full">
            <option value="bkash">Orange Money / Inwi Money</option>
            <option value="nagad">Maroc Telecom Money / Wave</option>
            <option value="card">Carte bancaire (Visa / Mastercard)</option>
            <option value="bank">Virement bancaire CIH / Attijari / CPA</option>
          </select>
        </div>
      </div>

      <div className="space-y-3">
        <SH icon={ShieldAlert} label="Securite et conformite" ic="text-warning" bg="bg-warning/5" bd="border-warning/10" />
        <div className="space-y-4 rounded-xl border border-border bg-surface px-4 py-3.5">
          <Toggle name="kyc_verified" checked={formData.kyc_verified} onChange={handleChange}
            ac="peer-checked:bg-success"
            label="KYC valide" hint="Piece d'identite et adresse verifiees par la banque" />
          <div className="border-t border-border/40" />
          <Toggle name="otp_used" checked={formData.otp_used} onChange={handleChange}
            ac="peer-checked:bg-primary"
            label="Authentification OTP / 2FA" hint="Code SMS ou appli d'authentification utilise" />
          <div className="border-t border-border/40" />
          <Toggle name="is_new_city" checked={formData.is_new_city === 1}
            onChange={(e) => setFormData((p) => ({ ...p, is_new_city: e.target.checked ? 1 : 0 }))}
            ac="peer-checked:bg-danger"
            label="Zone geographique inhabituelle" hint="Transaction depuis une ville ou region jamais vue" />
        </div>
      </div>

      <div className="space-y-3">
        <SH icon={Zap} label="Activite recente du compte" ic="text-warning" bg="bg-warning/5" bd="border-warning/10" />
        <p className="rounded-lg border border-border/60 bg-surface px-3 py-2 text-[10px] text-content-muted">
          Historique des <strong>24 dernieres heures</strong> — cles pour detecter une velocite anormale.
        </p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={L}>Nb d'operations (24h)</label>
            <input type="number" name="txn_count_24h" defaultValue={formData.txn_count_24h}
              onChange={handleChange} min="0"
              className="input-field h-9 w-full tabular-nums text-xs" />
            <p className="mt-0.5 ml-0.5 text-[9px] text-content-muted">combien de paiements recents ?</p>
          </div>
          <div>
            <label className={L}>Total cumule (24h)</label>
            <div className="relative">
              <input type="number" name="txn_sum_24h" defaultValue={formData.txn_sum_24h}
                onChange={handleChange} min="0"
                className="input-field h-9 w-full tabular-nums text-xs pr-12" />
              <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[9px] font-bold text-content-muted">MAD</span>
            </div>
            <p className="mt-0.5 ml-0.5 text-[9px] text-content-muted">total depense depuis minuit</p>
          </div>
        </div>
        <div>
          <label className={L}>Intervalle depuis la derniere operation</label>
          <div className="grid grid-cols-4 gap-1.5 mt-1">
            {TIME_OPTS.map((opt) => {
              const active = formData.time_since_last_txn === opt.value;
              return (
                <button key={opt.value} type="button"
                  onClick={() => setFormData((p) => ({ ...p, time_since_last_txn: opt.value }))}
                  className={[
                    "rounded-lg border py-2 text-[10px] font-bold transition-colors",
                    active
                      ? opt.danger ? "border-danger bg-danger-light/60 text-danger" : "border-primary bg-primary/10 text-primary"
                      : "border-border bg-surface text-content-muted hover:border-primary/30",
                  ].join(" ")}>
                  {opt.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <div>
        <label className={L}>Modele de detection</label>
        <select name="selected_model" value={formData.selected_model} onChange={handleChange}
          className="input-field w-full border-primary/20 bg-primary/5">
          <option value="xgboost">XGBoost — Champion (recommande)</option>
          <option value="random_forest">Random Forest</option>
          <option value="logistic_regression">Regression Logistique</option>
        </select>
      </div>

      <div className="space-y-2.5 pt-1">
        <button onClick={onSubmit} disabled={isLoading}
          className="h-10 w-full rounded-lg border border-border bg-white text-sm font-bold text-content hover:bg-surface disabled:opacity-50 transition-colors">
          {isLoading
            ? <span className="flex items-center justify-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Calcul...</span>
            : <span className="flex items-center justify-center gap-2"><Zap className="h-4 w-4" />Verification rapide</span>}
        </button>
        <button onClick={onFullAnalysis} disabled={isLoading}
          className="btn-primary h-12 w-full justify-center gap-2 shadow-soft disabled:opacity-50">
          {isLoading
            ? <span className="flex items-center justify-center gap-2"><Loader2 className="h-5 w-5 animate-spin" />Analyse en cours...</span>
            : <span className="flex items-center justify-center gap-2"><BrainCircuit className="h-5 w-5" />Analyse experte IA</span>}
        </button>
      </div>

    </div>
  );
});

Form.displayName = "Form";
export default Form;
