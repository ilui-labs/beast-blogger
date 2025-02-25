import type { ContentStructure } from '@types';
import type { EmailCommand, RevisionRequest } from '@types';

export class EmailRevisionService {
  private revisions: Map<string, RevisionRequest[]>;

  constructor() {
    this.revisions = new Map();
  }

  async createRevision(contentId: string, content: ContentStructure, command: EmailCommand): Promise<RevisionRequest> {
    const revisionRequest: RevisionRequest = {
      id: `rev_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      content,
      command,
      timestamp: new Date(),
      status: 'pending',
      metadata: {
        commandContext: command.additionalContext
      }
    };

    // Store the revision
    const existingRevisions = this.revisions.get(contentId) || [];
    this.revisions.set(contentId, [...existingRevisions, revisionRequest]);

    return revisionRequest;
  }

  async updateRevisionStatus(
    contentId: string, 
    revisionId: string, 
    status: RevisionRequest['status'],
    metadata?: Partial<RevisionRequest['metadata']>
  ): Promise<RevisionRequest | null> {
    const revisions = this.revisions.get(contentId);
    if (!revisions) return null;

    const revisionIndex = revisions.findIndex(rev => rev.id === revisionId);
    if (revisionIndex === -1) return null;

    const startTime = revisions[revisionIndex].timestamp.getTime();
    const processingTime = Date.now() - startTime;

    const updatedRevision = {
      ...revisions[revisionIndex],
      status,
      metadata: {
        ...revisions[revisionIndex].metadata,
        ...metadata,
        processingTime
      }
    };

    revisions[revisionIndex] = updatedRevision;
    this.revisions.set(contentId, revisions);

    return updatedRevision;
  }

  async getRevisionHistory(contentId: string): Promise<RevisionRequest[]> {
    return this.revisions.get(contentId) || [];
  }

  async getLatestRevision(contentId: string): Promise<RevisionRequest | null> {
    const revisions = this.revisions.get(contentId) || [];
    return revisions.length > 0 ? revisions[revisions.length - 1] : null;
  }

  async getRevision(contentId: string, revisionId: string): Promise<RevisionRequest | null> {
    const revisions = this.revisions.get(contentId);
    if (!revisions) return null;

    return revisions.find(rev => rev.id === revisionId) || null;
  }

  async getRevisionsByStatus(contentId: string, status: RevisionRequest['status']): Promise<RevisionRequest[]> {
    const revisions = this.revisions.get(contentId) || [];
    return revisions.filter(rev => rev.status === status);
  }

  async getAverageProcessingTime(contentId: string): Promise<number | null> {
    const revisions = this.revisions.get(contentId) || [];
    const completedRevisions = revisions.filter(rev => 
      rev.status === 'completed' && rev.metadata?.processingTime
    );

    if (completedRevisions.length === 0) return null;

    const totalTime = completedRevisions.reduce(
      (sum, rev) => sum + (rev.metadata?.processingTime || 0), 
      0
    );

    return totalTime / completedRevisions.length;
  }
} 