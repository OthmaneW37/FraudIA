import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, Mail, Lock, Loader2, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { api } from '../api/client';

const LoginPage = ({ onLogin }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      const data = await api.login(email, password);
      onLogin(data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Email ou mot de passe incorrect');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left panel - branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-content relative flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-primary" />
          <span className="text-2xl font-bold text-white tracking-tight">FraudIA</span>
        </div>
        
        <div>
          <h1 className="text-5xl font-serif text-white leading-tight mb-6">
            Plateforme d'investigation<br />
            <span className="text-primary italic">intelligente.</span>
          </h1>
          <p className="text-white/60 text-lg max-w-md leading-relaxed">
            Accédez à votre espace analyste pour investiguer les transactions suspectes avec l'aide de l'intelligence artificielle.
          </p>
        </div>

        <p className="text-white/30 text-xs">
          © 2026 FraudIA — Système de détection de fraude par IA
        </p>
      </div>

      {/* Right panel - login form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <motion.div 
          initial={{ opacity: 0, y: 20 }} 
          animate={{ opacity: 1, y: 0 }} 
          transition={{ duration: 0.5 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center gap-2 mb-12 justify-center">
            <ShieldCheck className="w-7 h-7 text-primary" />
            <span className="text-xl font-bold text-content">FraudIA</span>
          </div>

          <div className="mb-8">
            <h2 className="text-3xl font-serif text-content mb-2">Connexion</h2>
            <p className="text-content-muted text-sm">
              Identifiez-vous avec vos identifiants fournis par la banque.
            </p>
          </div>

          {error && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }} 
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-danger-light border border-danger/20 rounded-lg flex items-center gap-3 text-danger text-sm font-bold"
            >
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-content-muted uppercase tracking-widest mb-2">
                Adresse email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-muted" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="analyste@fraudia.ma"
                  required
                  className="w-full pl-10 pr-4 py-3 bg-white border border-border rounded-lg text-sm text-content placeholder:text-content-muted/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-content-muted uppercase tracking-widest mb-2">
                Mot de passe
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-muted" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-12 py-3 bg-white border border-border rounded-lg text-sm text-content placeholder:text-content-muted/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-content-muted hover:text-content transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading || !email || !password}
              className="w-full bg-content text-white py-3 rounded-lg font-medium text-sm hover:bg-content/90 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Connexion en cours...
                </>
              ) : (
                'Se connecter'
              )}
            </button>
          </form>

          <div className="mt-8 p-4 bg-surface rounded-lg border border-border">
            <p className="text-xs text-content-muted text-center">
              Les identifiants sont fournis par votre administrateur.<br />
              Contactez le support en cas de problème d'accès.
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default LoginPage;
