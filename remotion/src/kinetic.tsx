/** Entrada animada de texto (modo frase). Portado y recortado de content-studio
 * kinetic.tsx - solo el modo 'phrase' que usa Elenco (hook/CTA). */
import React from 'react';
import { spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { SPRINGS, type Energy } from './effects';

type Tok = { text: string; accent: boolean };

const parseAccent = (text: string): Tok[] =>
  text
    .split(/(\*[^*]+\*)/)
    .filter(Boolean)
    .map((s) =>
      s.startsWith('*') && s.endsWith('*') ? { text: s.slice(1, -1), accent: true } : { text: s, accent: false },
    );

export const KineticPhrase: React.FC<{
  text: string;
  from: number;
  energy: Energy;
  accent?: string;
  blur?: number;
}> = ({ text, from, energy, accent, blur = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = frame < from ? 0 : spring({ frame: frame - from, fps, config: SPRINGS[energy] });
  const dy = 24 * (1 - p);
  const bl = blur * Math.max(1 - p, 0);
  return (
    <span
      style={{
        display: 'inline-block',
        opacity: Math.min(p, 1),
        transform: `translateY(${dy}px)`,
        filter: bl > 0.1 ? `blur(${bl}px)` : undefined,
      }}
    >
      {parseAccent(text).map((t, i) => (
        <span key={i} style={t.accent ? { color: accent } : undefined}>
          {t.text}
        </span>
      ))}
    </span>
  );
};
