import { motion } from 'framer-motion';

/**
 * @param {{value?: number | null}} props
 */
export default function ConfidenceArc({ value }) {
  const numeric = typeof value === 'number' ? Math.max(0, Math.min(value, 100)) : 0;
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (numeric / 100) * circumference;
  const color = numeric >= 90 ? '#34d399' : numeric >= 70 ? '#fbbf24' : '#fb7185';

  return (
    <div className="relative h-20 w-20">
      <svg viewBox="0 0 80 80" className="-rotate-90">
        <circle cx="40" cy="40" r={radius} fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="7" />
        <motion.circle
          cx="40"
          cy="40"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 0.9, ease: 'easeOut' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center font-mono text-xs font-bold text-clinic-bone">
        {typeof value === 'number' ? `${Math.round(numeric)}%` : 'FB'}
      </div>
    </div>
  );
}
