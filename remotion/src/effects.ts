/** Micro-efectos de frontera. Portado verbatim de content-studio (referencia,
 * sin dependencia en runtime). */
import { interpolate } from 'remotion';

const clamp = { extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const };

export const fadeWindow = (frame: number, from: number, to: number, fin = 8, fout = 8) =>
  interpolate(frame, [from, from + fin, to - fout, to], [0, 1, 1, 0], clamp);

/** Flash blanco de 1->len frames. Devuelve opacity del overlay blanco. */
export const flash = (frame: number, at: number, peak = 0.5, len = 4) =>
  frame < at ? 0 : interpolate(frame, [at, at + 1, at + len], [0, peak, 0], clamp);

export type Energy = 'snappy' | 'dry' | 'soft';
export const SPRINGS: Record<Energy, { damping: number; stiffness?: number }> = {
  snappy: { damping: 12, stiffness: 180 },
  dry: { damping: 200 },
  soft: { damping: 26, stiffness: 80 },
};
