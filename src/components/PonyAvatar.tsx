import { useEffect, useMemo, useRef } from 'react';
import lottie, { type AnimationItem } from 'lottie-web';
import dogAnimation from '../assets/lottie/pets/dog.json';
import foxAnimation from '../assets/lottie/pets/fox.json';
import horseAnimation from '../assets/lottie/pets/horse.json';
import pandaAnimation from '../assets/lottie/pets/panda.json';
import pigAnimation from '../assets/lottie/pets/pig.json';
import rabbitAnimation from '../assets/lottie/pets/rabbit.json';
import type { AgentStatus } from '../data/agents';

export type IdleVariant = 'sleeping' | 'coffee' | 'workout' | 'bathroom' | 'wandering';
export type PetTheme = 'horse' | 'pig' | 'dog' | 'rabbit' | 'panda' | 'fox';

type PonyAvatarProps = {
  status: AgentStatus;
  idleVariant: IdleVariant;
  petTheme: PetTheme;
};

const PET_ANIMATIONS: Record<PetTheme, object> = {
  horse: horseAnimation,
  pig: pigAnimation,
  dog: dogAnimation,
  rabbit: rabbitAnimation,
  panda: pandaAnimation,
  fox: foxAnimation,
};

export function PonyAvatar({ status, idleVariant, petTheme }: PonyAvatarProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const animationRef = useRef<AnimationItem | null>(null);

  const animationData = useMemo(() => {
    void status;
    void idleVariant;
    return PET_ANIMATIONS[petTheme];
  }, [status, idleVariant, petTheme]);

  useEffect(() => {
    if (!containerRef.current) return;

    animationRef.current?.destroy();
    animationRef.current = lottie.loadAnimation({
      container: containerRef.current,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      animationData,
      rendererSettings: {
        preserveAspectRatio: 'xMidYMid meet',
      },
    });

    return () => {
      animationRef.current?.destroy();
      animationRef.current = null;
    };
  }, [animationData]);

  return (
    <div className={`pony-avatar state-${status} idle-${idleVariant}`}>
      <div className="pony-lottie" ref={containerRef} />
    </div>
  );
}
