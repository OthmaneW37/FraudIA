import React from 'react';

const SHAPBarChart = React.memo(({ features }) => {
  if (!features || features.length === 0) return null;

  const maxVal = Math.max(...features.map(f => Math.abs(f.shap_value)));

  return (
    <div className="space-y-5">
      <div className="space-y-3">
        {features.map((feat, idx) => {
          const isPositive = feat.shap_value > 0;
          const percentage = (Math.abs(feat.shap_value) / maxVal) * 100;
          
          return (
            <div 
              key={idx}
              className="group"
            >
              <div className="flex justify-between items-center mb-1.5 px-1">
                <span className="text-sm font-medium text-content group-hover:text-primary transition-colors tracking-tight">
                   {feat.feature.replace(/_/g, ' ')}
                </span>
                <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${isPositive ? 'bg-danger-light text-danger' : 'bg-success-light text-success'}`}>
                 {isPositive ? '▲' : '▼'} {Math.abs(feat.shap_value).toFixed(4)}
                </span>
              </div>
              <div className="h-2 w-full bg-surface rounded-full overflow-hidden border border-border">
                <div 
                  style={{ width: `${percentage}%` }}
                  className={`h-full rounded-full transition-all duration-1000 ease-out ${isPositive ? 'bg-danger' : 'bg-success'}`}
                />
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="pt-4 border-t border-border flex justify-between items-center px-1">
         <span className="text-[10px] font-bold text-content-muted uppercase tracking-widest">Interprétation</span>
         <div className="flex gap-4">
            <div className="flex items-center gap-1.5">
               <div className="w-2 h-2 rounded-full bg-danger"></div>
               <span className="text-[10px] font-bold text-content-muted uppercase tracking-wider">Pro-Fraude</span>
            </div>
            <div className="flex items-center gap-1.5">
               <div className="w-2 h-2 rounded-full bg-success"></div>
               <span className="text-[10px] font-bold text-content-muted uppercase tracking-wider">Légitime</span>
            </div>
         </div>
      </div>
    </div>
  );
});

SHAPBarChart.displayName = 'SHAPBarChart';
export default SHAPBarChart;
