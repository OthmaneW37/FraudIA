import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, Terminal, ShieldAlert } from 'lucide-react';

const AgentReport = React.memo(({ report }) => {
  if (!report) return (
    <div className="h-full flex flex-col items-center justify-center p-12 text-center border-2 border-dashed border-white/5 rounded-3xl group">
      <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-500">
         <Bot className="w-8 h-8 text-slate-700" />
      </div>
      <h4 className="text-sm font-bold text-slate-400 mb-2">En attente d'expertise</h4>
      <p className="text-xs text-slate-600 max-w-[200px] leading-relaxed">
        {`G\u00e9n\u00e9rez une analyse compl\u00e8te pour solliciter le module de raisonnement LLM.`}
      </p>
    </div>
  );

  // Parse sections from LLM response
  const parseReport = (text) => {
    const sections = [];
    // Try to split by common LLM patterns: [SECTION], **SECTION**, etc.
    const sectionRegex = /\[([A-ZÀ-Ü\s]+)\]\s*:?\s*/g;
    let lastIndex = 0;
    let match;
    
    while ((match = sectionRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        const content = text.slice(lastIndex, match.index).trim();
        if (content) sections.push({ title: null, content });
      }
      lastIndex = match.index + match[0].length;
      const nextMatch = sectionRegex.exec(text);
      const end = nextMatch ? nextMatch.index : text.length;
      sections.push({ title: match[1].trim(), content: text.slice(lastIndex, end).trim() });
      lastIndex = end;
      if (nextMatch) sectionRegex.lastIndex = nextMatch.index;
    }
    
    if (sections.length === 0) {
      sections.push({ title: null, content: text });
    } else if (lastIndex < text.length) {
      const remaining = text.slice(lastIndex).trim();
      if (remaining) sections.push({ title: null, content: remaining });
    }
    
    return sections;
  };

  const sections = parseReport(report);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative h-full flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
           <div className="w-10 h-10 rounded-xl bg-accent/20 flex items-center justify-center">
              <Bot className="w-5 h-5 text-accent" />
           </div>
           <div>
              <h3 className="text-base font-black text-white uppercase tracking-tight">Investigateur IA</h3>
              <p className="text-xs font-bold text-accent/60 uppercase tracking-widest leading-none">Rapport d'analyse</p>
           </div>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 bg-white/5 rounded-full border border-white/5">
           <Terminal className="w-3 h-3 text-slate-500" />
           <span className="text-xs font-mono font-bold text-slate-400">LLaMA 3.2</span>
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto max-h-[400px] pr-1 space-y-4 scrollbar-thin">
        {sections.map((section, i) => (
          <div key={i}>
            {section.title && (
              <div className="flex items-center gap-2 mb-2">
                <ShieldAlert className="w-3.5 h-3.5 text-accent/70" />
                <span className="text-xs font-black text-accent uppercase tracking-widest">{section.title}</span>
              </div>
            )}
            <p className="text-sm text-slate-300 leading-relaxed">
              {section.content}
            </p>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-5 pt-4 border-t border-white/5 flex items-center justify-between">
         <div className="flex gap-1">
            <motion.div animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1.5 }} className="w-1.5 h-1.5 rounded-full bg-accent" />
            <motion.div animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-accent" />
            <motion.div animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-accent" />
         </div>
         <div className="flex items-center gap-2 text-primary">
            <Sparkles className="w-4 h-4" />
            <span className="text-xs font-black uppercase tracking-widest text-primary/80">Analyse certifi\u00e9e</span>
         </div>
      </div>
    </motion.div>
  );
});

AgentReport.displayName = 'AgentReport';
export default AgentReport;
