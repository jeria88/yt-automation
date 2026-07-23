/** elenco — el director nuevo de ReyPirataChaman: el guion transita entre MAS
 * DE UN vehiculo/personaje real narrando, sincronizado al audio real de Franco
 * (no a la formula de palabras/segundo que usan el resto de directores de
 * content-studio). Cada segmento del storyboard (Fase 3) trae su propio
 * vehiculo con crossfade o corte entre ellos.
 *
 * v2 (feedback Franco tras ver los primeros 2 publicados): fondo liso sin
 * vida, sin subtitulos, sin nada que sostenga la atencion cada pocos
 * segundos. Se agrega: fondo con movimiento propio (gradiente que respira),
 * subtitulos karaoke con timestamps reales de whisper, y un flash/pulso en
 * cada corte de segmento del transcript (no arbitrario - sigue el ritmo real
 * del habla, no un timer fijo). */
import React from 'react';
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { loadFont as loadGrotesk } from '@remotion/google-fonts/SpaceGrotesk';
import { fadeWindow, flash } from '../effects';
import { KineticPhrase } from '../kinetic';

const { fontFamily: grotesk } = loadGrotesk();

export type ElencoSegment = {
  start: number; // segundos, real (whisper)
  end: number;
  vehiculoArt?: string; // path/url del cutout PNG - sin arte, el segmento queda solo con el fondo
  transitionIn: 'cut' | 'xfade';
};

export type TranscriptWord = { word: string; start: number; end: number };
export type TranscriptSegment = { start: number; end: number; text: string; words: TranscriptWord[] };

export type ElencoProps = {
  texts: { hook: string; cta: string };
  tokens: { jade: string; cream: string; dark: string };
  domain: string;
  narrationAudio: string;
  segments: ElencoSegment[];
  durationSeconds: number;
  transcript?: TranscriptSegment[];
};

export const resolveSrc = (src: string) => (src.startsWith('http') ? src : staticFile(src));

const TextBlock: React.FC<{ children: React.ReactNode; size: number; y: number; opacity?: number }> = ({
  children, size, y, opacity = 1,
}) => (
  <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: '0 72px', top: `${(y - 0.5) * 100}%` }}>
    <AbsoluteFill
      style={{
        background: 'linear-gradient(180deg, rgba(0,0,0,0) 25%, rgba(0,0,0,0.42) 42%, rgba(0,0,0,0.42) 58%, rgba(0,0,0,0) 75%)',
        opacity,
      }}
    />
    <div
      style={{
        fontFamily: grotesk, fontSize: size, fontWeight: 800, lineHeight: 1.15,
        letterSpacing: '-0.02em', color: '#F0E8DC', textAlign: 'center', maxWidth: 936, opacity,
        textShadow: '0 2px 10px rgba(0,0,0,0.9), 0 0 40px rgba(0,0,0,0.7)',
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);

/** Fondo con vida propia: gradiente radial que se desplaza lento (seno/coseno,
 * ciclos 28-45s, nunca ligado a scroll) entre el color base y un tinte jade
 * sutil - reemplaza el backgroundColor plano que se sentia "muerto". */
const AnimatedBackground: React.FC<{ tokens: ElencoProps['tokens'] }> = ({ tokens }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const px = 50 + Math.sin((t / 28) * 2 * Math.PI) * 18;
  const py = 45 + Math.cos((t / 37) * 2 * Math.PI) * 22;
  const glow = 0.10 + 0.05 * (1 + Math.sin((t / 19) * 2 * Math.PI)) / 2;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: tokens.dark,
        backgroundImage: `radial-gradient(circle at ${px}% ${py}%, ${tokens.jade}${Math.round(glow * 255).toString(16).padStart(2, '0')} 0%, ${tokens.dark} 60%)`,
      }}
    />
  );
};

/** Capa de personaje: bottom-anchored, drift lento seno/coseno (nunca ligado a
 * scroll, ciclos 25-40s). Crossfade entre segmentos si transitionIn='xfade'. */
const VehicleSegment: React.FC<{ art?: string; tokens: ElencoProps['tokens']; xfadeFrames: number }> = ({
  art, xfadeFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!art) return null;
  const t = frame / fps;
  const dx = Math.sin((t / 30) * 2 * Math.PI) * 22;
  const dy = Math.cos((t / 37) * 2 * Math.PI) * 16;
  const sc = 1 + Math.sin((t / 41) * 2 * Math.PI) * 0.03;
  const opacity = xfadeFrames > 0
    ? interpolate(frame, [0, xfadeFrames], [0, 1], { extrapolateRight: 'clamp' })
    : 1;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <Img
        src={resolveSrc(art)}
        style={{
          position: 'absolute', bottom: 0, right: '-4%', height: '88%', maxWidth: '92%',
          objectFit: 'contain', objectPosition: 'bottom right', opacity,
          transform: `translate(${dx}px, ${dy}px) scale(${sc})`,
        }}
      />
    </AbsoluteFill>
  );
};

/** Subtitulos karaoke: timestamps REALES de whisper (Fase 3), no stagger
 * sintetico - la palabra activa se resalta segun su word.start/end real. */
const CaptionTrack: React.FC<{ segments: TranscriptSegment[]; color: string; accent: string }> = ({
  segments, color, accent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const seg = segments.find((s) => t >= s.start && t < s.end);
  if (!seg || !seg.words || seg.words.length === 0) return null;
  return (
    <TextBlock size={58} y={0.84}>
      <span>
        {seg.words.map((w, i) => (
          <span key={i} style={{ color: t >= w.start ? accent : color, opacity: t >= w.start ? 1 : 0.55 }}>
            {w.word}{i < seg.words.length - 1 ? ' ' : ''}
          </span>
        ))}
      </span>
    </TextBlock>
  );
};

export const Elenco: React.FC<ElencoProps> = (props) => {
  const { texts, tokens, domain, narrationAudio, segments, transcript = [] } = props;
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const ctaSeconds = 3;
  const ctaStart = durationInFrames - Math.round(ctaSeconds * fps);
  const hookEnd = Math.min(48, Math.round(ctaStart * 0.15));

  return (
    <AbsoluteFill style={{ backgroundColor: tokens.dark }}>
      <Audio src={resolveSrc(narrationAudio)} />
      <AnimatedBackground tokens={tokens} />

      {segments.map((seg, i) => {
        const from = Math.round(seg.start * fps);
        const to = Math.min(Math.round(seg.end * fps), ctaStart);
        if (to <= from) return null;
        const xfade = seg.transitionIn === 'xfade' && i > 0 ? 8 : 0;
        return (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            <VehicleSegment art={seg.vehiculoArt} tokens={tokens} xfadeFrames={xfade} />
          </Sequence>
        );
      })}

      {/* Flash sutil en cada corte de frase real del audio - sostiene la
          atencion cada pocos segundos siguiendo el ritmo del habla, no un
          timer arbitrario. */}
      {transcript.slice(1).map((seg, i) => {
        const at = Math.round(seg.start * fps);
        if (at >= ctaStart) return null;
        const op = flash(frame, at, 0.22, 5);
        return op > 0.01 ? <AbsoluteFill key={i} style={{ backgroundColor: '#fff', opacity: op }} /> : null;
      })}

      {frame < ctaStart && transcript.length > 0 && (
        <CaptionTrack segments={transcript} color={tokens.cream} accent={tokens.jade} />
      )}

      {frame < hookEnd && texts.hook && (
        <TextBlock size={72} y={0.16} opacity={fadeWindow(frame, 0, hookEnd, 1, 8)}>
          <KineticPhrase text={texts.hook} from={0} energy="soft" accent={tokens.jade} blur={8} />
        </TextBlock>
      )}

      {frame >= ctaStart && (
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32 }}>
            <div style={{ fontFamily: grotesk, fontSize: 64, fontWeight: 800, color: tokens.cream, textAlign: 'center', maxWidth: 900 }}>
              {texts.cta}
            </div>
            <div style={{ fontFamily: grotesk, fontSize: 80, fontWeight: 900, color: tokens.jade }}>{domain}</div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
