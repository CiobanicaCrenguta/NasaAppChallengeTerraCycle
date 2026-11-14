import { useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Pressable, ScrollView, Text, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useConversation } from '@/conversation';
import { useFields, useMe, useOverview } from '@/hooks';
import { useLang } from '@/i18n';
import { AnswerCard } from '@/components/cards';
import { FieldShape } from '@/components/FieldShape';
import { Icon } from '@/components/Icon';
import { Button, Chip, IconButton } from '@/components/ui';
import { colors, fonts, size, type } from '@/theme';
import type { AssistantMessage, Overview } from '@/types';

function Answer({ m, live }: { m: AssistantMessage; live: boolean }) {
  const { reply, speak, pending } = useConversation();
  const { t } = useLang();
  const fields = useFields();
  const field = fields.data?.features.find((f) => f.properties.id === m.fieldId);
  return (
    <View style={{ gap: 12 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, minHeight: 32 }}>
        {field && <FieldShape geometry={field.geometry} health={field.properties.health} size={28} />}
        <Text style={[type.label, { flex: 1, fontSize: 14 }]}>{m.fieldName ?? ''}</Text>
        <IconButton icon="speaker" label={t.listen} onPress={() => speak(m)} sizePx={36} color={colors.muted} />
      </View>
      <Text style={type.answer}>{m.text}</Text>
      {m.detail && <Text style={[type.body, { fontSize: 17, lineHeight: 25 }]}>{m.detail}</Text>}
      {m.cards?.map((c, i) => <AnswerCard key={i} card={c} />)}
      {live && m.replies && (
        <View style={{ gap: 10, marginTop: 4 }}>
          {m.replies.prompt && <Text style={[type.title, { fontSize: 18 }]}>{m.replies.prompt}</Text>}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
            {m.replies.options.map((o) => <Chip key={o.value} label={o.label} disabled={pending} onPress={() => reply(m.replies!.id, o, m.fieldId)} />)}
          </View>
        </View>
      )}
      {live && m.links?.map((o) => (
        <Pressable key={o.value} accessibilityRole="button" disabled={pending} onPress={() => reply('next', o, m.fieldId)} hitSlop={8}
          style={({ pressed }) => ({ alignSelf: 'flex-start', minHeight: 44, justifyContent: 'center', opacity: pressed ? 0.5 : 1 })}>
          <Text style={{ fontFamily: fonts.bold, fontSize: 16, color: colors.green, textDecorationLine: 'underline' }}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

/** The short situation report shown when the app opens. */
function Home({ o }: { o: Overview }) {
  const router = useRouter();
  const { t } = useLang();
  const { ask } = useConversation();
  const fields = useFields();
  return (
    <View style={{ gap: 12 }}>
      {o.attention.length > 0 && (
        <View style={{ backgroundColor: colors.paper, borderWidth: 1.5, borderColor: colors.edge, borderRadius: size.radius, paddingHorizontal: 16 }}>
          {o.attention.map((a, i) => {
            const f = fields.data?.features.find((x) => x.properties.id === a.fieldId);
            return (
              <Pressable key={a.fieldId} accessibilityRole="button" onPress={() => ask(t.askFieldText(a.name), { fieldId: a.fieldId, intent: 'health' })}
                style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 64, borderTopWidth: i ? 1 : 0, borderColor: colors.line, opacity: pressed ? 0.5 : 1 })}>
                {f && <FieldShape geometry={f.geometry} health={f.properties.health} size={36} />}
                <View style={{ flex: 1 }}>
                  <Text style={type.title}>{a.name}</Text>
                  <Text style={{ fontFamily: fonts.bold, fontSize: 13, color: colors.orange }}>{a.label}</Text>
                </View>
                <Icon name="chevron" size={20} color={colors.ink} />
              </Pressable>
            );
          })}
        </View>
      )}
      <View style={{ flexDirection: 'row', gap: 12 }}>
        {o.stats.map((s) => (
          <Pressable key={s.id} accessibilityRole="button" onPress={() => router.navigate('/data')}
            style={({ pressed }) => ({ flex: 1, backgroundColor: colors.paper, borderWidth: 1.5, borderColor: colors.edge, borderRadius: size.radius, padding: 14, gap: 2, opacity: pressed ? 0.5 : 1 })}>
            <Text style={type.label}>{s.label}</Text>
            <Text style={{ fontFamily: fonts.title, fontSize: 26, color: colors.ink }}>{s.value}</Text>
            <Text style={{ fontFamily: fonts.bold, fontSize: 13, color: s.warn ? colors.orange : colors.green }}>{s.note}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export default function AskScreen() {
  const router = useRouter();
  const { t } = useLang();
  const me = useMe();
  const overview = useOverview();
  const { current, pending, failed, send, retry, startNew } = useConversation();
  const [text, setText] = useState('');
  const [hint, setHint] = useState(false);
  const input = useRef<React.ComponentRef<typeof TextInput>>(null);
  const scroll = useRef<React.ComponentRef<typeof ScrollView>>(null);
  const empty = current.messages.length === 0;

  useEffect(() => {
    const id = setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 80);
    return () => clearTimeout(id);
  }, [current.messages.length, pending]);

  const submit = () => {
    const q = text.trim();
    if (!q) return;
    setText('');
    setHint(false);
    send(q);
  };
  const lastId = current.messages[current.messages.length - 1]?.id;

  return (
    <SafeAreaView edges={['top']} style={{ flex: 1, backgroundColor: colors.bone }}>
      <KeyboardAvoidingView behavior="padding" style={{ flex: 1 }}>
        {/* header */}
        <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: size.gutter - 8, height: 52 }}>
          <IconButton icon="clock" label={t.history} onPress={() => router.push('/history')} />
          {!empty && <IconButton icon="plus" label={t.newQuestion} onPress={startNew} />}
        </View>

        <ScrollView ref={scroll} keyboardShouldPersistTaps="handled" contentContainerStyle={{ flexGrow: 1, paddingHorizontal: size.gutter, paddingBottom: 20, gap: 28 }}>
          {empty ? (
            <View style={{ flex: 1, justifyContent: 'center', gap: 22 }}>
              <View style={{ gap: 6 }}>
                {me.data && <Text style={[type.body, { fontSize: 18, color: colors.muted }]}>{t.hello(me.data.name)}</Text>}
                <Text style={[type.h1, { fontSize: 32, lineHeight: 39 }]}>{overview.data?.headline ?? t.prompt}</Text>
              </View>
              {overview.data && <Home o={overview.data} />}
              <View>
                <Text style={[type.label, { marginBottom: 2 }]}>{t.askMore}</Text>
                {t.suggestions.map((q, i) => (
                  <Pressable key={q} accessibilityRole="button" onPress={() => send(q)}
                    style={({ pressed }) => ({ minHeight: 56, flexDirection: 'row', alignItems: 'center', borderTopWidth: i ? 1 : 0, borderColor: colors.line, opacity: pressed ? 0.5 : 1 })}>
                    <Text style={[type.title, { flex: 1, fontFamily: fonts.semibold }]}>{q}</Text>
                    <Icon name="chevron" size={20} color={colors.muted} />
                  </Pressable>
                ))}
              </View>
            </View>
          ) : (
            <>
              {current.messages.map((m) =>
                m.role === 'user' ? (
                  <View key={m.id} style={{ alignSelf: 'flex-end', maxWidth: '85%', backgroundColor: colors.sand, borderRadius: 18, borderBottomRightRadius: 6, paddingHorizontal: 16, paddingVertical: 10 }}>
                    <Text style={{ fontFamily: fonts.semibold, fontSize: 16, lineHeight: 22, color: colors.ink }}>{m.text}</Text>
                  </View>
                ) : (
                  <Answer key={m.id} m={m} live={m.id === lastId && !pending} />
                ),
              )}
              {pending && <Text style={[type.body, { color: colors.muted }]}>{t.thinking}</Text>}
              {failed && (
                <View style={{ gap: 10, alignItems: 'flex-start' }}>
                  <Text style={type.body}>{t.errorAnswer}</Text>
                  <Button label={t.retry} onPress={retry} />
                </View>
              )}
            </>
          )}
        </ScrollView>

        {/* composer */}
        <View style={{ paddingHorizontal: size.gutter, paddingTop: 8, paddingBottom: 12, gap: 6 }}>
          {hint && <Text style={[type.label, { textAlign: 'center' }]}>{t.micHint}</Text>}
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <View style={{ flex: 1, flexDirection: 'row', alignItems: 'center', minHeight: 56, backgroundColor: colors.paper, borderWidth: 1.5, borderColor: colors.edge, borderRadius: 28, paddingLeft: 20, paddingRight: 6 }}>
              <TextInput
                ref={input} value={text} onChangeText={setText} placeholder={t.placeholder} placeholderTextColor={colors.muted}
                returnKeyType="send" onSubmitEditing={submit} submitBehavior="submit"
                style={{ flex: 1, fontFamily: fonts.medium, fontSize: 17, color: colors.ink, paddingVertical: 10 }}
              />
              {text.trim().length > 0 && <IconButton icon="send" label={t.send} onPress={submit} filled sizePx={44} />}
            </View>
            <IconButton icon="mic" label={t.talk} filled sizePx={56} onPress={() => { setHint(true); input.current?.focus(); }} />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
