/** elenco — el director nuevo de ReyPirataChaman: el guion transita entre MAS
 * DE UN vehiculo/personaje real narrando, sincronizado al audio real de Franco
 * (no a la formula de palabras/segundo que usan el resto de directores de
 * content-studio). Cada segmento del storyboard (Fase 3) trae su propio
 * vehiculo con crossfade o corte entre ellos.
 *
 * v3 (feedback Franco tras ver el video v2): la fuente (Space Grotesk) se
 * sentia muy cuadrada/corporativa -> Outfit (redondeada, mas calida). El
 * fondo abstracto (gradiente + flash) se veia mal -> reemplazado por broll
 * real (GIF de GIPHY, licenciado para reinsertar - no scraping de video con
 * riesgo de copyright) alineado a la keyword del segmento. El personaje
 * tapaba los subtitulos (mismo bottom-anchored + scrim grande) -> mas chico,
 * reposicionado arriba del area de subtitulos, scrim de texto mas angosto. */
import React from 'react';
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Gif } from '@remotion/gif';
import { loadFont } from '@remotion/google-fonts/Outfit';
import { fadeWindow } from '../effects';
import { KineticPhrase } from '../kinetic';

const { fontFamily: outfit } = loadFont();

export type ElencoSegment = {
  start: number; // segundos, real (whisper)
  end: number;
  vehiculoArt?: string; // path/url del cutout PNG - sin arte, el segmento queda solo con el fondo
  brollGif?: string; // path/url del GIF de fondo para este segmento (GIPHY) - opcional
  vehiculoName?: string; // nombre del autor/personaje, para el card de apoyo
  quote?: string; // cita del vehiculo relacionada al tema de este beat
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

const TextBlock: React.FC<{ children: React.ReactNode; size: number; y: number; opacity?: number; scrimSpread?: number }> = ({
  children, size, y, opacity = 1, scrimSpread = 22,
}) => (
  <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: '0 72px', top: `${(y - 0.5) * 100}%` }}>
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.55) ${50 - scrimSpread}%, rgba(0,0,0,0.55) ${50 + scrimSpread}%, rgba(0,0,0,0) 100%)`,
        opacity,
      }}
    />
    <div
      style={{
        fontFamily: outfit, fontSize: size, fontWeight: 700, lineHeight: 1.2,
        letterSpacing: '-0.01em', color: '#F0E8DC', textAlign: 'center', maxWidth: 936, opacity,
        textShadow: '0 2px 10px rgba(0,0,0,0.9), 0 0 40px rgba(0,0,0,0.7)',
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);

/** Fondo: GIF real (GIPHY) en loop suave, con overlay oscuro para legibilidad.
 * Sin GIF para el segmento -> queda el color base solo (nunca un gradiente/
 * flash abstracto, eso fue lo que se vio mal en v2). */
const BrollBackground: React.FC<{ gif?: string; dark: string }> = ({ gif, dark }) => {
  if (!gif) return <AbsoluteFill style={{ backgroundColor: dark }} />;
  return (
    <AbsoluteFill style={{ backgroundColor: dark }}>
      <Gif src={resolveSrc(gif)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} loopBehavior="loop" />
      <AbsoluteFill style={{ backgroundColor: dark, opacity: 0.5 }} />
    </AbsoluteFill>
  );
};

/** Capa de personaje: mas chico y arriba del area de subtitulos (antes 88%
 * bottom-anchored competia directo con el caption de abajo y quedaba tapado
 * por su scrim). Drift lento seno/coseno (nunca ligado a scroll, ciclos
 * 25-40s). Crossfade entre segmentos si transitionIn='xfade'. */
const VehicleSegment: React.FC<{ art?: string; xfadeFrames: number }> = ({ art, xfadeFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!art) return null;
  const t = frame / fps;
  const dx = Math.sin((t / 30) * 2 * Math.PI) * 18;
  const dy = Math.cos((t / 37) * 2 * Math.PI) * 12;
  const sc = 1 + Math.sin((t / 41) * 2 * Math.PI) * 0.03;
  const opacity = xfadeFrames > 0
    ? interpolate(frame, [0, xfadeFrames], [0, 1], { extrapolateRight: 'clamp' })
    : 1;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <Img
        src={resolveSrc(art)}
        style={{
          position: 'absolute', top: '8%', right: '2%', height: '52%', maxWidth: '80%',
          objectFit: 'contain', objectPosition: 'top right', opacity,
          transform: `translate(${dx}px, ${dy}px) scale(${sc})`,
          filter: 'drop-shadow(0 12px 28px rgba(0,0,0,0.55))',
        }}
      />
    </AbsoluteFill>
  );
};

/** Card de apoyo: nombre del autor/personaje + una cita suya relacionada al
 * tema del beat (feedback Franco). Vive a la izquierda, en el tercio medio -
 * no compite con el personaje (arriba-derecha) ni con los subtitulos (abajo). */
const AuthorCard: React.FC<{ name?: string; quote?: string; jade: string; cream: string; fadeInFrames: number }> = ({
  name, quote, jade, cream, fadeInFrames,
}) => {
  const frame = useCurrentFrame();
  if (!name) return null;
  const opacity = interpolate(frame, [0, fadeInFrames], [0, 1], { extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'flex-start', padding: '0 64px', top: '-6%' }}>
      <div style={{ maxWidth: 560, opacity, borderLeft: `4px solid ${jade}`, paddingLeft: 24 }}>
        {quote && (
          <div style={{
            fontFamily: outfit, fontSize: 34, fontWeight: 500, fontStyle: 'italic', color: cream,
            lineHeight: 1.35, marginBottom: 14, textShadow: '0 2px 12px rgba(0,0,0,0.85)',
          }}>
            "{quote}"
          </div>
        )}
        <div style={{ fontFamily: outfit, fontSize: 28, fontWeight: 800, color: jade, textShadow: '0 2px 10px rgba(0,0,0,0.85)' }}>
          — {name}
        </div>
      </div>
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
    <TextBlock size={54} y={0.87} scrimSpread={14}>
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

      {segments.map((seg, i) => {
        const from = Math.round(seg.start * fps);
        const to = Math.min(Math.round(seg.end * fps), ctaStart);
        if (to <= from) return null;
        return (
          <Sequence key={`bg-${i}`} from={from} durationInFrames={to - from}>
            <BrollBackground gif={seg.brollGif} dark={tokens.dark} />
          </Sequence>
        );
      })}

      {segments.map((seg, i) => {
        const from = Math.round(seg.start * fps);
        const to = Math.min(Math.round(seg.end * fps), ctaStart);
        if (to <= from) return null;
        const xfade = seg.transitionIn === 'xfade' && i > 0 ? 8 : 0;
        return (
          <Sequence key={`veh-${i}`} from={from} durationInFrames={to - from}>
            <VehicleSegment art={seg.vehiculoArt} xfadeFrames={xfade} />
          </Sequence>
        );
      })}

      {segments.map((seg, i) => {
        const from = Math.round(seg.start * fps);
        const to = Math.min(Math.round(seg.end * fps), ctaStart);
        if (to <= from) return null;
        return (
          <Sequence key={`author-${i}`} from={from} durationInFrames={to - from}>
            <AuthorCard name={seg.vehiculoName} quote={seg.quote} jade={tokens.jade} cream={tokens.cream} fadeInFrames={14} />
          </Sequence>
        );
      })}

      {frame < ctaStart && transcript.length > 0 && (
        <CaptionTrack segments={transcript} color={tokens.cream} accent={tokens.jade} />
      )}

      {frame < hookEnd && texts.hook && (
        <TextBlock size={68} y={0.16} opacity={fadeWindow(frame, 0, hookEnd, 1, 8)}>
          <KineticPhrase text={texts.hook} from={0} energy="soft" accent={tokens.jade} blur={8} />
        </TextBlock>
      )}

      {frame >= ctaStart && (
        <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', backgroundColor: tokens.dark }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32 }}>
            <div style={{ fontFamily: outfit, fontSize: 60, fontWeight: 700, color: tokens.cream, textAlign: 'center', maxWidth: 900 }}>
              {texts.cta}
            </div>
            <div style={{ fontFamily: outfit, fontSize: 76, fontWeight: 800, color: tokens.jade }}>{domain}</div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};
