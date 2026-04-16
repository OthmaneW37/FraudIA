import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer } from 'recharts';

const Gauge = React.memo(({ value, isFraud }) => {
  const data = [
    { name: 'Score', value: value * 100 },
    { name: 'Remaining', value: 100 - (value * 100) },
  ];

  const getColor = () => {
    if (value > 0.7) return '#f43f5e'; // Danger
    if (value > 0.4) return '#fbbf24'; // Warning (Amber)
    return '#10b981'; // Success
  };

  const mainColor = getColor();

  return (
    <div className="relative w-full h-[300px] flex items-center justify-center">
      {/* Background Glow */}
      <div 
        className="absolute w-40 h-40 rounded-full blur-[60px] opacity-20"
        style={{ backgroundColor: mainColor }}
      ></div>

      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="80%"
            startAngle={200}
            endAngle={-20}
            innerRadius="75%"
            outerRadius="95%"
            paddingAngle={0}
            dataKey="value"
            stroke="none"
            cornerRadius={40}
          >
            <Cell fill={mainColor} className="drop-shadow-[0_0_10px_rgba(0,0,0,0.5)]" />
            <Cell fill="rgba(255, 255, 255, 0.03)" />
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-12">
        <div className="relative">
           <span className="text-6xl font-black text-white tracking-tighter">
             {(value * 100).toFixed(0)}
           </span>
           <span className="text-xl font-bold text-slate-500 absolute -right-6 top-2">%</span>
        </div>
        <div className="flex flex-col items-center mt-2">
           <div className={`px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-[0.15em] mb-1 ${value > 0.5 ? 'bg-danger/10 text-danger' : 'bg-success/10 text-success'}`}>
             {value > 0.7 ? 'Risque Critique' : value > 0.4 ? 'Risque Mod\u00e9r\u00e9' : 'Risque Faible'}
           </div>
           <span className="text-xs text-slate-500 font-bold uppercase tracking-widest opacity-50">
             Indice de Probabilit\u00e9 de Fraude
           </span>
        </div>
      </div>

      {/* Decorative Marks */}
      <div className="absolute bottom-12 w-full flex justify-between px-[20%] text-xs font-black text-slate-700 tracking-widest uppercase">
         <span>Min</span>
         <span>Seuil</span>
         <span>Max</span>
      </div>
    </div>
  );
});

Gauge.displayName = 'Gauge';
export default Gauge;
