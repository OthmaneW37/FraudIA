import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  AreaChart, Area,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import {
  ShieldCheck, Activity, TrendingUp, AlertTriangle, BarChart3, PieChart as PieIcon, Clock, Layers, LogOut, Plus, Users
} from 'lucide-react';

const RISK_COLORS = {
  'FAIBLE': '#22c55e',
  'MOYEN': '#f59e0b',
  'ÉLEVÉ': '#f97316',
  'ELEVÉ': '#f97316',
  'CRITIQUE': '#ef4444',
};

const TYPE_LABELS = {
  transfer: 'Virement',
  payment: 'Paiement',
  purchase: 'Achat',
  online_purchase: 'Achat en ligne',
  withdrawal: 'Retrait',
};

const FEATURE_LABELS = {
  is_night: 'Heure nocturne',
  transaction_amount: 'Montant',
  log_amount: 'Log montant',
  amount_ratio: 'Ratio montant',
  time_diff: 'Écart temporel',
  hour: 'Heure',
  txn_count_today: 'Nb transactions/jour',
  kyc_verified: 'KYC vérifié',
  otp_used: 'OTP utilisé',
  merchant_category: 'Catégorie marchand',
  device_type: 'Type appareil',
  transaction_type: 'Type transaction',
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
      <p className="font-bold text-content mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.color }}>
          {p.name} : <span className="font-mono font-bold">{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</span>
        </p>
      ))}
    </div>
  );
};

const KpiCard = ({ icon: Icon, label, value, sub, color = 'text-primary' }) => (
  <div className="card p-5 bg-white flex items-start gap-4">
    <div className={`p-3 rounded-xl bg-surface ${color}`}>
      <Icon className="w-5 h-5" />
    </div>
    <div>
      <p className="text-xs text-content-muted font-medium uppercase tracking-wider">{label}</p>
      <p className="text-2xl font-bold text-content mt-1">{value}</p>
      {sub && <p className="text-xs text-content-muted mt-0.5">{sub}</p>}
    </div>
  </div>
);

const SectionTitle = ({ icon: Icon, title, subtitle }) => (
  <div className="flex items-center gap-3 mb-4">
    <div className="p-2 rounded-lg bg-surface text-primary">
      <Icon className="w-4 h-4" />
    </div>
    <div>
      <h3 className="text-sm font-bold text-content uppercase tracking-wide">{title}</h3>
      {subtitle && <p className="text-xs text-content-muted">{subtitle}</p>}
    </div>
  </div>
);

export default function AnalyticsPage({ user, health, onLogout, onNavigate, onNewAnalysis }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const analytics = await api.getAnalytics();
        setData(analytics);
      } catch (e) {
        console.warn('Analytics load failed', e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const riskPieData = (data?.risk_distribution || []).map(d => ({
    ...d,
    fill: RISK_COLORS[d.name] || '#94a3b8',
  }));

  const featureBarData = (data?.top_fraud_features || []).map(d => ({
    ...d,
    label: FEATURE_LABELS[d.feature] || d.feature,
  }));

  const typeData = (data?.by_type || []).map(d => ({
    ...d,
    label: TYPE_LABELS[d.type] || d.type,
  }));

  const categoryData = (data?.by_category || []).map(d => ({
    ...d,
    label: d.category,
  }));

  const hourData = data?.by_hour || [];
  const timeline = data?.score_timeline || [];

  return (
    <div className="min-h-screen bg-background">
      {/* Header — identique au dashboard */}
      <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <div className="flex items-center gap-2 cursor-pointer" onClick={() => onNavigate('landing')}>
              <ShieldCheck className="w-6 h-6 text-primary" />
              <span className="font-bold text-lg">FraudIA</span>
            </div>
            <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-content-muted">
              <span onClick={() => onNavigate('dashboard')} className="hover:text-content transition-colors cursor-pointer">{user?.role === 'superadmin' ? 'Supervision Globale' : 'Opérations'}</span>
              <span className="text-content pb-1 border-b-2 border-primary cursor-pointer">Analytiques</span>
              {user?.role === 'superadmin' && (
                <span onClick={() => onNavigate('admin')} className="hover:text-content transition-colors cursor-pointer flex items-center gap-1">
                  <Users className="w-4 h-4"/> Équipe
                </span>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 text-xs font-bold uppercase ${health?.status === 'healthy' ? 'text-success' : 'text-danger'}`}>
              <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-success' : 'bg-danger animate-pulse'}`}></div>
              {health?.status === 'healthy' ? 'API Active' : 'API Injoignable'}
            </div>
            <button onClick={onNewAnalysis} className="btn-primary flex items-center gap-2 text-sm">
              <Plus className="w-4 h-4" /> Nouvelle Analyse
            </button>
            {user && (
              <div className="flex items-center gap-3 ml-2 pl-4 border-l border-border">
                <div className="text-right hidden md:block">
                  <p className="text-xs font-bold text-content">{user.full_name}</p>
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
        <div className="mb-8">
          <h1 className="text-3xl font-serif mb-2 text-content">
            {user?.role === 'superadmin' ? 'Analytiques Globales' : 'Vos Analytiques'}
          </h1>
          <p className="text-content-muted text-sm">
            {user?.role === 'superadmin' 
              ? 'Performance et tendances globales de détection de fraude sur l\'ensemble des analystes.'
              : 'Vue d\'ensemble de vos analyses de fraude — données cloisonnées par analyste.'}
          </p>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary border-t-transparent"></div>
          </div>
        ) : !data || data.total === 0 ? (
          <div className="card p-12 bg-white text-center">
            <Activity className="w-10 h-10 text-border mx-auto mb-4" />
            <p className="text-content-muted text-sm">Aucune donnée d'analyse disponible.</p>
            <p className="text-content-muted text-xs mt-1">Effectuez des analyses pour voir apparaître vos statistiques.</p>
          </div>
        ) : (
          <>
            {/* KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <KpiCard icon={Activity} label="Analyses effectuées" value={data.total} />
              <KpiCard icon={TrendingUp} label="Score moyen" value={`${data.avg_score}%`} color="text-warning" />
              <KpiCard icon={AlertTriangle} label="Risque élevé / critique" value={data.high_risk_count} sub={`${((data.high_risk_count / data.total) * 100).toFixed(0)}% du total`} color="text-danger" />
              <KpiCard icon={ShieldCheck} label="Taux de conformité" value={`${(100 - (data.high_risk_count / data.total) * 100).toFixed(0)}%`} sub="Transactions à faible risque" color="text-success" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Pie Chart — Répartition risque */}
              <div className="card p-6 bg-white">
                <SectionTitle 
                  icon={PieIcon} 
                  title="Répartition par niveau de risque" 
                  subtitle={user?.role === 'superadmin' ? "Distribution des analyses de l'équipe" : "Distribution de vos analyses"} 
                />
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={riskPieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      innerRadius={55}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {riskPieData.map((entry, i) => (
                        <Cell key={i} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      verticalAlign="bottom"
                      formatter={(value) => <span className="text-xs font-medium text-content">{value}</span>}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Bar Chart — Facteurs de fraude les plus impactants */}
              <div className="card p-6 bg-white">
                <SectionTitle icon={BarChart3} title="Facteurs de fraude dominants" subtitle="Impact SHAP cumulé sur les transactions à risque" />
                {featureBarData.length === 0 ? (
                  <div className="flex items-center justify-center h-[280px] text-content-muted text-sm">
                    Pas assez de données
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height={280}>
                    <BarChart data={featureBarData} layout="vertical" margin={{ left: 20, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                      <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                      <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" width={120} />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar dataKey="total_impact" name="Impact cumulé" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={20} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Bar Chart — Par type de transaction */}
              <div className="card p-6 bg-white">
                <SectionTitle icon={Layers} title="Analyse par type de transaction" subtitle="Total vs transactions à risque" />
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={typeData} margin={{ left: 10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend formatter={(value) => <span className="text-xs font-medium">{value}</span>} />
                    <Bar dataKey="total" name="Total" fill="#94a3b8" radius={[4, 4, 0, 0]} barSize={28} />
                    <Bar dataKey="risky" name="À risque" fill="#ef4444" radius={[4, 4, 0, 0]} barSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Bar Chart — Par catégorie marchand */}
              <div className="card p-6 bg-white">
                <SectionTitle icon={Layers} title="Analyse par catégorie marchand" subtitle="Secteurs les plus analysés" />
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={categoryData} margin={{ left: 10, right: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend formatter={(value) => <span className="text-xs font-medium">{value}</span>} />
                    <Bar dataKey="total" name="Total" fill="#94a3b8" radius={[4, 4, 0, 0]} barSize={28} />
                    <Bar dataKey="risky" name="À risque" fill="#f97316" radius={[4, 4, 0, 0]} barSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
              {/* Area Chart — Distribution horaire */}
              <div className="card p-6 bg-white">
                <SectionTitle icon={Clock} title="Distribution horaire des analyses" subtitle="Heures les plus fréquentes et à risque" />
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={hourData} margin={{ left: 10, right: 10 }}>
                    <defs>
                      <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                      <linearGradient id="gradRisk" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ef4444" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="hour" tick={{ fontSize: 11 }} stroke="#9ca3af" tickFormatter={(h) => `${h}h`} />
                    <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" allowDecimals={false} />
                    <Tooltip content={<CustomTooltip />} labelFormatter={(h) => `${h}h00`} />
                    <Area type="monotone" dataKey="total" name="Total" stroke="#6366f1" fill="url(#gradTotal)" strokeWidth={2} />
                    <Area type="monotone" dataKey="risky" name="À risque" stroke="#ef4444" fill="url(#gradRisk)" strokeWidth={2} />
                    <Legend formatter={(value) => <span className="text-xs font-medium">{value}</span>} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Timeline — Évolution des scores */}
              <div className="card p-6 bg-white">
                <SectionTitle icon={TrendingUp} title="Évolution des scores de fraude" subtitle="Historique chronologique de vos analyses" />
                <ResponsiveContainer width="100%" height={280}>
                  <AreaChart data={timeline} margin={{ left: 10, right: 10 }}>
                    <defs>
                      <linearGradient id="gradScore" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="tx_id" tick={{ fontSize: 9 }} stroke="#9ca3af" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div className="bg-white border border-border rounded-lg shadow-lg px-3 py-2 text-xs">
                            <p className="font-mono font-bold text-content">{d.tx_id}</p>
                            <p className="text-content-muted">{d.date}</p>
                            <p className="mt-1">Score : <span className="font-bold" style={{ color: RISK_COLORS[d.risk] || '#6366f1' }}>{d.score}%</span></p>
                            <p>Niveau : <span className="font-bold" style={{ color: RISK_COLORS[d.risk] || '#6366f1' }}>{d.risk}</span></p>
                          </div>
                        );
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="score"
                      name="Score %"
                      stroke="#f59e0b"
                      fill="url(#gradScore)"
                      strokeWidth={2}
                      dot={({ cx, cy, payload }) => (
                        <circle
                          key={payload.tx_id}
                          cx={cx}
                          cy={cy}
                          r={5}
                          fill={RISK_COLORS[payload.risk] || '#f59e0b'}
                          stroke="#fff"
                          strokeWidth={2}
                        />
                      )}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {user?.role === 'superadmin' && data.by_analyst && data.by_analyst.length > 0 && (
              <div className="card p-6 bg-white mb-6">
                <SectionTitle icon={Users} title="Volume par Analyste" subtitle="Répartition de la charge de travail au sein de l'équipe" />
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={data.by_analyst} layout="vertical" margin={{ left: 40, right: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" horizontal={false} />
                    <XAxis type="number" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} stroke="#9ca3af" width={140} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="count" name="Analyses" fill="#10b981" radius={[0, 4, 4, 0]} barSize={30} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
