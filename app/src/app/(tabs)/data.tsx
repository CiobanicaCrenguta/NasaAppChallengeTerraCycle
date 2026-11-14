import { useState } from 'react';
import { ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useFields, useInsights } from '@/hooks';
import { useLang } from '@/i18n';
import { BarChart, LineChart } from '@/components/charts';
import { Card, Chip, SourceLine, StateView } from '@/components/ui';
import { colors, fonts, size, type } from '@/theme';
import type { Know, Scope } from '@/types';

const knowColor: Record<Know['id'], string> = { field: colors.green, area: colors.blue, you: colors.ink, blind: colors.muted };

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

/** The evidence behind the answers: each analysis is one plain sentence, then its chart. */
export default function DataScreen() {
  const { t } = useLang();
  const fields = useFields();
  const [fieldId, setFieldId] = useState<string | undefined>();
  const selected = fieldId ?? fields.data?.features[0]?.properties.id;
  const insights = useInsights(selected);

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: colors.bone }}>
      <ScrollView contentContainerStyle={{ padding: size.gutter, paddingBottom: 32, gap: 16 }}>
        <View style={{ gap: 4, marginBottom: 4 }}>
          <Text style={type.h1}>{t.dataTitle}</Text>
          {insights.data && <Text style={[type.body, { color: colors.muted }]}>{t.dataSub(insights.data.area)}</Text>}
        </View>

        {insights.isLoading && <StateView kind="loading" text={t.dataLoading} />}
        {insights.isError && <StateView kind="error" text={t.dataError} action={t.retry} onAction={() => insights.refetch()} />}

        {insights.data && (
          <Card style={{ gap: 16 }}>
            <Text style={type.h2}>{t.knowTitle}</Text>
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
          </Card>
        )}

        {insights.data?.cards.map((c) => (
          <Card key={c.id}>
            {c.perField && fields.data && (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
                {fields.data.features.map((f) => (
                  <Chip key={f.properties.id} label={f.properties.name} selected={f.properties.id === selected} onPress={() => setFieldId(f.properties.id)} />
                ))}
              </ScrollView>
            )}
            <ScopeTag scope={c.scope} />
            <Text style={[type.h2, { lineHeight: 28 }]}>{c.takeaway}</Text>
            <Text style={type.label}>{c.series.title}</Text>
            {c.series.kind === 'line' ? <LineChart s={c.series} /> : <BarChart s={c.series} />}
            <SourceLine source={c.series.source} />
          </Card>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}
