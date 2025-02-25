import nodemailer from 'nodemailer';
import { simpleParser, ParsedMail } from 'mailparser';
import Imap from 'imap';
import { Box } from 'imap';
import { EventEmitter } from 'events';
import { ChatOpenAI } from '@langchain/openai';
import { PromptTemplate } from '@langchain/core/prompts';
import { StructuredOutputParser } from 'langchain/output_parsers';
import { z } from 'zod';
import type { EmailConfig, EmailMessage, EmailCommand } from '@types';

const commandSchema = z.array(
  z.object({
    type: z.enum([
      'UPLOAD_TO_SHOPIFY', 
      'CHANGE_IMAGE', 
      'UPDATE_CONTENT', 
      'REJECT',
      'LIST_KEYWORDS',
      'UPDATE_KEYWORDS',
      'LIST_POSTS',
      'DELETE_POST',
      'GENERATE_POSTS'
    ]),
    feedback: z.string().optional(),
    additionalContext: z.object({
      tone: z.string().optional(),
      specificRequests: z.array(z.string()).optional(),
      urgency: z.enum(['low', 'medium', 'high']).optional(),
      count: z.number().optional(),
      keywords: z.array(z.string()).optional(),
      postId: z.string().optional(),
    }).optional(),
  })
).min(1);

export class EmailService extends EventEmitter {
  private transporter: nodemailer.Transporter;
  private imap: Imap;
  private isConnected: boolean = false;
  private llm: ChatOpenAI;
  private commandParser: StructuredOutputParser<typeof commandSchema>;
  private readonly defaultFrom = process.env.EMAIL_FROM || 'beastblogger@beastputty.com';

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
      const contentId = message.subject.match(/Content Preview: ([a-zA-Z0-9_-]+)/)?.[1];
      const commands = await this.parseCommand(message.body);
      
      for (const command of commands) {
        this.emit('command', { 
          ...command, 
          contentId,
          from: message.from
        });
      }
    } catch (error) {
      console.error('Error handling incoming email:', error instanceof Error ? error.message : 'Unknown error');
      this.emit('error', error);
    }
  }

  private async parseCommand(body: string): Promise<Array<Omit<EmailCommand, 'contentId' | 'from'>>> {
    try {
      const prompt = new PromptTemplate({
        template: `Analyze the following email response and identify ALL requested actions and their additional context.

Email content:
{emailBody}

Common patterns to look for:
1. Content approval and publishing requests
2. Image change requests
3. Content revision requests
4. Rejections or feedback
5. List or manage keywords
6. List or manage posts
7. Generate new posts

For EACH action identified, provide:
- type: The main action requested
- feedback: Any feedback or comments provided
- additionalContext: Additional details about the request

Return an array of commands, even if there's only one.

{format_instructions}`,
        inputVariables: ['emailBody'],
        partialVariables: {
          format_instructions: this.commandParser.getFormatInstructions(),
        },
      });

      const input = await prompt.format({ emailBody: body });
      const response = await this.llm.invoke(input);
      const parsed = await this.commandParser.parse(response.content.toString()) as z.infer<typeof commandSchema>;

      return Array.isArray(parsed) ? parsed : [parsed];
    } catch (error) {
      console.error('Error parsing commands with LLM:', error instanceof Error ? error.message : 'Unknown error');
      return [];
    }
  }

  async sendErrorNotification(title: string, error: unknown, metadata?: Record<string, unknown>): Promise<void> {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    const errorDetails = error instanceof Error ? error.stack : String(error);
    
    await this.sendEmail({
      from: this.defaultFrom,
      to: process.env.ADMIN_EMAIL || 'jackson@beastputty.com',
      subject: `Error: ${title}`,
      body: `An error occurred: ${errorMessage}`,
      html: `
        <h2>Error: ${title}</h2>
        <p><strong>Message:</strong> ${errorMessage}</p>
        ${metadata ? `<p><strong>Context:</strong> ${JSON.stringify(metadata, null, 2)}</p>` : ''}
        ${errorDetails ? `<pre>${errorDetails}</pre>` : ''}
      `
    });
  }
} 