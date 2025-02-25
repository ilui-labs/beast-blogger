import { ContentGeneratorService } from '../content/ContentGeneratorService';
import { EmailService } from './EmailService';
import { EmailRevisionService } from './EmailRevisionService';
import { ImageHandlerService } from '../image/ImageHandlerService';
import { ShopifyUploaderService } from '../shopify/ShopifyUploaderService';
import { StorageService } from '../storage/StorageService';
import type { 
  ContentStructure,
  EmailCommand,
  StorageCommand,
  ImageScenario
} from '@types';

interface ContentUpdateOptions {
  tone?: string;
  urgency?: 'low' | 'medium' | 'high';
  requirements?: string[];
}

interface RejectionDetails {
  feedback?: string;
  tone?: string;
  specificIssues?: string[];
  urgency?: 'low' | 'medium' | 'high';
}

export class EmailCommandHandler {
  private contentMap: Map<string, ContentStructure> = new Map();

  constructor(
    private emailService: EmailService,
    private revisionService: EmailRevisionService,
    private shopifyUploader: ShopifyUploaderService,
    private imageService: ImageHandlerService,
    private contentService: ContentGeneratorService,
    private storageService: StorageService
  ) {
    this.setupEventListeners();
    this.storageService.load().catch(error => 
      this.handleError('Storage Load Error', error)
    );
  }

  private setupEventListeners(): void {
    this.emailService.on('command', async (command: EmailCommand | StorageCommand) => {
      try {
        if ('contentId' in command && command.contentId) {
          await this.handleCommand(command as EmailCommand);
        } else {
          await this.handleStorageCommand(command as StorageCommand);
        }
      } catch (error) {
        await this.handleError('Command Processing Error', error, { command });
      }
    });

    this.emailService.on('error', async (error: Error) => {
      await this.handleError('Email Service Error', error);
    });
  }

  async sendContentPreview(content: ContentStructure, toEmail: string): Promise<string> {
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

    await this.emailService.sendEmail({
      from: process.env.EMAIL_FROM || 'beastblogger@beastputty.com',
      to: toEmail,
      subject: `Content Preview: ${contentId}`,
      body: `${content.title}\n\n${content.excerpt}\n\n${content.content}\n\nPlease review and reply with your feedback.`,
      html: emailHtml
    });

    return contentId;
  }

  private async handleCommand(command: EmailCommand): Promise<void> {
    if (!command.contentId) {
      throw new Error('Content ID is required for this operation');
    }

    const content = await this.getContentForCommand(command);
    if (!content) {
      await this.handleError(
        'Content Not Found', 
        new Error(`Content not found for command: ${command.contentId}`),
        { command }
      );
      return;
    }

    // Create a revision request
    const revision = await this.revisionService.createRevision(
      command.contentId,
      content,
      command
    );

    try {
      switch (command.type) {
      case 'UPLOAD_TO_SHOPIFY':
        await this.handleShopifyUpload(content, command.additionalContext);
        break;
      case 'CHANGE_IMAGE':
        await this.handleImageChange(content, command.additionalContext);
        break;
      case 'UPDATE_CONTENT':
        await this.handleContentUpdate(content, command.additionalContext);
        break;
      case 'REJECT':
        await this.handleRejection(content, command.feedback, command.additionalContext);
        break;
      }

      await this.revisionService.updateRevisionStatus(command.contentId, revision.id, 'completed');
    } catch (error) {
      const metadata = {
        command,
        content: {
          id: content.title,
          excerpt: content.excerpt
        },
        revision: {
          id: revision.id,
          timestamp: revision.timestamp
        }
      };

      await this.revisionService.updateRevisionStatus(
        command.contentId, 
        revision.id, 
        'failed',
        { 
          errorDetails: error instanceof Error ? error.message : 'Unknown error'
        }
      );

      await this.handleError(
        `${command.type} Processing Error`,
        error,
        metadata
      );

      throw error;
    }
  }

  private async handleError(
    title: string,
    error: unknown,
    metadata?: Record<string, unknown>
  ): Promise<void> {
    console.error(`${title}:`, {
      error: error instanceof Error ? error.message : 'Unknown error',
      metadata
    });
    await this.emailService.sendErrorNotification(title, error, metadata);
  }

  private async getContentForCommand(command: EmailCommand): Promise<ContentStructure | null> {
    const revision = await this.revisionService.getLatestRevision(command.contentId);
    return revision?.content || null;
  }

  private async handleShopifyUpload(
    content: ContentStructure, 
    context?: EmailCommand['additionalContext']
  ): Promise<void> {
    try {
      if (context?.urgency === 'high') {
        console.log('Processing urgent Shopify upload');
      }

      // Convert ContentStructure to ShopifyArticleInput
      const shopifyArticle = {
        title: content.title,
        content: content.content,
        excerpt: content.excerpt,
        image: content.images?.[0] ? {
          url: content.images[0].url,
          altText: content.images[0].alt
        } : undefined
      };

      const response = await this.shopifyUploader.uploadPost(shopifyArticle);
      console.log(`Article uploaded to Shopify: ${response.handle}`);

      // Store the Shopify response details in the content
      Object.assign(content, {
        shopifyData: {
          id: response.id,
          handle: response.handle,
          publishedAt: new Date()
        }
      });
    } catch (error) {
      console.error('Error uploading to Shopify:', error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  }

  private async handleImageChange(
    content: ContentStructure,
    context?: EmailCommand['additionalContext']
  ): Promise<void> {
    try {
      const imageScenario: ImageScenario = {
        description: `Update image for article: ${content.title}`,
        prompt: context?.specificRequests?.join('\n') || '',
        relevantKeywords: content.metadata.keywords,
        absurdityLevel: 8,
        beastPuttyConnection: 'Incorporating Beast Putty themes and style'
      };

      const newImage = await this.imageService.generateImage(imageScenario);
      content.images = [newImage, ...(content.images || [])];
    } catch (error) {
      console.error('Error changing image:', error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  }

  private async handleContentUpdate(
    content: ContentStructure,
    context?: EmailCommand['additionalContext']
  ): Promise<void> {
    try {
      const updateOptions: ContentUpdateOptions = {
        tone: context?.tone,
        urgency: context?.urgency,
        requirements: context?.specificRequests,
      };

      // Generate new content with the same structure
      const updatedContent = await this.contentService.generateContent(
        `Update article: ${content.title} with tone: ${updateOptions.tone || 'default'}`,
        content.metadata.keywords
      );

      // Merge the new content while preserving metadata and links
      Object.assign(content, {
        title: updatedContent.title,
        excerpt: updatedContent.excerpt,
        content: updatedContent.content,
        htmlContent: updatedContent.htmlContent
      });
    } catch (error) {
      console.error('Error updating content:', error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  }

  private async handleRejection(
    content: ContentStructure,
    feedback?: string,
    context?: EmailCommand['additionalContext']
  ): Promise<void> {
    try {
      const rejectionDetails: RejectionDetails = {
        feedback,
        tone: context?.tone,
        specificIssues: context?.specificRequests,
        urgency: context?.urgency,
      };

      // Store rejection details in content metadata
      Object.assign(content.metadata, {
        rejectionHistory: [
          ...(content.metadata.rejectionHistory || []),
          {
            timestamp: new Date(),
            ...rejectionDetails
          }
        ]
      });

      // Log rejection for tracking
      console.log('Content rejected:', {
        contentId: content.title,
        details: rejectionDetails
      });
    } catch (error) {
      console.error('Error handling rejection:', error instanceof Error ? error.message : 'Unknown error');
      throw error;
    }
  }

  private async handleStorageCommand(command: StorageCommand): Promise<void> {
    let keywords: string[];
    
    switch (command.type) {
    case 'LIST_KEYWORDS':
      keywords = this.storageService.getKeywords();
      await this.emailService.sendEmail({
        from: process.env.EMAIL_FROM || 'beastblogger@beastputty.com',
        to: command.from,
        subject: 'Current Keywords List',
        body: `Current keywords:\n\n${keywords.join('\n')}`
      });
      break;
    case 'UPDATE_KEYWORDS':
      if (command.additionalContext?.keywords) {
        await this.storageService.updateKeywords(command.additionalContext.keywords);
      }
      break;
    case 'LIST_POSTS':
      // Handle listing posts
      break;
    case 'DELETE_POST':
      if (command.additionalContext?.postId) {
        await this.storageService.deletePost(command.additionalContext.postId);
      }
      break;
    case 'GENERATE_POSTS':
      // Handle post generation
      break;
    }
  }
} 