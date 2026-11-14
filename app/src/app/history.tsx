import { Pressable, ScrollView, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useConversation } from '@/conversation';
import { useLang } from '@/i18n';
import { IconButton, StateView } from '@/components/ui';
import { colors, size, type } from '@/theme';

export default function HistoryScreen() {
  const router = useRouter();
  const { t, lang } = useLang();
  const { history, current, open } = useConversation();
  const list = current.messages.length ? [current, ...history] : history;
  const day = (ms: number) => new Date(ms).toLocaleDateString(lang === 'ro' ? 'ro-RO' : 'en-GB', { day: 'numeric', month: 'long' });

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bone }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: size.gutter - 8, height: 52, gap: 4 }}>
        <IconButton icon="back" label={t.back} onPress={() => router.back()} />
        <Text style={type.h2}>{t.history}</Text>
      </View>
      {list.length === 0 ? (
        <StateView kind="empty" text={t.noHistory} />
      ) : (
        <ScrollView contentContainerStyle={{ paddingHorizontal: size.gutter, paddingBottom: 24 }}>
          {list.map((c, i) => {
            const q = c.messages.find((m) => m.role === 'user');
            const a = [...c.messages].reverse().find((m) => m.role === 'assistant');
            return (
              <Pressable key={c.id} accessibilityRole="button" onPress={() => { open(c.id); router.back(); }}
                style={({ pressed }) => ({ paddingVertical: 14, borderTopWidth: i ? 1 : 0, borderColor: colors.line, gap: 2, opacity: pressed ? 0.6 : 1 })}>
                <Text style={type.label}>{day(c.startedAt)}</Text>
                <Text style={type.title} numberOfLines={1}>{q?.text}</Text>
                {a && <Text style={[type.body, { color: colors.muted }]} numberOfLines={1}>{a.text}</Text>}
              </Pressable>
            );
          })}
        </ScrollView>
      )}
    </SafeAreaView>
  );
}
