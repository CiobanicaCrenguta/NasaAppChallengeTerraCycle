import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useConversation } from '@/conversation';
import { useField, useFields } from '@/hooks';
import { useLang } from '@/i18n';
import { FieldShape } from '@/components/FieldShape';
import { LeafletMap } from '@/components/LeafletMap';
import { Button, StateView } from '@/components/ui';
import { colors, fonts, size, type } from '@/theme';
import type { FieldFeature } from '@/types';

function Details({ f }: { f: FieldFeature }) {
  const { t } = useLang();
  const router = useRouter();
  const { ask: askNew } = useConversation();
  const summary = useField(f.properties.id);
  const ask = (text: string, intent: 'rotation' | 'health') => {
    askNew(text, { fieldId: f.properties.id, intent });
    router.navigate('/');
  };
  return (
    <View style={{ gap: 12, paddingBottom: 14 }}>
      {summary.data && (
        <View style={{ gap: 6 }}>
          <Text style={type.label}>{t.grewHere}</Text>
          <View style={{ flexDirection: 'row', gap: 6 }}>
            {summary.data.history.map((h) => (
              <View key={h.year} style={{ flex: 1, backgroundColor: colors.sand, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 10 }}>
                <Text style={type.label}>{h.year}</Text>
                <Text style={{ fontFamily: fonts.bold, fontSize: 14, lineHeight: 18, color: colors.ink }} numberOfLines={2}>{h.crop}</Text>
              </View>
            ))}
          </View>
        </View>
      )}
      <View style={{ flexDirection: 'row', gap: 8 }}>
        <Button label={t.planField} variant="primary" style={{ flex: 1.2, paddingHorizontal: 10 }} onPress={() => ask(t.planFieldText(f.properties.name), 'rotation')} />
        <Button label={t.askField} style={{ flex: 1, paddingHorizontal: 10 }} onPress={() => ask(t.askFieldText(f.properties.name), 'health')} />
      </View>
    </View>
  );
}

export default function LandScreen() {
  const { t } = useLang();
  const fields = useFields();
  const [selected, setSelected] = useState<string | undefined>();
  const feats = fields.data?.features ?? [];

  if (!fields.data) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bone, justifyContent: 'center' }}>
        {fields.isError
          ? <StateView kind="error" text={t.fieldsError} action={t.retry} onAction={() => fields.refetch()} />
          : <StateView kind="loading" text={t.fieldsLoading} />}
      </SafeAreaView>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: colors.bone }}>
      <View style={{ flex: 1 }}>
        <LeafletMap fields={fields.data} selectedId={selected} onSelect={setSelected} />
      </View>
      <View style={{ maxHeight: '52%', backgroundColor: colors.bone, borderTopLeftRadius: 22, borderTopRightRadius: 22, marginTop: -22 }}>
        <ScrollView contentContainerStyle={{ paddingHorizontal: size.gutter, paddingTop: 8, paddingBottom: 8 }}>
          {feats.map((f, i) => {
            const p = f.properties;
            const open = p.id === selected;
            return (
              <View key={p.id} style={{ borderTopWidth: i ? 1 : 0, borderColor: colors.line }}>
                <Pressable accessibilityRole="button" accessibilityState={{ expanded: open }} onPress={() => setSelected(open ? undefined : p.id)}
                  style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 14, minHeight: 68, opacity: pressed ? 0.6 : 1 })}>
                  <FieldShape geometry={f.geometry} health={p.health} />
                  <View style={{ flex: 1 }}>
                    <Text style={type.title}>{p.name}</Text>
                    <Text style={[type.body, { fontSize: 14, color: colors.muted }]}>{p.crop} · {p.ha.toFixed(p.ha < 1 ? 2 : 1)} ha</Text>
                  </View>
                  <Text style={{ fontFamily: fonts.bold, fontSize: 13, color: p.health === 'good' ? colors.green : p.health === 'unknown' ? colors.muted : colors.orange }}>{p.healthLabel}</Text>
                </Pressable>
                {open && <Details f={f} />}
              </View>
            );
          })}
        </ScrollView>
      </View>
    </View>
  );
}
