import { useState } from 'react';
import { Text, View } from 'react-native';
import Svg, { Circle, G, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';
import { colors, fonts } from '../theme';
import type { Series } from '../types';

function useWidth() {
  const [w, setW] = useState(0);
  return { w, onLayout: (e: { nativeEvent: { layout: { width: number } } }) => setW(e.nativeEvent.layout.width) };
}

/** This year (solid) against the usual level (dashed). */
export function LineChart({ s }: { s: Series }) {
  const { w, onLayout } = useWidth();
  const h = 170, top = 12, bottom = 132;
  const all = [...s.values, ...(s.usual ?? [])];
  const hiV = Math.max(...all), loV = Math.min(...all);
  const max = hiV + (hiV - loV) * 0.12, min = Math.max(0, loV - (hiV - loV) * 0.35);
  const x = (i: number) => 8 + (i * (w - 16)) / (s.labels.length - 1);
  const y = (v: number) => bottom - ((v - min) / (max - min || 1)) * (bottom - top);
  const line = (vs: number[]) => vs.map((v, i) => `${x(i)},${y(v)}`).join(' ');
  const hi = s.highlightIndex;
  return (
    <View onLayout={onLayout}>
      {(s.valuesLabel || s.usualLabel) && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', columnGap: 18, rowGap: 4, marginBottom: 4 }}>
          {s.valuesLabel && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={{ width: 22, height: 3, borderRadius: 2, backgroundColor: colors.green }} />
              <Text style={{ fontFamily: fonts.bold, fontSize: 13, color: colors.ink }}>{s.valuesLabel}</Text>
            </View>
          )}
          {s.usual && s.usualLabel && (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={{ flexDirection: 'row', gap: 4 }}>
                <View style={{ width: 6, height: 2, backgroundColor: colors.muted }} />
                <View style={{ width: 6, height: 2, backgroundColor: colors.muted }} />
                <View style={{ width: 6, height: 2, backgroundColor: colors.muted }} />
              </View>
              <Text style={{ fontFamily: fonts.bold, fontSize: 13, color: colors.muted }}>{s.usualLabel}</Text>
            </View>
          )}
        </View>
      )}
      {w > 0 && (
        <Svg width={w} height={h}>
          <Line x1={0} x2={w} y1={bottom} y2={bottom} stroke={colors.line} strokeWidth={1} />
          {s.usual && <Polyline points={line(s.usual)} fill="none" stroke={colors.muted} strokeWidth={2} strokeDasharray="6,5" />}
          <Polyline points={line(s.values)} fill="none" stroke={colors.green} strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
          {hi !== undefined && <Circle cx={x(hi)} cy={y(s.values[hi])} r={6} fill={colors.orange} stroke={colors.paper} strokeWidth={2} />}
          {s.labels.map((m, i) => (
            <SvgText key={i} x={x(i)} y={h - 8} fontFamily={fonts.semibold} fontSize={13} fill={colors.muted} textAnchor={i === 0 ? 'start' : i === s.labels.length - 1 ? 'end' : 'middle'}>{m}</SvgText>
          ))}
        </Svg>
      )}
    </View>
  );
}

export function BarChart({ s }: { s: Series }) {
  const { w, onLayout } = useWidth();
  const h = 160, top = 22, bottom = 128;
  const max = Math.max(...s.values);
  const n = s.values.length, gap = 6;
  const bw = (w - gap * (n - 1)) / n;
  return (
    <View onLayout={onLayout} style={{ height: h }}>
      {w > 0 && (
        <Svg width={w} height={h}>
          {s.values.map((v, i) => {
            const bh = Math.max(4, (v / max) * (bottom - top));
            const bx = i * (bw + gap);
            const hi = i === s.highlightIndex;
            return (
              <G key={i}>
                <Rect x={bx} y={bottom - bh} width={bw} height={bh} rx={4} fill={hi ? colors.orange : colors.blue} />
                <SvgText x={bx + bw / 2} y={bottom - bh - 6} fontFamily={fonts.bold} fontSize={13} fill={colors.ink} textAnchor="middle">{v}</SvgText>
                <SvgText x={bx + bw / 2} y={h - 8} fontFamily={fonts.semibold} fontSize={13} fill={colors.muted} textAnchor="middle">{s.labels[i]}</SvgText>
              </G>
            );
          })}
        </Svg>
      )}
    </View>
  );
}
