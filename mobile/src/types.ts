export type User = {
  user_id: string;
  email: string;
  display_name: string;
  profile_id: string | null;
};

export type Profile = {
  id: string;
  name: string;
  age?: number | null;
  gender?: string | null;
  seeking?: string | null;
  photo?: string | null;
  verified?: number;
  dating_energy?: string | null;
  relationship_intent?: string | null;
};

export type Match = Profile & {
  compatibility?: { total?: number; breakdown?: Record<string, number> };
};

export type Conversation = {
  partner_id: string;
  partner_name?: string;
  last_message?: string;
  unread?: number;
};

export type Message = {
  id: string;
  from_id: string;
  to_id: string;
  content: string;
  created_at: string;
  deleted?: number;
  edited?: number;
};
