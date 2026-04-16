import React, { useRef, useCallback } from 'react';
import { Zap, BrainCircuit, Info, Loader2 } from 'lucide-react';

const Form = React.memo(({ formData, setFormData, onSubmit, isLoading, onFullAnalysis }) => {
  const debounceRef = useRef({});

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    const val = type === 'checkbox' ? checked : value;

    // Debounce number inputs to avoid re-render storm on fast typing
    if (type === 'number') {
      if (debounceRef.current[name]) clearTimeout(debounceRef.current[name]);
      debounceRef.current[name] = setTimeout(() => {
        setFormData(prev => ({ ...prev, [name]: val }));
      }, 300);
    } else {
      setFormData(prev => ({ ...prev, [name]: val }));
    }
  }, [setFormData]);

  const inputClasses = "w-full bg-slate-800/40 border border-white/5 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary/40 transition-all";
  const labelClasses = "block text-xs font-black text-slate-500 uppercase tracking-widest mb-1.5 ml-1";

  return (
    <div className="space-y-5">
      {/* ID + Montant + Heure */}
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className={labelClasses}>Identifiant Transaction</label>
          <input 
            name="transaction_id"
            value={formData.transaction_id}
            onChange={handleChange}
            className={inputClasses}
            placeholder="Ex: TX_9921_AF"
          />
        </div>
        
        <div>
          <label className={labelClasses}>Montant (MAD)</label>
          <div className="relative">
             <input 
                type="number"
                name="transaction_amount"
                defaultValue={formData.transaction_amount}
                onChange={handleChange}
                className={inputClasses}
             />
             <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-600">MAD</span>
          </div>
        </div>

        <div>
           <label className={labelClasses}>Heure locale</label>
           <select 
              name="hour"
              value={formData.hour}
              onChange={handleChange}
              className={inputClasses}
           >
              {[...Array(24)].map((_, i) => (
                <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
              ))}
           </select>
        </div>
      </div>

      {/* Type + Secteur */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelClasses}>Type de Transaction</label>
          <select 
            name="transaction_type"
            value={formData.transaction_type}
            onChange={handleChange}
            className={inputClasses}
          >
            <option value="transfer">Virement</option>
            <option value="payment">Paiement</option>
            <option value="withdrawal">Retrait</option>
            <option value="deposit">Dépôt</option>
            <option value="purchase">Achat en ligne</option>
            <option value="other">Autre</option>
          </select>
        </div>
        <div>
          <label className={labelClasses}>Secteur Marchand</label>
          <select 
            name="merchant_category"
            value={formData.merchant_category}
            onChange={handleChange}
            className={inputClasses}
          >
            <option value="retail">Commerce de détail</option>
            <option value="crypto">Cryptomonnaies</option>
            <option value="gambling">Jeux d'argent</option>
            <option value="leisure">Loisirs & Tourisme</option>
            <option value="tech">Technologie</option>
          </select>
        </div>
      </div>

      {/* Localisation: Ville + Pays */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelClasses}>Ville</label>
          <select 
            name="city"
            value={formData.city}
            onChange={handleChange}
            className={inputClasses}
          >
            <option value="Casablanca">Casablanca</option>
            <option value="Rabat">Rabat</option>
            <option value="Marrakech">Marrakech</option>
            <option value="Fes">Fès</option>
            <option value="Tanger">Tanger</option>
            <option value="Agadir">Agadir</option>
            <option value="Autre">Autre</option>
          </select>
        </div>
        <div>
          <label className={labelClasses}>Pays</label>
          <select 
            name="country"
            value={formData.country}
            onChange={handleChange}
            className={inputClasses}
          >
            <option value="Maroc">Maroc</option>
            <option value="France">France</option>
            <option value="Espagne">Espagne</option>
            <option value="USA">USA</option>
            <option value="Nigeria">Nigeria</option>
            <option value="Chine">Chine</option>
            <option value="Autre">Autre</option>
          </select>
        </div>
      </div>

      {/* Device + Devise */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelClasses}>Appareil / Device</label>
          <select 
            name="device_type"
            value={formData.device_type}
            onChange={handleChange}
            className={inputClasses}
          >
            <option value="Mobile App">Mobile App</option>
            <option value="Desktop Web">Desktop Web</option>
            <option value="Tablet">Tablette</option>
            <option value="API">API / Bot</option>
            <option value="POS">Terminal POS</option>
            <option value="ATM">Distributeur ATM</option>
          </select>
        </div>
        <div>
          <label className={labelClasses}>Devise</label>
          <select 
            name="currency"
            value={formData.currency}
            onChange={handleChange}
            className={inputClasses}
          >
            <option value="MAD">MAD</option>
            <option value="EUR">EUR</option>
            <option value="USD">USD</option>
            <option value="GBP">GBP</option>
          </select>
        </div>
      </div>

      {/* Historique client */}
      <div>
        <label className={labelClasses}>Moy. montant 30j (MAD)</label>
        <input 
          type="number"
          name="avg_amount_30d"
          defaultValue={formData.avg_amount_30d}
          onChange={handleChange}
          className={inputClasses}
          placeholder="1000"
        />
      </div>

      {/* Moteur + Toggles */}
      <div>
        <label className={labelClasses}>Moteur d'Inférence</label>
        <select 
          name="selected_model"
          value={formData.selected_model}
          onChange={handleChange}
          className={inputClasses}
        >
          <option value="xgboost">XGBoost (Default)</option>
          <option value="random_forest">Random Forest</option>
          <option value="logistic_regression">Logistic Regression</option>
        </select>
      </div>

      <div className="flex items-center gap-6 pt-1">
        <label className="flex items-center gap-3 cursor-pointer group">
          <div className="relative">
            <input type="checkbox" name="otp_used" checked={formData.otp_used} onChange={handleChange} className="sr-only peer" />
            <div className="w-10 h-6 bg-slate-800 rounded-full peer peer-checked:bg-primary transition-colors"></div>
            <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-4"></div>
          </div>
          <span className="text-xs font-bold text-slate-400 group-hover:text-slate-200 transition-colors">OTP Vérifié</span>
        </label>
      </div>

      {/* Boutons */}
      <div className="pt-3 space-y-3">
        <button 
          onClick={onSubmit}
          disabled={isLoading}
          className="cyber-button cyber-button-outline w-full h-12 flex items-center justify-center gap-3 group disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /><span className="text-sm">Analyse en cours...</span></>
          ) : (
            <><Zap className="w-4 h-4 group-hover:text-primary transition-colors" /><span className="text-sm">Vérification Rapide</span></>
          )}
        </button>
        
        <button 
          onClick={onFullAnalysis}
          disabled={isLoading}
          className="cyber-button cyber-button-primary w-full h-14 flex items-center justify-center gap-3 shadow-lg shadow-primary/20 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <><Loader2 className="w-5 h-5 animate-spin" /><span className="text-sm">Génération du rapport...</span></>
          ) : (
            <><BrainCircuit className="w-5 h-5" /><span className="text-sm">Expertise IA Complète</span></>
          )}
        </button>
      </div>

      <div className="p-3 rounded-xl bg-primary/5 border border-primary/10 flex gap-3">
         <Info className="w-4 h-4 text-primary shrink-0 mt-0.5" />
         <p className="text-xs text-slate-400 leading-relaxed font-medium">
            Le mode "Expertise IA" génère un rapport SHAP + analyse LLM locale (LLaMA 3.2). Temps estimé : 15-30s.
         </p>
      </div>
    </div>
  );
});

Form.displayName = 'Form';
export default Form;
