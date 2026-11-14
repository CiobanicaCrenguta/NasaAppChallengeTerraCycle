import Svg, { Path, Circle, Rect, Line, Polyline } from 'react-native-svg';
import { colors } from '../theme';

export type IconName = 'mic' | 'chevron' | 'back' | 'speaker' | 'chat' | 'map' | 'check' | 'x' | 'clock' | 'plus' | 'send' | 'chart';

export function Icon({ name, size = 24, color = colors.ink, stroke = 2 }: { name: IconName; size?: number; color?: string; stroke?: number }) {
  const p = { stroke: color, strokeWidth: stroke, fill: 'none', strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {name === 'mic' && (<><Rect x={9} y={3} width={6} height={11} rx={3} {...p} /><Path d="M5 11a7 7 0 0 0 14 0M12 18v3" {...p} /></>)}
      {name === 'chevron' && <Polyline points="9 6 15 12 9 18" {...p} />}
      {name === 'back' && <Polyline points="15 6 9 12 15 18" {...p} />}
      {name === 'speaker' && (<><Path d="M4 9h4l5-4v14l-5-4H4z" {...p} /><Path d="M17 9a4 4 0 0 1 0 6" {...p} /></>)}
      {name === 'chat' && <Path d="M4 20l1.5-4A8 8 0 1 1 9 19z" {...p} />}
      {name === 'map' && (<><Path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" {...p} /><Line x1={9} y1={4} x2={9} y2={18} {...p} /><Line x1={15} y1={6} x2={15} y2={20} {...p} /></>)}
      {name === 'check' && <Polyline points="5 12 10 17 19 7" {...p} />}
      {name === 'x' && <Path d="M6 6l12 12M18 6L6 18" {...p} />}
      {name === 'clock' && (<><Circle cx={12} cy={12} r={9} {...p} /><Polyline points="12 7 12 12 15.5 14" {...p} /></>)}
      {name === 'plus' && <Path d="M12 5v14M5 12h14" {...p} />}
      {name === 'chart' && <Path d="M4 20V10M10 20V4M16 20v-7M21 20H3" {...p} />}
      {name === 'send' && <Path d="M12 19V5M6 11l6-6 6 6" {...p} />}
    </Svg>
  );
}
