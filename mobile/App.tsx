import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import {
  ApiError,
  apiRequest,
  clearToken,
  getToken,
  login,
} from './src/api';
import type { Conversation, Match, Message, Profile, User } from './src/types';

type Screen = 'discover' | 'matches' | 'messages' | 'settings';

const colors = {
  base: '#1e1e2e',
  mantle: '#181825',
  surface: '#313244',
  text: '#cdd6f4',
  muted: '#a6adc8',
  mauve: '#cba6f7',
  green: '#a6e3a1',
  red: '#f38ba8',
};

function Button({
  label,
  onPress,
  secondary = false,
  disabled = false,
}: {
  label: string;
  onPress: () => void;
  secondary?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.button, secondary && styles.secondaryButton, disabled && styles.disabledButton]}
    >
      <Text style={[styles.buttonText, secondary && styles.secondaryButtonText]}>{label}</Text>
    </Pressable>
  );
}

function ErrorText({ error }: { error: string }) {
  return error ? <Text style={styles.error}>{error}</Text> : null;
}

function ProfileCard({ profile, onPress }: { profile: Profile; onPress?: () => void }) {
  return (
    <Pressable accessibilityRole={onPress ? 'button' : undefined} onPress={onPress} style={styles.card}>
      <View style={styles.avatar}>
        <Text style={styles.avatarText}>{profile.name.slice(0, 1).toUpperCase()}</Text>
      </View>
      <View style={styles.cardCopy}>
        <Text style={styles.cardTitle}>{profile.name}{profile.verified ? ' ✓' : ''}</Text>
        <Text style={styles.mutedText}>
          {[profile.age && `${profile.age} yrs`, profile.gender, profile.relationship_intent]
            .filter(Boolean)
            .join(' · ') || 'Kindred member'}
        </Text>
        {profile.dating_energy ? <Text style={styles.tag}>{profile.dating_energy}</Text> : null}
      </View>
    </Pressable>
  );
}

function LoginScreen({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [totp, setTotp] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await login(email.trim(), password, totp.trim());
      onLoggedIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in');
    } finally {
      setBusy(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.loginContainer} keyboardShouldPersistTaps="handled">
        <Text style={styles.brand}>Kindred</Text>
        <Text style={styles.subtitle}>Compatibility-first connection.</Text>
        <View style={styles.card}>
          <Text style={styles.heading}>Welcome back</Text>
          <TextInput autoCapitalize="none" autoComplete="email" keyboardType="email-address" onChangeText={setEmail} placeholder="Email" placeholderTextColor={colors.muted} style={styles.input} value={email} />
          <TextInput autoComplete="password" onChangeText={setPassword} placeholder="Password" placeholderTextColor={colors.muted} secureTextEntry style={styles.input} value={password} />
          <TextInput autoCapitalize="none" keyboardType="number-pad" maxLength={6} onChangeText={setTotp} placeholder="2FA code (if enabled)" placeholderTextColor={colors.muted} style={styles.input} value={totp} />
          <ErrorText error={error} />
          <Button disabled={busy || !email || !password} label={busy ? 'Signing in…' : 'Sign in'} onPress={submit} />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function DiscoverScreen() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(true);
  const load = useCallback(async () => {
    setBusy(true);
    try {
      const result = await apiRequest<Profile[]>('/api/profiles');
      setProfiles(result);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load profiles');
    } finally {
      setBusy(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);
  return (
    <View style={styles.screen}>
      <Text style={styles.heading}>Discover</Text>
      <Text style={styles.subtitle}>Find people through compatibility, not speed.</Text>
      <ErrorText error={error} />
      {busy ? <ActivityIndicator color={colors.mauve} /> : <FlatList data={profiles} keyExtractor={(item) => item.id} onRefresh={load} refreshing={busy} renderItem={({ item }) => <ProfileCard profile={item} />} ListEmptyComponent={<Text style={styles.mutedText}>No profiles are available yet.</Text>} />}
    </View>
  );
}

function MatchesScreen({ profileId }: { profileId: string }) {
  const [matches, setMatches] = useState<Match[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    void apiRequest<{ matches: Match[] }>(`/api/matches/${profileId}`)
      .then((result) => setMatches(result.matches || []))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : 'Unable to load matches'));
  }, [profileId]);
  return (
    <View style={styles.screen}>
      <Text style={styles.heading}>Your matches</Text>
      <Text style={styles.subtitle}>A little more intention, a lot less noise.</Text>
      <ErrorText error={error} />
      <FlatList data={matches} keyExtractor={(item) => item.id} renderItem={({ item }) => <ProfileCard profile={item} />} ListEmptyComponent={<Text style={styles.mutedText}>No compatible matches yet.</Text>} />
    </View>
  );
}

function ConversationScreen({ profileId, partnerId, onBack }: { profileId: string; partnerId: string; onBack: () => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    try {
      const result = await apiRequest<{ messages: Message[] }>(`/api/messages/${profileId}/${partnerId}`);
      setMessages(result.messages || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load conversation');
    }
  }, [partnerId, profileId]);
  useEffect(() => { void load(); }, [load]);
  const send = async () => {
    const content = draft.trim();
    if (!content) return;
    try {
      await apiRequest('/api/messages', { method: 'POST', body: { from_id: profileId, to_id: partnerId, content } });
      setDraft('');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to send message');
    }
  };
  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
      <View style={styles.screen}>
        <Button label="‹ Back to messages" onPress={onBack} secondary />
        <ErrorText error={error} />
        <FlatList data={messages} keyExtractor={(item) => item.id} renderItem={({ item }) => <View style={[styles.message, item.from_id === profileId ? styles.ownMessage : styles.otherMessage]}><Text style={styles.messageText}>{item.deleted ? 'This message was deleted' : item.content}</Text><Text style={styles.messageTime}>{new Date(item.created_at).toLocaleTimeString()}</Text></View>} ListEmptyComponent={<Text style={styles.mutedText}>Start a thoughtful conversation.</Text>} />
        <View style={styles.composer}>
          <TextInput multiline onChangeText={setDraft} onSubmitEditing={send} placeholder="Write a message…" placeholderTextColor={colors.muted} style={[styles.input, styles.composerInput]} value={draft} />
          <Button label="Send" onPress={send} />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function MessagesScreen({ profileId }: { profileId: string }) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [partnerId, setPartnerId] = useState<string | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    try {
      const result = await apiRequest<{ conversations: Conversation[] }>(`/api/messages/${profileId}`);
      setConversations(result.conversations || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load messages');
    }
  }, [profileId]);
  useEffect(() => { void load(); }, [load]);
  if (partnerId) return <ConversationScreen partnerId={partnerId} profileId={profileId} onBack={() => { setPartnerId(null); void load(); }} />;
  return (
    <View style={styles.screen}>
      <Text style={styles.heading}>Messages</Text>
      <Text style={styles.subtitle}>Conversations with room to be human.</Text>
      <ErrorText error={error} />
      <FlatList data={conversations} keyExtractor={(item) => item.partner_id} renderItem={({ item }) => <Pressable accessibilityRole="button" onPress={() => setPartnerId(item.partner_id)} style={styles.card}><Text style={styles.cardTitle}>{item.partner_name || 'Kindred member'}</Text><Text style={styles.mutedText} numberOfLines={2}>{item.last_message || 'Open conversation'}</Text></Pressable>} ListEmptyComponent={<Text style={styles.mutedText}>No conversations yet.</Text>} />
    </View>
  );
}

function SettingsScreen({ user, onLogout }: { user: User; onLogout: () => void }) {
  return (
    <View style={styles.screen}>
      <Text style={styles.heading}>Settings</Text>
      <View style={styles.card}><Text style={styles.cardTitle}>{user.display_name}</Text><Text style={styles.mutedText}>{user.email}</Text><Text style={styles.mutedText}>{user.profile_id ? 'Profile connected' : 'Finish your profile on the web portal'}</Text></View>
      <Button label="Sign out" onPress={onLogout} secondary />
    </View>
  );
}

function AppShell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [screen, setScreen] = useState<Screen>('discover');
  const content = useMemo(() => {
    if (screen === 'matches') return user.profile_id ? <MatchesScreen profileId={user.profile_id} /> : <EmptyProfile />;
    if (screen === 'messages') return user.profile_id ? <MessagesScreen profileId={user.profile_id} /> : <EmptyProfile />;
    if (screen === 'settings') return <SettingsScreen onLogout={onLogout} user={user} />;
    return <DiscoverScreen />;
  }, [onLogout, screen, user]);
  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.flex}>{content}</View>
      <View style={styles.nav}>{(['discover', 'matches', 'messages', 'settings'] as Screen[]).map((item) => <Pressable accessibilityRole="tab" accessibilityState={{ selected: screen === item }} key={item} onPress={() => setScreen(item)} style={styles.navItem}><Text style={[styles.navText, screen === item && styles.navTextActive]}>{item.charAt(0).toUpperCase() + item.slice(1)}</Text></Pressable>)}</View>
    </SafeAreaView>
  );
}

function EmptyProfile() {
  return <View style={styles.screen}><Text style={styles.heading}>Finish your profile</Text><Text style={styles.subtitle}>Complete the questionnaire in the Kindred web portal to unlock matches and messages.</Text></View>;
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  useEffect(() => {
    void (async () => {
      if (!await getToken()) { setCheckingSession(false); return; }
      try { setUser(await apiRequest<User>('/api/auth/me')); }
      catch { await clearToken(); }
      finally { setCheckingSession(false); }
    })();
  }, []);
  if (checkingSession) return <SafeAreaView style={styles.safe}><ActivityIndicator color={colors.mauve} /></SafeAreaView>;
  if (!user) return <LoginScreen onLoggedIn={() => { void apiRequest<User>('/api/auth/me').then(setUser); }} />;
  return <AppShell onLogout={async () => { await clearToken(); setUser(null); }} user={user} />;
}

const styles = StyleSheet.create({
  safe: { backgroundColor: colors.base, flex: 1 },
  flex: { flex: 1 },
  loginContainer: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  screen: { flex: 1, padding: 20 },
  brand: { color: colors.mauve, fontSize: 40, fontWeight: '800', marginBottom: 4 },
  heading: { color: colors.text, fontSize: 26, fontWeight: '800', marginBottom: 6 },
  subtitle: { color: colors.muted, fontSize: 15, lineHeight: 22, marginBottom: 18 },
  card: { backgroundColor: colors.surface, borderRadius: 16, flexDirection: 'row', marginBottom: 12, padding: 16 },
  cardCopy: { flex: 1, marginLeft: 12 },
  cardTitle: { color: colors.text, fontSize: 17, fontWeight: '700', marginBottom: 4 },
  mutedText: { color: colors.muted, fontSize: 14, lineHeight: 20 },
  avatar: { alignItems: 'center', backgroundColor: colors.mauve, borderRadius: 28, height: 56, justifyContent: 'center', width: 56 },
  avatarText: { color: colors.base, fontSize: 24, fontWeight: '800' },
  tag: { alignSelf: 'flex-start', backgroundColor: colors.green, borderRadius: 8, color: colors.base, fontSize: 12, marginTop: 8, overflow: 'hidden', paddingHorizontal: 8, paddingVertical: 3 },
  input: { backgroundColor: colors.mantle, borderColor: colors.surface, borderRadius: 10, borderWidth: 1, color: colors.text, fontSize: 16, marginBottom: 12, padding: 13 },
  button: { alignItems: 'center', backgroundColor: colors.mauve, borderRadius: 10, marginTop: 4, paddingHorizontal: 18, paddingVertical: 12 },
  buttonText: { color: colors.base, fontSize: 15, fontWeight: '800' },
  secondaryButton: { backgroundColor: colors.surface },
  secondaryButtonText: { color: colors.text },
  disabledButton: { opacity: 0.45 },
  error: { color: colors.red, fontSize: 14, marginBottom: 12 },
  nav: { backgroundColor: colors.mantle, borderTopColor: colors.surface, borderTopWidth: 1, flexDirection: 'row', paddingBottom: 8, paddingTop: 8 },
  navItem: { alignItems: 'center', flex: 1, padding: 8 },
  navText: { color: colors.muted, fontSize: 12 },
  navTextActive: { color: colors.mauve, fontWeight: '800' },
  message: { borderRadius: 14, marginBottom: 8, maxWidth: '82%', padding: 12 },
  ownMessage: { alignSelf: 'flex-end', backgroundColor: colors.mauve },
  otherMessage: { alignSelf: 'flex-start', backgroundColor: colors.surface },
  messageText: { color: colors.text, fontSize: 15, lineHeight: 21 },
  messageTime: { color: colors.muted, fontSize: 10, marginTop: 4 },
  composer: { flexDirection: 'row', gap: 8, paddingTop: 8 },
  composerInput: { flex: 1, marginBottom: 0, maxHeight: 96 },
});
