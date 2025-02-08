import { ContentStructure, ContentGeneratorService } from '../content/ContentGeneratorService';
import { EmailCommand, EmailService } from './EmailService';
import { EmailRevisionService } from './EmailRevisionService';
import { ImageHandlerService, ImageScenario } from '../image/ImageHandlerService';
import { ShopifyUploaderService } from '../shopify/ShopifyUploaderService';

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
  private readonly adminEmail = process.env.ADMIN_EMAIL || 'jackson@beastputty.com';

  constructor(
    private emailService: EmailService,
    private revisionService: EmailRevisionService,
    private shopifyUploader: ShopifyUploaderService,
    private imageService: ImageHandlerService,
    private contentService: ContentGeneratorService
  ) {
    this.setupCommandListeners();
  }

  private setupCommandListeners(): void {
    this.emailService.on('command', async (command: EmailCommand) => {
      try {
        await this.handleCommand(command);
      } catch (error) {
        await this.handleError('Command Processing Error', error, { command });
      }
    });
  }

  private async handleCommand(command: EmailCommand): Promise<void> {
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
    try {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const errorStack = error instanceof Error ? error.stack : undefined;
      
      const emailHtml = `
        <h1>⚠️ Beast Blogger Error: ${title}</h1>
        <h2>Error Details</h2>
        <p><strong>Message:</strong> ${errorMessage}</p>
        ${errorStack ? `<h3>Stack Trace</h3><pre>${errorStack}</pre>` : ''}
        ${metadata ? `
          <h3>Additional Context</h3>
          <pre>${JSON.stringify(metadata, null, 2)}</pre>
        ` : ''}
        <hr>
        <p>Timestamp: ${new Date().toISOString()}</p>
      `;

      await this.emailService.sendEmail({
        from: process.env.EMAIL_FROM || 'beastblogger@beastputty.com',
        to: this.adminEmail,
        subject: `🚨 Beast Blogger Error: ${title}`,
        body: `Error: ${errorMessage}\n\nMetadata: ${JSON.stringify(metadata, null, 2)}`,
        html: emailHtml
      });

      console.error(`Error notification sent to ${this.adminEmail}:`, {
        title,
        error: errorMessage,
        metadata
      });
    } catch (sendError) {
      // If we can't send the error email, at least log it
      console.error('Failed to send error notification:', sendError);
      console.error('Original error:', error);
      console.error('Error metadata:', metadata);
    }
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
} 