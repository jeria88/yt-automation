import React from 'react';
import { Composition } from 'remotion';
import { Elenco, type ElencoProps } from './directors/Elenco';

const FPS = 24;
const W = 1080;
const H = 1920;

const demoProps: ElencoProps = {
  texts: {
    hook: 'La realidad que ves afuera es solo un espejo.',
    cta: 'Suscribite para el viaje interior',
  },
  tokens: { jade: '#7ecfa8', cream: '#F0E8DC', dark: '#040810' },
  domain: 'ReyPirataChaman',
  narrationAudio: '',
  segments: [],
  durationSeconds: 15,
};

export const Root: React.FC = () => (
  <Composition
    id="elenco"
    component={Elenco}
    durationInFrames={Math.round(demoProps.durationSeconds * FPS)}
    fps={FPS}
    width={W}
    height={H}
    defaultProps={demoProps}
    calculateMetadata={async ({ props }) => ({
      durationInFrames: Math.round((props.durationSeconds || 15) * FPS),
    })}
  />
);
