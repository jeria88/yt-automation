/** elenco — el director nuevo de ReyPirataChaman: el guion transita entre MAS
 * DE UN vehiculo/personaje real narrando, sincronizado al audio real de Franco
 * (no a la formula de palabras/segundo que usan el resto de directores de
 * content-studio). Cada segmento del storyboard (Fase 3) trae su propio
 * vehiculo con crossfade o corte entre ellos. */
import React from 'react';
import { AbsoluteFill, Audio, Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { loadFont as loadGrotesk } from '@remotion/google-fonts/SpaceGrotesk';
import { fadeWindow } from '../effects';
import { KineticPhrase } from '../kinetic';

const { fontFamily: grotesk } = loadGrotesk();

export type ElencoSegment = {
  start: number; // segundos, real (whisper)
  end: number;
  vehiculoArt?: string; // path/url del cutout PNG - sin arte, el segmento queda solo con el fondo
  transitionIn: 'cut' | 'xfade';
};

export type ElencoProps = {
  texts: { hook: string; cta: string };
  tokens: { jade: string; cream: string; dark: string };
  domain: string;
  narrationAudio: string;
  segments: ElencoSegment[];
  durationSeconds: number;
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

export const Elenco: React.FC<ElencoProps> = (props) => {
  const { texts, tokens, domain, narrationAudio, segments, durationSeconds } = props;
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
        const xfade = seg.transitionIn === 'xfade' && i > 0 ? 8 : 0;
        return (
          <Sequence key={i} from={from} durationInFrames={to - from}>
            <VehicleSegment art={seg.vehiculoArt} tokens={tokens} xfadeFrames={xfade} />
          </Sequence>
        );
      })}

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
