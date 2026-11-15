import { ReactNode, useState } from 'react';
import { LayoutAnimation, Platform, Pressable, ScrollView, Text, UIManager, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFields, useInsights } from '@/hooks';
import { useLang } from '@/i18n';
import { BarChart, LineChart } from '@/components/charts';
import { Icon, IconName } from '@/components/Icon';
import { Chip, SourceLine, StateView } from '@/components/ui';
import { colors, fonts, size, type } from '@/theme';
import type { Know, Scope } from '@/types';

if (Platform.OS === 'android') UIManager.setLayoutAnimationEnabledExperimental?.(true);

const knowColor: Record<Know['id'], string> = { field: colors.green, area: colors.blue, you: colors.ink, blind: colors.muted };
const cardIcon: Record<string, IconName> = { green: 'leaf', rain: 'drop', temp: 'sun', soil: 'layers' };

/** Says plainly whether a number was measured on the field or estimated for the wider area. */
function ScopeTag({ scope }: { scope: Scope }) {
  const { t } = useLang();
  const field = scope === 'field';
  return (
    <View style={{ alignSelf: 'flex-start', flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: field ? colors.greenSoft : colors.sand, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 }}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: field ? colors.green : colors.blue }} />
      <Text style={{ fontFamily: fonts.bold, fontSize: 13, color: colors.ink }}>{field ? t.scopeField : t.scopeArea}</Text>
    </View>
  );
}

/**
 * One story on the page. Closed: a pictogram, one large sentence and an arrow pointing down.
 * Tapped: it opens downwards to show the evidence, and the arrow points up.
 */
function Story({ icon, tint, headline, hint, open, onToggle, children }: {
  icon: IconName; tint: 'green' | 'blue' | 'ink'; headline: string; hint?: string; open: boolean; onToggle: () => void; children: ReactNode;
}) {
  const { t } = useLang();
  const color = tint === 'green' ? colors.green : tint === 'blue' ? colors.blue : colors.ink;
  const soft = tint === 'green' ? colors.greenSoft : colors.sand;
  return (
    <View style={{ backgroundColor: colors.paper, borderWidth: 1.5, borderColor: colors.edge, borderRadius: 22, overflow: 'hidden' }}>
      <Pressable
        accessibilityRole="button" accessibilityState={{ expanded: open }} accessibilityHint={open ? t.showLess : t.showMore}
        onPress={onToggle}
        style={({ pressed }) => ({ padding: 18, gap: 14, backgroundColor: pressed ? colors.bone : colors.paper })}
      >
        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <View style={{ width: 48, height: 48, borderRadius: 24, backgroundColor: soft, alignItems: 'center', justifyContent: 'center' }}>
            <Icon name={icon} size={26} color={color} stroke={2.2} />
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, height: 40, paddingLeft: 14, paddingRight: 10, borderRadius: 20, borderWidth: 1.5, borderColor: colors.edge, backgroundColor: open ? colors.ink : colors.paper }}>
            <Text style={{ fontFamily: fonts.bold, fontSize: 14, color: open ? colors.paper : colors.ink }}>{open ? t.showLess : t.showMore}</Text>
            <Icon name={open ? 'up' : 'down'} size={20} color={open ? colors.paper : colors.ink} stroke={2.4} />
          </View>
        </View>
        <Text style={{ fontFamily: fonts.title, fontSize: 27, lineHeight: 33, color: colors.ink }}>{headline}</Text>
        {hint && !open && <Text style={[type.body, { color: colors.muted }]}>{hint}</Text>}
      </Pressable>
      {open && (
        <View style={{ paddingHorizontal: 18, paddingBottom: 18, paddingTop: 16, gap: 12, borderTopWidth: 1, borderColor: colors.line }}>
          {children}
        </View>
      )}
    </View>
  );
}

/** The evidence behind the answers. Each story is one large sentence; tapping it opens the chart behind it. */
export default function DataScreen() {
  const { t } = useLang();
  const fields = useFields();
  const [fieldId, setFieldId] = useState<string | undefined>();
  const [open, setOpen] = useState<string | null>(null);
  const selected = fieldId ?? fields.data?.features[0]?.properties.id;
  const insights = useInsights(selected);
  const toggle = (id: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setOpen((now) => (now === id ? null : id));
  };

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: colors.bone }}>
      <ScrollView contentContainerStyle={{ padding: size.gutter, paddingBottom: 32, gap: 14 }}>
        <View style={{ gap: 6, marginTop: 8, marginBottom: 8 }}>
          <Text style={{ fontFamily: fonts.title, fontSize: 36, lineHeight: 42, color: colors.ink }}>{t.dataTitle}</Text>
          {insights.data && <Text style={[type.body, { fontSize: 17, color: colors.muted }]}>{t.dataSub(insights.data.area)}</Text>}
        </View>

        {insights.isLoading && <StateView kind="loading" text={t.dataLoading} />}
        {insights.isError && <StateView kind="error" text={t.dataError} action={t.retry} onAction={() => insights.refetch()} />}

        {insights.data?.cards.map((c) => (
          <Story key={c.id} icon={cardIcon[c.id] ?? 'chart'} tint={c.scope === 'field' ? 'green' : 'blue'} headline={c.takeaway}
            open={open === c.id} onToggle={() => toggle(c.id)}>
            {c.perField && fields.data && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
                {fields.data.features.map((f) => (
                  <Chip key={f.properties.id} label={f.properties.name} selected={f.properties.id === selected} onPress={() => setFieldId(f.properties.id)} />
                ))}
              </ScrollView>
            )}
            <ScopeTag scope={c.scope} />
            <Text style={type.label}>{c.series.title}</Text>
            {c.series.kind === 'line' ? <LineChart s={c.series} /> : <BarChart s={c.series} />}
            <SourceLine source={c.series.source} />
          </Story>
        ))}

        {insights.data && (
          <Story icon="info" tint="ink" headline={t.knowTitle} hint={t.knowHint} open={open === 'know'} onToggle={() => toggle('know')}>
            {insights.data.knows.map((k) => (
              <View key={k.id} style={{ gap: 4 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: knowColor[k.id] }} />
                  <Text style={type.title}>{k.title}</Text>
                </View>
                {k.items.map((item) => (
                  <Text key={item} style={[type.body, { paddingLeft: 18 }]}>{item}</Text>
                ))}
                {k.note && <Text style={[type.label, { paddingLeft: 18, marginTop: 2 }]}>{k.note}</Text>}
              </View>
            ))}
          </Story>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}
