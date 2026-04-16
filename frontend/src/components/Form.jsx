import React, { useRef, useCallback } from 'react';
import { Zap, BrainCircuit, Info, Loader2, Cpu, Cloud } from 'lucide-react';

const Form = React.memo(({ formData, setFormData, onSubmit, isLoading, onFullAnalysis, llmProvider, setLlmProvider }) => {
  const debounceRef = useRef({});

  const handleChange = useCallback((e) => {
    const { name, value, type, checked } = e.target;
    const val = type === 'checkbox' ? checked : value;

    if (type === 'number') {
      if (debounceRef.current[name]) clearTimeout(debounceRef.current[name]);
      debounceRef.current[name] = setTimeout(() => {
        setFormData(prev => ({ ...prev, [name]: val }));
      }, 300);
    } else {
      setFormData(prev => ({ ...prev, [name]: val }));
    }
  }, [setFormData]);

  const labelClasses = "block text-xs font-bold text-content-muted uppercase tracking-widest mb-1.5 ml-0.5";

  return (
    <div className="space-y-6">
      {/* ID + Montant + Heure */}
      <div className="grid grid-cols-2 gap-4">
        <div className="col-span-2">
          <label className={labelClasses}>Identifiant Transaction</label>
          <input 
            name="transaction_id"
            value={formData.transaction_id}
            onChange={handleChange}
            className="input-field"
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
                className="input-field pr-12 w-full tabular-nums"
             />
             <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-content-muted">MAD</span>
          </div>
        </div>

        <div>
           <label className={labelClasses}>Heure locale</label>
           <select 
              name="hour"
              value={formData.hour}
              onChange={handleChange}
              className="input-field w-full tabular-nums"
           >
              {[...Array(24)].map((_, i) => (
                <option key={i} value={i}>{i.toString().padStart(2, '0')}:00</option>
              ))}
           </select>
        </div>
      </div>

      {/* Type + Secteur */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClasses}>Type de Transaction</label>
          <select 
            name="transaction_type"
            value={formData.transaction_type}
            onChange={handleChange}
            className="input-field w-full"
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
            className="input-field w-full"
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
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClasses}>Ville</label>
          <select 
            name="city"
            value={formData.city}
            onChange={handleChange}
            className="input-field w-full"
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
            className="input-field w-full"
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
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClasses}>Appareil</label>
          <select 
            name="device_type"
            value={formData.device_type}
            onChange={handleChange}
            className="input-field w-full"
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
            className="input-field w-full"
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
          className="input-field w-full tabular-nums"
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
          className="input-field w-full"
        >
          <option value="xgboost">XGBoost (Default)</option>
          <option value="random_forest">Random Forest</option>
          <option value="logistic_regression">Logistic Regression</option>
        </select>
      </div>

      {/* ── Sélecteur Moteur LLM ── */}
      <div className="p-4 rounded-xl bg-white border border-border space-y-3">
        <p className="text-xs font-bold text-content-muted uppercase tracking-widest mb-2">Moteur d'Explication IA</p>
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setLlmProvider('local')}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-bold transition-all ${
              llmProvider === 'local'
                ? 'bg-primary-light border-primary/30 text-primary'
                : 'bg-surface border-border text-content-muted hover:text-content hover:bg-white'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            Mistral Local
          </button>
          <button
            type="button"
            onClick={() => setLlmProvider('perplexity')}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-bold transition-all ${
              llmProvider === 'perplexity'
                ? 'bg-secondary-light border-secondary/30 text-secondary'
                : 'bg-surface border-border text-content-muted hover:text-content hover:bg-white'
            }`}
          >
            <Cloud className="w-3.5 h-3.5" />
            Perplexity API
          </button>
        </div>

        {llmProvider === 'perplexity' && (
          <p className="text-[11px] text-content-muted ml-1">
            Clé API configurée via <code className="font-mono bg-surface px-1 py-0.5 rounded">.env</code>
          </p>
        )}
      </div>

      <div className="flex items-center gap-6 pt-2">
        <label className="flex items-center gap-3 cursor-pointer group">
          <div className="relative">
            <input type="checkbox" name="otp_used" checked={formData.otp_used} onChange={handleChange} className="sr-only peer" />
            <div className="w-10 h-6 bg-surface border border-border rounded-full peer peer-checked:bg-primary transition-colors"></div>
            <div className="absolute left-1 top-1 w-4 h-4 bg-white shadow-sm rounded-full transition-transform peer-checked:translate-x-4"></div>
          </div>
          <span className="text-sm font-medium text-content group-hover:text-primary transition-colors">OTP Vérifié</span>
        </label>
      </div>

      {/* Boutons */}
      <div className="pt-6 space-y-3">
        <button 
          onClick={onSubmit}
          disabled={isLoading}
          className="w-full h-12 flex items-center justify-center gap-2 rounded-lg font-medium text-sm border border-border bg-white text-content hover:bg-surface transition-colors disabled:opacity-50"
        >
          {isLoading ? (
            <><Loader2 className="w-4 h-4 animate-spin" /><span>Analyse en cours...</span></>
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
            <><Loader2 className="w-5 h-5 animate-spin" /><span>Génération...</span></>
          ) : (
            <><BrainCircuit className="w-5 h-5" /><span>Expertise IA Complète</span></>
          )}
        </button>
      </div>
    </div>
  );
});

Form.displayName = 'Form';
export default Form;
