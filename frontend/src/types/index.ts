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
}

export interface AgentConfig {
  provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
}

export interface ReviewCreate {
  agent_roles: string[];
  provider?: string;
  model?: string;
  agent_configs?: Record<string, AgentConfig>;
  api_keys?: Record<string, string>;
  conversation_mode?: 'council' | 'arena';
}

export interface ReviewAgent {
  id: number;
  review_id: number;
  role: string;
  provider: string;
  model: string;
  parsed_successfully: boolean;
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
