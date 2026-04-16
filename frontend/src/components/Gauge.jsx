import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const Gauge = React.memo(({ value, isFraud }) => {
  const data = [
    { name: 'Score', value: value * 100 },
    { name: 'Remaining', value: 100 - (value * 100) },
  ];

  const getColor = () => {
    if (value > 0.7) return '#EF4444'; // Danger
    if (value > 0.4) return '#F97316'; // Warning
    return '#22C55E'; // Success
  };

  const getPillClass = () => {
    if (value > 0.7) return 'bg-danger-light text-danger';
    if (value > 0.4) return 'bg-warning-light text-warning';
    return 'bg-success-light text-success';
  }

  const mainColor = getColor();

  return (
    <div className="relative w-full flex flex-col">
      <div className="relative w-full h-[160px] mt-6 overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                startAngle={180}
                endAngle={0}
                innerRadius="75%"
                outerRadius="90%"
                paddingAngle={0}
                dataKey="value"
                stroke="none"
                cornerRadius={40}
              >
                <Cell fill={mainColor} />
                <Cell fill="#E5E5E5" />
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>
        
        {/* Score and Badge inside the arch */}
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-4">
          <div className="flex items-baseline mb-1">
             <span className="text-6xl font-serif text-content tracking-tighter tabular-nums leading-none">
               {(value * 100).toFixed(0)}
             </span>
             <span className="text-xl font-bold text-content-muted ml-0.5">%</span>
          </div>
          <div className={`px-4 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${getPillClass()}`}>
             {value > 0.7 ? 'Risque Critique' : value > 0.4 ? 'Risque Modéré' : 'Risque Faible'}
          </div>
        </div>
      </div>

      {/* Decorative marks and label safely below the arch */}
      <div className="mt-8 pt-4 border-t border-border w-full flex flex-col items-center gap-2">
         <span className="text-[10px] text-content-muted font-bold uppercase tracking-widest">
           Probabilité de Fraude
         </span>
         <div className="w-full flex justify-between px-[10%] text-[10px] font-bold text-content-muted tracking-widest uppercase">
            <span>Min</span>
            <span className="text-content">Seuil (80%)</span>
            <span>Max</span>
         </div>
      </div>
    </div>
  );
});

Gauge.displayName = 'Gauge';
export default Gauge;
