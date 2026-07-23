/** elenco — el director nuevo de ReyPirataChaman: el guion transita entre MAS
 * DE UN vehiculo/personaje real narrando, sincronizado al audio real de Franco
 * (no a la formula de palabras/segundo que usan el resto de directores de
 * content-studio). Cada segmento del storyboard (Fase 3) trae su propio
 * vehiculo con crossfade o corte entre ellos.
 *
 * v3 (feedback Franco tras ver el video v2): la fuente (Space Grotesk) se
 * sentia muy cuadrada/corporativa -> Outfit (redondeada, mas calida). El
 * fondo abstracto (gradiente + flash) se veia mal -> reemplazado por broll
 * real alineado a la keyword del segmento. El personaje tapaba los
 * subtitulos (mismo bottom-anchored + scrim grande) -> mas chico,
 * reposicionado arriba del area de subtitulos, scrim de texto mas angosto.
 *
 * v4 (feedback Franco: los GIF de GIPHY traian texto/marca de agua ajenos
 * quemados en la imagen - verificado en vivo, uno era literalmente una
 * quote-card de Pinterest). GIPHY es un indice de memes/reacciones, no de
 * b-roll. Reemplazado por video stock real (Pexels/Pixabay, patron
 * adoptado de MoneyPrinterTurbo/ShortGPT - ver broll_gif.py), sin audio
 * propio y con loop corto (los clips de stock duran al menos 4s
 * garantizado por el backend, pero un segmento puede durar mas).
 *
 * v5 (feedback Franco, confirmado con Gemini: el retrato circular + globo
 * de cita en pantalla es contraproducente para viralizacion - forzaba a
 * elegir entre leer la cita o escuchar la narracion). Sacados
 * VehicleSegment y AuthorCard del todo. Los subtitulos karaoke
 * (CaptionTrack, ya existian) cubren el rol de "tipografia kinetica en
 * sync con la voz" sin agregar nada nuevo. El personaje real (vehiculo)
 * sigue existiendo en el storyboard/guion como referencia de tono/cita,
 * simplemente no se muestra - el gate de aprobacion de arte por Telegram
 * en render_worker.py se saca en consecuencia (no tiene proposito si
 * nada se renderiza). */
import React from 'react';
import { AbsoluteFill, Audio, Loop, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { loadFont } from '@remotion/google-fonts/Outfit';
import { fadeWindow } from '../effects';
import { KineticPhrase } from '../kinetic';

const { fontFamily: outfit } = loadFont();

export type ElencoSegment = {
  start: number; // segundos, real (whisper)
  end: number;
  vehiculoArt?: string; // path/url del cutout PNG - sin arte, el segmento queda solo con el fondo
  brollVideo?: string; // path/url del clip de stock de fondo para este segmento (Pexels/Pixabay) - opcional
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

// Ventana de loop conservadora: el backend garantiza >=4s por clip
// (MIN_DURATION_SECONDS en broll_gif.py), 3.5s deja margen sin arriesgar
// pedir un frame que no existe en clips justo en el limite.
const BROLL_LOOP_SECONDS = 3.5;

/** Fondo: video de stock real (Pexels/Pixabay) en loop corto, sin audio
 * propio, con overlay oscuro para legibilidad. Sin video para el segmento
 * -> queda el color base solo (nunca un gradiente/flash abstracto, eso fue
 * lo que se vio mal en v2). */
const BrollBackground: React.FC<{ video?: string; dark: string }> = ({ video, dark }) => {
  const { fps } = useVideoConfig();
  if (!video) return <AbsoluteFill style={{ backgroundColor: dark }} />;
  return (
    <AbsoluteFill style={{ backgroundColor: dark }}>
      <Loop durationInFrames={Math.round(BROLL_LOOP_SECONDS * fps)}>
        <OffthreadVideo src={resolveSrc(video)} muted style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      </Loop>
      <AbsoluteFill style={{ backgroundColor: dark, opacity: 0.72 }} />
    </AbsoluteFill>
  );
};

/** Grading de marca: unifica el tono de personaje (calido, rojo/naranja del
 * estilo shonen) + broll (colores random de GIPHY) bajo un mismo aura verde
 * mistica, igual al logo del canal (feedback Franco). mix-blend-mode:'color'
 * tine todo lo de abajo preservando el detalle de luminosidad - no tapa la
 * imagen, la "unifica". + vinieta oscura en los bordes (mistico/cinematico)
 * + pulso lento de intensidad del aura (seno, ciclo 32s, nunca ligado a
 * scroll, ver regla de motion del proyecto). */
const BrandGrade: React.FC<{ jade: string; dark: string }> = ({ jade, dark }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const pulse = 0.34 + 0.08 * (1 + Math.sin((t / 32) * 2 * Math.PI)) / 2;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <AbsoluteFill style={{ backgroundColor: jade, opacity: pulse, mixBlendMode: 'color' }} />
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse at 50% 45%, transparent 38%, ${dark}cc 100%)`,
        }}
      />
    </AbsoluteFill>
  );
};

/** Subtitulos karaoke: timestamps REALES de whisper (Fase 3), no stagger
 * sintetico - la palabra activa se resalta segun su word.start/end real. */
// feedback Franco: mostrar el parrafo whisper entero era demasiado texto en
// pantalla, confundia. Se corta en frases chicas (CAPTION_CHUNK palabras) y
// solo se muestra la que esta sonando ahora.
const CAPTION_CHUNK = 5;

const CaptionTrack: React.FC<{ segments: TranscriptSegment[]; color: string; accent: string }> = ({
  segments, color, accent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const seg = segments.find((s) => t >= s.start && t < s.end);
  if (!seg || !seg.words || seg.words.length === 0) return null;

  const chunks: TranscriptWord[][] = [];
  for (let i = 0; i < seg.words.length; i += CAPTION_CHUNK) chunks.push(seg.words.slice(i, i + CAPTION_CHUNK));
  const active = chunks.find((c) => t >= c[0].start && t < c[c.length - 1].end + 0.4) ?? chunks[chunks.length - 1];

  return (
    <TextBlock size={54} y={0.87} scrimSpread={14}>
      <span>
        {active.map((w, i) => (
          <span key={i} style={{ color: t >= w.start ? accent : color, opacity: t >= w.start ? 1 : 0.55 }}>
            {w.word}{i < active.length - 1 ? ' ' : ''}
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
            <BrollBackground video={seg.brollVideo} dark={tokens.dark} />
          </Sequence>
        );
      })}

      <BrandGrade jade={tokens.jade} dark={tokens.dark} />

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
