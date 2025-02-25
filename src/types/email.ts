import { ContentStructure } from './content';

export interface EmailConfig {
  host: string;
  port: number;
  user: string;
  pass: string;
  imapHost?: string;
  imapPort?: number;
  openAiKey: string;
}

export interface EmailMessage {
  id: string;
  subject: string;
  body: string;
  html?: string;
  from: string;
  to: string;
  timestamp: Date;
}

export interface EmailCommand {
  type: 'UPLOAD_TO_SHOPIFY' | 'CHANGE_IMAGE' | 'UPDATE_CONTENT' | 'REJECT' |
        'LIST_KEYWORDS' | 'UPDATE_KEYWORDS' | 'LIST_POSTS' | 'DELETE_POST' | 'GENERATE_POSTS';
  contentId: string;  // Required for content-related commands
  from: string;
  feedback?: string;
  additionalContext?: {
    tone?: string;
    specificRequests?: string[];
    urgency?: 'low' | 'medium' | 'high';
    count?: number;
    keywords?: string[];
    postId?: string;
  };
}

export interface StorageCommand extends Omit<EmailCommand, 'contentId'> {
  contentId?: never;
  type: 'LIST_KEYWORDS' | 'UPDATE_KEYWORDS' | 'LIST_POSTS' | 'DELETE_POST' | 'GENERATE_POSTS';
}

export interface RevisionRequest {
  id: string;
  content: ContentStructure;
  command: EmailCommand;
  timestamp: Date;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  metadata?: {
    processingTime?: number;
    errorDetails?: string;
    commandContext?: EmailCommand['additionalContext'];
  };
} 