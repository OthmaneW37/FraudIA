import React from 'react';

const SHAPBarChart = React.memo(({ features }) => {
  if (!features || features.length === 0) return null;

  const maxVal = Math.max(...features.map(f => Math.abs(f.shap_value)));

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        {features.map((feat, idx) => {
          const isPositive = feat.shap_value > 0;
          const percentage = (Math.abs(feat.shap_value) / maxVal) * 100;
          
          return (
            <div 
              key={idx}
              className="group"
            >
              <div className="flex justify-between items-center mb-2 px-1">
                <span className="text-sm font-bold text-slate-300 group-hover:text-white transition-colors tracking-tight">
                   {feat.feature.replace(/_/g, ' ')}
                </span>
                <span className={`text-xs font-mono font-bold px-2 py-0.5 rounded-md ${isPositive ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'}`}>
                  {isPositive ? '\u25b2' : '\u25bc'} {Math.abs(feat.shap_value).toFixed(4)}
                </span>
              </div>
              <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden border border-white/5 p-[1px]">
                <div className="h-full w-full bg-slate-800/50 rounded-full overflow-hidden">
                  <div 
                    style={{ width: `${percentage}%` }}
                    className={`h-full rounded-full transition-all duration-1000 ease-out ${isPositive ? 'bg-gradient-to-r from-danger/40 to-danger shadow-[0_0_10px_rgba(244,63,94,0.3)]' : 'bg-gradient-to-r from-success/40 to-success shadow-[0_0_10px_rgba(16,185,129,0.3)]'}`}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="pt-4 border-t border-white/5 flex justify-between items-center px-1">
         <span className="text-xs font-bold text-slate-500 uppercase tracking-widest">Interpr\u00e9tation</span>
         <div className="flex gap-4">
            <div className="flex items-center gap-1.5">
               <div className="w-2 h-2 rounded-full bg-danger"></div>
               <span className="text-[11px] font-bold text-slate-400 uppercase">Pro-Fraude</span>
            </div>
            <div className="flex items-center gap-1.5">
               <div className="w-2 h-2 rounded-full bg-success"></div>
               <span className="text-[11px] font-bold text-slate-400 uppercase">L\u00e9gitime</span>
            </div>
         </div>
      </div>
    </div>
  );
});

SHAPBarChart.displayName = 'SHAPBarChart';
export default SHAPBarChart;
