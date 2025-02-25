export interface ContentStructure {
  title: string;
  excerpt: string;
  content: string;
  metadata: {
    keywords: string[];
    rejectionHistory?: Array<{
      timestamp: Date;
      feedback?: string;
      tone?: string;
      specificIssues?: string[];
      urgency?: 'low' | 'medium' | 'high';
    }>;
  };
  links: Array<{
    url: string;
    text: string;
    isInternal: boolean;
  }>;
  images?: Array<{
    url: string;
    alt: string;
    caption: string;
  }>;
  htmlContent?: string;
  shopifyData?: {
    id: string;
    handle: string;
    publishedAt: Date;
  };
}

export interface ValidatedLink {
  url: string;
  text: string;
  isValid: boolean;
  isInternal: boolean;
} 