import { ContentStructure } from '../content/ContentGeneratorService';

interface EmailTemplate {
  subject: string;
  body: string;
  previewText: string;
  contentPreview: ContentStructure;
}

interface FeedbackData {
  id: string;
  timestamp: Date;
  comments: Array<{
    section: string;
    comment: string;
    status: 'pending' | 'addressed' | 'rejected';
  }>;
}

interface RevisionData {
  id: string;
  version: number;
  timestamp: Date;
  changes: Array<{
    type: 'addition' | 'deletion' | 'modification';
    section: string;
    oldContent?: string;
    newContent?: string;
  }>;
  status: 'draft' | 'in_review' | 'approved' | 'rejected';
}

export class EmailPreviewService {
  private templates: Map<string, EmailTemplate>;
  private feedback: Map<string, FeedbackData[]>;
  private revisions: Map<string, RevisionData[]>;

  constructor() {
    this.templates = new Map();
    this.feedback = new Map();
    this.revisions = new Map();
  }

  async generatePreview(content: ContentStructure): Promise<EmailTemplate> {
    try {
      const template: EmailTemplate = {
        subject: `Content Review: ${content.title}`,
        previewText: `Please review the following content: ${content.title}`,
        body: this.formatContentForEmail(content),
        contentPreview: content
      };

      const templateId = this.generateTemplateId(content);
      this.templates.set(templateId, template);

      return template;
    } catch (error) {
      console.error('Error generating email preview:', error);
      throw error;
    }
  }

  async collectFeedback(templateId: string, feedback: Omit<FeedbackData, 'id' | 'timestamp'>): Promise<FeedbackData> {
    try {
      const feedbackData: FeedbackData = {
        id: this.generateFeedbackId(),
        timestamp: new Date(),
        ...feedback
      };

      const existingFeedback = this.feedback.get(templateId) || [];
      this.feedback.set(templateId, [...existingFeedback, feedbackData]);

      return feedbackData;
    } catch (error) {
      console.error('Error collecting feedback:', error);
      throw error;
    }
  }

  async trackRevision(templateId: string, changes: RevisionData['changes']): Promise<RevisionData> {
    try {
      const existingRevisions = this.revisions.get(templateId) || [];
      const newVersion = existingRevisions.length + 1;

      const revisionData: RevisionData = {
        id: this.generateRevisionId(),
        version: newVersion,
        timestamp: new Date(),
        changes,
        status: 'draft'
      };

      this.revisions.set(templateId, [...existingRevisions, revisionData]);

      return revisionData;
    } catch (error) {
      console.error('Error tracking revision:', error);
      throw error;
    }
  }

  async updateRevisionStatus(templateId: string, revisionId: string, status: RevisionData['status']): Promise<RevisionData> {
    try {
      const revisions = this.revisions.get(templateId);
      if (!revisions) {
        throw new Error('Template not found');
      }

      const revisionIndex = revisions.findIndex(rev => rev.id === revisionId);
      if (revisionIndex === -1) {
        throw new Error('Revision not found');
      }

      revisions[revisionIndex].status = status;
      this.revisions.set(templateId, revisions);

      return revisions[revisionIndex];
    } catch (error) {
      console.error('Error updating revision status:', error);
      throw error;
    }
  }

  private formatContentForEmail(content: ContentStructure): string {
    // Implement email formatting logic
    return `
      <h1>${content.title}</h1>
      ${content.sections.map((section: { heading: string; content: string }) => `
        <h2>${section.heading}</h2>
        <p>${section.content}</p>
      `).join('')}
    `;
  }

  private generateTemplateId(content: ContentStructure): string {
    return `template_${Date.now()}_${content.title.toLowerCase().replace(/\s+/g, '_')}`;
  }

  private generateFeedbackId(): string {
    return `feedback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateRevisionId(): string {
    return `revision_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}