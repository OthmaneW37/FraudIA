import React from 'react';
import { motion } from 'framer-motion';
import { Bot, Sparkles, Terminal, ShieldAlert } from 'lucide-react';

/**
 * Transforme le texte brut du LLM en sections visuelles.
 */
function parseReport(text) {
  if (!text || typeof text !== 'string') return [{ title: null, content: String(text || '') }];

  const sections = [];
  const lines = text.split('\n');
  let currentSection = { title: null, lines: [] };

  for (const line of lines) {
    const bracketMatch = line.match(/^\[([A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖÙÚÛÜÝ\s]+)\]\s*:?\s*(.*)/);
    if (bracketMatch) {
      if (currentSection.lines.length > 0 || currentSection.title) {
        sections.push({
          title: currentSection.title,
          content: currentSection.lines.join('\n').trim(),
        });
      }
      currentSection = {
        title: bracketMatch[1].trim(),
        lines: bracketMatch[2] ? [bracketMatch[2]] : [],
      };
    } else {
      currentSection.lines.push(line);
    }
  }

  if (currentSection.lines.length > 0 || currentSection.title) {
    sections.push({
      title: currentSection.title,
      content: currentSection.lines.join('\n').trim(),
    });
  }

  return sections.length > 0 ? sections : [{ title: null, content: text }];
}

const SECTION_COLORS = {
  'NIVEAU DE RISQUE': 'text-warning',
  'MOTIFS PRINCIPAUX': 'text-primary',
  'RECOMMANDATION': 'text-secondary',
};

const AgentReport = React.memo(({ report, llmProvider }) => {
  if (!report) return (
    <div className="h-full flex flex-col items-center justify-center p-12 text-center border-l-4 border-border rounded-r-xl bg-surface">
      <Bot className="w-8 h-8 text-content-muted mb-4" />
      <h4 className="text-sm font-bold text-content-muted mb-2">En attente d'expertise</h4>
      <p className="text-xs text-content-muted max-w-[200px] leading-relaxed">
        Générez une analyse complète pour solliciter le module de raisonnement LLM.
      </p>
    </div>
  );

  let sections;
  try {
    sections = parseReport(report);
  } catch {
    sections = [{ title: null, content: String(report) }];
  }

  const providerLabel = llmProvider === 'perplexity' ? 'Perplexity API' : 'Mistral Local';

  return (
    <motion.div 
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative h-full flex flex-col border-l-4 border-primary bg-white rounded-r-xl p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5 pb-4 border-b border-border">
        <div className="flex items-center gap-3">
           <Bot className="w-5 h-5 text-content-muted" />
           <div>
              <h3 className="text-sm font-bold text-content uppercase tracking-widest">Synthèse Analytique IA</h3>
           </div>
        </div>
        <div className="flex items-center gap-1.5 px-3 py-1 bg-surface rounded-full border border-border">
           <Terminal className="w-3 h-3 text-content-muted" />
           <span className="text-[10px] font-mono font-bold text-content-muted uppercase tracking-widest">{providerLabel}</span>
        </div>
      </div>

      {/* Content Body */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {sections.map((section, i) => (
          <div key={i}>
            {section.title && (
              <div className="flex items-center gap-2 mb-1.5">
                <ShieldAlert className="w-3.5 h-3.5 text-content-muted shrink-0" />
                <span className={`text-[11px] font-bold uppercase tracking-widest ${SECTION_COLORS[section.title] || 'text-content-muted'}`}>
                  {section.title}
                </span>
              </div>
            )}
            {section.content && (
              <p className="text-base text-content leading-relaxed whitespace-pre-wrap pl-6">
                {section.content}
              </p>
            )}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="mt-5 pt-4 border-t border-border flex items-center justify-between">
         <div className="flex gap-1">
            <motion.div animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1.5 }} className="w-1.5 h-1.5 rounded-full bg-content-muted" />
            <motion.div animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.2 }} className="w-1.5 h-1.5 rounded-full bg-content-muted" />
            <motion.div animate={{ opacity: [0.2, 1, 0.2] }} transition={{ repeat: Infinity, duration: 1.5, delay: 0.4 }} className="w-1.5 h-1.5 rounded-full bg-content-muted" />
         </div>
         <div className="flex items-center gap-2 text-primary">
            <Sparkles className="w-4 h-4" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-primary">Analyse certifiée</span>
         </div>
      </div>
    </motion.div>
  );
});

AgentReport.displayName = 'AgentReport';
export default AgentReport;
