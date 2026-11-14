import { Text, View } from 'react-native';
import { colors, fonts, type } from '../theme';
import type { Card as CardT } from '../types';
import { BarChart, LineChart } from './charts';
import { Icon } from './Icon';
import { Card, SourceLine } from './ui';

function Row({ icon, color, text }: { icon: 'check' | 'x'; color: string; text: string }) {
  return (
    <View style={{ flexDirection: 'row', gap: 10, alignItems: 'flex-start' }}>
      <View style={{ marginTop: 2 }}><Icon name={icon} size={18} color={color} stroke={2.4} /></View>
      <Text style={[type.body, { flex: 1 }]}>{text}</Text>
    </View>
  );
}

export function AnswerCard({ card }: { card: CardT }) {
  if (card.type === 'rotation') {
    return (
      <Card>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          {card.plan.map((p, i) => (
            <View key={p.year} style={{ flex: 1, borderRadius: 12, paddingVertical: 10, paddingHorizontal: 10, backgroundColor: i === 0 ? colors.green : colors.sand, gap: 2 }}>
              <Text style={{ fontFamily: fonts.semibold, fontSize: 13, color: i === 0 ? colors.greenSoft : colors.muted }}>{p.year}</Text>
              <Text style={{ fontFamily: fonts.bold, fontSize: 15, lineHeight: 19, color: i === 0 ? colors.paper : colors.ink }}>{p.crop}</Text>
            </View>
          ))}
        </View>
        {card.reasons.map((r) => <Row key={r} icon="check" color={colors.green} text={r} />)}
        {card.avoid && <Row icon="x" color={colors.red} text={card.avoid} />}
      </Card>
    );
  }
  if (card.type === 'chart') {
    const s = card.series;
    return (
      <Card>
        <Text style={type.title}>{s.title}</Text>
        {s.kind === 'line' ? <LineChart s={s} /> : <BarChart s={s} />}
        <SourceLine source={s.source} />
      </Card>
    );
  }
  return (
    <Card>
      {card.items.map((t) => <Row key={t} icon="x" color={colors.muted} text={t} />)}
    </Card>
  );
}
