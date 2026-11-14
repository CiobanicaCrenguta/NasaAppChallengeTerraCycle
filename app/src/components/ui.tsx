import { ReactNode } from 'react';
import { ActivityIndicator, Pressable, StyleProp, Text, View, ViewStyle } from 'react-native';
import { colors, fonts, size, type } from '../theme';
import { Icon, IconName } from './Icon';
import type { Source } from '../types';

/* ---------- Button ---------- */
export function Button({ label, onPress, variant = 'secondary', icon, style, disabled }: {
  label: string; onPress: () => void; variant?: 'primary' | 'secondary'; icon?: IconName; style?: StyleProp<ViewStyle>; disabled?: boolean;
}) {
  const primary = variant === 'primary';
  return (
    <Pressable
      accessibilityRole="button" disabled={disabled} onPress={onPress}
      style={({ pressed }) => [{
        minHeight: size.button, borderRadius: 999, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
        backgroundColor: primary ? colors.green : colors.paper, borderWidth: primary ? 0 : 1.5, borderColor: colors.edge, opacity: pressed || disabled ? 0.6 : 1,
      }, style]}
    >
      {icon && <Icon name={icon} size={20} color={primary ? colors.paper : colors.ink} />}
      <Text style={[type.button, { color: primary ? colors.paper : colors.ink }]}>{label}</Text>
    </Pressable>
  );
}

/* ---------- IconButton ---------- */
export function IconButton({ icon, label, onPress, filled, sizePx = size.touch, color }: {
  icon: IconName; label: string; onPress: () => void; filled?: boolean; sizePx?: number; color?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button" accessibilityLabel={label} onPress={onPress} hitSlop={6}
      style={({ pressed }) => ({
        width: sizePx, height: sizePx, borderRadius: sizePx / 2, alignItems: 'center', justifyContent: 'center',
        backgroundColor: filled ? colors.green : 'transparent', opacity: pressed ? 0.6 : 1,
      })}
    >
      <Icon name={icon} size={sizePx > 52 ? 28 : 22} color={color ?? (filled ? colors.paper : colors.ink)} />
    </Pressable>
  );
}

/* ---------- Chip: a tap answer ---------- */
export function Chip({ label, onPress, disabled, selected }: { label: string; onPress: () => void; disabled?: boolean; selected?: boolean }) {
  return (
    <Pressable
      accessibilityRole="button" disabled={disabled} onPress={onPress}
      style={({ pressed }) => ({
        minHeight: size.touch, paddingHorizontal: 18, borderRadius: 999, justifyContent: 'center',
        backgroundColor: selected ? colors.green : pressed ? colors.greenSoft : colors.paper, borderWidth: 1.5, borderColor: colors.green, opacity: disabled ? 0.5 : 1,
      })}
    >
      <Text style={{ fontFamily: fonts.bold, fontSize: 16, color: selected ? colors.paper : colors.green }}>{label}</Text>
    </Pressable>
  );
}

/* ---------- Card ---------- */
export function Card({ children, style }: { children: ReactNode; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[{ backgroundColor: colors.paper, borderWidth: 1.5, borderColor: colors.edge, borderRadius: size.radius, padding: 16, gap: 12 }, style]}>
      {children}
    </View>
  );
}

/* ---------- SourceLine ---------- */
export function SourceLine({ source }: { source: Source }) {
  return <Text style={type.label}>{source.name} · {source.detail}</Text>;
}

/* ---------- States: always a sentence, never a bare spinner ---------- */
export function StateView({ kind, text, action, onAction }: { kind: 'loading' | 'error' | 'empty'; text: string; action?: string; onAction?: () => void }) {
  return (
    <View style={{ alignItems: 'center', gap: 12, padding: 24 }}>
      {kind === 'loading' && <ActivityIndicator color={colors.green} />}
      <Text style={[type.body, { textAlign: 'center', color: colors.muted }]}>{text}</Text>
      {action && onAction && <Button label={action} onPress={onAction} />}
    </View>
  );
}
