import { Tabs } from 'expo-router';
import { Icon } from '@/components/Icon';
import { useLang } from '@/i18n';
import { colors, fonts } from '@/theme';

export default function TabsLayout() {
  const { t } = useLang();
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarHideOnKeyboard: true,
        tabBarActiveTintColor: colors.green,
        tabBarInactiveTintColor: colors.muted,
        tabBarLabelStyle: { fontFamily: fonts.bold, fontSize: 13 },
        tabBarStyle: { backgroundColor: colors.paper, borderTopColor: colors.edge, borderTopWidth: 1.5, height: 76, paddingTop: 8 },
        sceneStyle: { backgroundColor: colors.bone },
      }}
    >
      <Tabs.Screen name="index" options={{ title: t.tabAsk, tabBarIcon: ({ color }) => <Icon name="chat" color={color as string} /> }} />
      <Tabs.Screen name="land" options={{ title: t.tabLand, tabBarIcon: ({ color }) => <Icon name="map" color={color as string} /> }} />
      <Tabs.Screen name="data" options={{ title: t.tabData, tabBarIcon: ({ color }) => <Icon name="chart" color={color as string} /> }} />
    </Tabs>
  );
}
