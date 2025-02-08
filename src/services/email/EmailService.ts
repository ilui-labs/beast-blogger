import nodemailer from 'nodemailer';
import { simpleParser, ParsedMail } from 'mailparser';
import Imap from 'imap';
import { Box } from 'imap';
import { EventEmitter } from 'events';
import { ContentStructure } from '../content/ContentGeneratorService';
import { ChatOpenAI } from '@langchain/openai';
import { PromptTemplate } from '@langchain/core/prompts';
import { StructuredOutputParser } from 'langchain/output_parsers';
import { z } from 'zod';

const commandSchema = z.object({
  type: z.enum(['UPLOAD_TO_SHOPIFY', 'CHANGE_IMAGE', 'UPDATE_CONTENT', 'REJECT']),
  feedback: z.string().optional(),
  additionalContext: z.object({
    tone: z.string().optional(),
    specificRequests: z.array(z.string()).optional(),
    urgency: z.enum(['low', 'medium', 'high']).optional(),
  }).optional(),
});

// Configuration interfaces
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
  type: 'UPLOAD_TO_SHOPIFY' | 'CHANGE_IMAGE' | 'UPDATE_CONTENT' | 'REJECT';
  contentId: string;
  feedback?: string;
  additionalContext?: {
    tone?: string;
    specificRequests?: string[];
    urgency?: 'low' | 'medium' | 'high';
  };
}

export class EmailService extends EventEmitter {
  private transporter: nodemailer.Transporter;
  private imap: Imap;
  private isConnected: boolean = false;
  private contentMap: Map<string, ContentStructure>;
  private llm: ChatOpenAI;
  private commandParser: StructuredOutputParser<typeof commandSchema>;

  constructor(config: EmailConfig) {
    super();
    
    // Setup SMTP for sending emails
    this.transporter = nodemailer.createTransport({
      host: config.host || 'smtp.zoho.com',
      port: config.port || 465,
      secure: true,
      auth: {
        user: config.user,
        pass: config.pass,
      },
    });

    // Setup IMAP for receiving emails
    this.imap = new Imap({
      user: config.user,
      password: config.pass,
      host: config.imapHost || 'imap.zoho.com',
      port: config.imapPort || 993,
      tls: true,
      tlsOptions: { rejectUnauthorized: true }
    });

    this.contentMap = new Map();

    // Initialize LLM
    this.llm = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.3,
      openAIApiKey: config.openAiKey,
    });

    // Initialize command parser
    this.commandParser = StructuredOutputParser.fromZodSchema(commandSchema);

    // Setup IMAP error handling
    this.imap.on('error', (err: Error) => {
      console.error('IMAP error:', err);
      this.emit('error', err);
    });

    this.imap.on('end', () => {
      this.isConnected = false;
      this.emit('disconnected');
    });
  }

  async connect(): Promise<void> {
    if (this.isConnected) return;

    try {
      await new Promise<void>((resolve, reject) => {
        this.imap.once('ready', () => {
          this.isConnected = true;
          this.emit('connected');
          resolve();
        });
        this.imap.once('error', reject);
        this.imap.connect();
      });

      await this.startListening();
    } catch (error) {
      console.error('Error connecting to mail server:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to connect to mail server');
    }
  }

  async disconnect(): Promise<void> {
    if (!this.isConnected) return;

    await new Promise<void>((resolve) => {
      this.imap.once('end', () => resolve());
      this.imap.end();
    });
  }

  async sendContentPreview(content: ContentStructure, toEmail: string): Promise<string> {
    try {
      const contentId = `content_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      this.contentMap.set(contentId, content);

      const emailHtml = `
        <h1>${content.title}</h1>
        <p><strong>Excerpt:</strong> ${content.excerpt}</p>
        <hr>
        ${content.content}
        <hr>
        <p>Please review the content above and reply with your feedback. You can:</p>
        <ul>
          <li>Approve and publish the content</li>
          <li>Request changes to the images</li>
          <li>Request content revisions</li>
          <li>Reject the content with feedback</li>
        </ul>
        <p>Feel free to provide your feedback in natural language - our system will understand your intent.</p>
      `;

      await this.sendEmail({
        from: process.env.EMAIL_FROM || 'beastblogger@beastputty.com',
        to: toEmail,
        subject: `Content Preview: ${contentId}`,
        body: `${content.title}\n\n${content.excerpt}\n\n${content.content}\n\nPlease review and reply with your feedback.`,
        html: emailHtml
      });

      return contentId;
    } catch (error) {
      console.error('Error sending email preview:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to send email preview');
    }
  }

  async sendEmail(message: Omit<EmailMessage, 'id' | 'timestamp'>): Promise<string> {
    try {
      const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      await this.transporter.sendMail({
        messageId,
        from: message.from,
        to: message.to,
        subject: message.subject,
        text: message.body,
        html: message.html,
      });

      return messageId;
    } catch (error) {
      console.error('Error sending email:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to send email');
    }
  }

  private async startListening(): Promise<void> {
    try {
      await new Promise<Box>((resolve, reject) => {
        this.imap.openBox('INBOX', false, (err: Error | null, box: Box) => {
          if (err) reject(err);
          else resolve(box);
        });
      });

      // Listen for new emails
      this.imap.on('mail', () => {
        this.processNewEmails();
      });
    } catch (error) {
      console.error('Error starting email listener:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to start email listener');
    }
  }

  private async processNewEmails(): Promise<void> {
    try {
      const messages = await new Promise<number[]>((resolve, reject) => {
        this.imap.search(['UNSEEN'], (err: Error | null, results: number[]) => {
          if (err) reject(err);
          else resolve(results);
        });
      });

      for (const msgId of messages) {
        const fetch = this.imap.fetch(msgId, { bodies: '' });
        
        fetch.on('message', async (msg) => {
          let buffer = '';
          msg.on('body', (stream) => {
            stream.on('data', (chunk) => {
              buffer += chunk.toString('utf8');
            });
          });

          msg.once('end', async () => {
            try {
              const parsed: ParsedMail = await simpleParser(buffer);
              
              const message: EmailMessage = {
                id: msgId.toString(),
                subject: parsed.subject || '',
                body: parsed.text || '',
                html: parsed.html || undefined,
                from: Array.isArray(parsed.from) 
                  ? parsed.from[0]?.text || '' 
                  : parsed.from?.text || '',
                to: Array.isArray(parsed.to) 
                  ? parsed.to[0]?.text || '' 
                  : parsed.to?.text || '',
                timestamp: parsed.date || new Date(),
              };

              await this.handleIncomingEmail(message);
              this.emit('message', message);
            } catch (parseError) {
              console.error('Error parsing email:', parseError instanceof Error ? parseError.message : 'Unknown error');
            }
          });
        });
      }
    } catch (error) {
      console.error('Error processing new emails:', error instanceof Error ? error.message : 'Unknown error');
    }
  }

  private async handleIncomingEmail(message: EmailMessage): Promise<void> {
    try {
      // Extract content ID from subject (e.g., "Re: Content Preview: [contentId]")
      const contentId = message.subject.match(/Content Preview: ([a-zA-Z0-9_-]+)/)?.[1];
      
      if (contentId && this.contentMap.has(contentId)) {
        const command = await this.parseCommand(message.body);
        if (command) {
          this.emit('command', { ...command, contentId });
        }
      }
    } catch (error) {
      console.error('Error handling incoming email:', error instanceof Error ? error.message : 'Unknown error');
    }
  }

  private async parseCommand(body: string): Promise<Omit<EmailCommand, 'contentId'> | null> {
    try {
      const prompt = new PromptTemplate({
        template: `Analyze the following email response and identify the requested action and any additional context.

Email content:
{emailBody}

Common patterns to look for:
1. Content approval and publishing requests
2. Image change requests
3. Content revision requests
4. Rejections or feedback

Also identify:
- The tone of the request (urgent, casual, formal, etc.)
- Any specific requirements or details mentioned
- The overall urgency level

Provide a structured response with:
- type: The main action requested
- feedback: Any feedback or comments provided
- additionalContext: Additional details about the request

{format_instructions}`,
        inputVariables: ['emailBody'],
        partialVariables: {
          format_instructions: this.commandParser.getFormatInstructions(),
        },
      });

      const input = await prompt.format({ emailBody: body });
      const response = await this.llm.invoke(input);
      const parsed = await this.commandParser.parse(response.content.toString()) as z.infer<typeof commandSchema>;

      // Map the parsed response to our command structure
      return {
        type: parsed.type,
        feedback: parsed.feedback,
        additionalContext: parsed.additionalContext
      };
    } catch (error) {
      console.error('Error parsing command with LLM:', error instanceof Error ? error.message : 'Unknown error');
      return null;
    }
  }
} 