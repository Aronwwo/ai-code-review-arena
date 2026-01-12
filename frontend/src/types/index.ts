// Auth types
export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

// Project types
export interface Project {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  created_at: string;
  updated_at: string;
  file_count: number;
  review_count: number;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

// File types
export interface File {
  id: number;
  project_id: number;
  name: string;
  language: string | null;
  size_bytes: number;
  content_hash: string;
  created_at: string;
  updated_at: string;
}

export interface FileWithContent extends File {
  content: string;
}

export interface FileCreate {
  name: string;
  content: string;
  language?: string;
}

// Review types
export type ReviewStatus = 'pending' | 'running' | 'completed' | 'failed';
export type IssueSeverity = 'info' | 'warning' | 'error';
export type IssueStatus = 'open' | 'confirmed' | 'dismissed' | 'resolved';

export interface Review {
  id: number;
  project_id: number;
  status: ReviewStatus;
  created_by: number;
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  agent_count: number;
  issue_count: number;
  review_mode?: ReviewMode;
  summary?: string | null;
}

export interface AgentConfig {
  provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
  timeout_seconds?: number;
  custom_provider?: {
    id: string;
    name: string;
    base_url: string;
    api_key?: string;
    header_name?: string;
    header_prefix?: string;
  };
}

export interface ReviewCreate {
  review_mode: ReviewMode;
  agent_roles: string[];
  provider?: string;
  model?: string;
  agent_configs?: Record<string, AgentConfig>;
  moderator_config: AgentConfig;
  api_keys?: Record<string, string>;
}

export interface ReviewAgent {
  id: number;
  review_id: number;
  role: string;
  provider: string;
  model: string;
  parsed_successfully: boolean;
  timed_out: boolean;
  timeout_seconds: number | null;
  raw_output: string | null;
  created_at: string;
}

export interface Issue {
  id: number;
  review_id: number;
  file_id: number | null;
  severity: IssueSeverity;
  category: string;
  title: string;
  description: string;
  file_name: string | null;
  line_start: number | null;
  line_end: number | null;
  status: IssueStatus;
  confirmed: boolean;
  final_severity: IssueSeverity | null;
  moderator_comment: string | null;
  created_at: string;
  updated_at: string;
  suggestion_count: number;
}

export interface Suggestion {
  id: number;
  issue_id: number;
  suggested_code: string | null;
  explanation: string;
  created_at: string;
}

export interface IssueWithSuggestions extends Issue {
  suggestions: Suggestion[];
}

// Conversation types
export type ConversationMode = 'cooperative' | 'adversarial' | 'council' | 'arena';
export type ConversationStatus = 'pending' | 'running' | 'completed' | 'failed';
export type SenderType = 'agent' | 'user' | 'moderator';

export interface Conversation {
  id: number;
  review_id: number;
  mode: ConversationMode;
  topic_type: string;
  topic_id: number | null;
  status: ConversationStatus;
  summary: string | null;
  created_at: string;
  completed_at: string | null;
  message_count: number;
}

export interface Message {
  id: number;
  conversation_id: number;
  sender_type: SenderType;
  sender_name: string;
  turn_index: number;
  content: string;
  is_summary: boolean;
  created_at: string;
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[];
}

export interface ConversationCreate {
  mode: ConversationMode;
  topic_type: string;
  topic_id?: number;
  provider?: string;
  model?: string;
}

// Review mode types
export type ReviewMode = 'council' | 'arena';

// Arena types
export type ArenaStatus = 'pending' | 'running' | 'voting' | 'completed' | 'failed';
export type ArenaWinner = 'A' | 'B' | 'tie';

export interface ArenaTeamConfig {
  general: AgentConfig;
  security: AgentConfig;
  performance: AgentConfig;
  style: AgentConfig;
}

export interface ArenaIssue {
  severity: 'info' | 'warning' | 'error';
  category: string;
  title: string;
  description: string;
  file_name: string | null;
  line_start: number | null;
  line_end: number | null;
}

export interface ArenaSession {
  id: number;
  project_id: number;
  created_by: number;
  status: ArenaStatus;
  error_message: string | null;
  team_a_config: ArenaTeamConfig;
  team_b_config: ArenaTeamConfig;
  team_a_summary: string | null;
  team_b_summary: string | null;
  team_a_issues: ArenaIssue[];
  team_b_issues: ArenaIssue[];
  winner: ArenaWinner | null;
  vote_comment: string | null;
  voted_at: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ArenaSessionCreate {
  project_id: number;
  team_a_config: ArenaTeamConfig;
  team_b_config: ArenaTeamConfig;
  api_keys?: Record<string, string>;
}

export interface ArenaVote {
  winner: ArenaWinner;
  comment?: string;
}

export interface TeamRating {
  id: number;
  config_hash: string;
  config: ArenaTeamConfig;
  elo_rating: number;
  games_played: number;
  wins: number;
  losses: number;
  ties: number;
  win_rate: number;
}
