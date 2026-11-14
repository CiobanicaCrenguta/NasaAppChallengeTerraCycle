import Svg, { Polygon as SvgPolygon } from 'react-native-svg';
import { colors } from '../theme';
import type { Health, Polygon } from '../types';

/** The field's real outline, drawn flat (north up). */
export function FieldShape({ geometry, health = 'good', size = 44 }: { geometry: Polygon; health?: Health; size?: number }) {
  const ring = geometry.coordinates[0];
  const cos = Math.cos((ring[0][1] * Math.PI) / 180);
  const pts = ring.map(([lon, lat]) => [lon * cos, -lat]);
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const minX = Math.min(...xs), minY = Math.min(...ys);
  const w = Math.max(...xs) - minX || 1, h = Math.max(...ys) - minY || 1;
  const pad = 3, s = (size - 2 * pad) / Math.max(w, h);
  const ox = (size - w * s) / 2, oy = (size - h * s) / 2;
  const points = pts.map(([x, y]) => `${(ox + (x - minX) * s).toFixed(1)},${(oy + (y - minY) * s).toFixed(1)}`).join(' ');
  const fill = health === 'good' ? colors.greenSoft : health === 'unknown' ? colors.sand : colors.orangeSoft;
  const stroke = health === 'good' ? colors.green : health === 'unknown' ? colors.muted : colors.orange;
  return (
    <Svg width={size} height={size}>
      <SvgPolygon points={points} fill={fill} stroke={stroke} strokeWidth={1.5} strokeLinejoin="round" />
    </Svg>
  );
}
