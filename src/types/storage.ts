import { ContentStructure } from './content';
import { ImageScenario } from './image';
import { KeywordAnalysis, SeoMetadata } from './seo';

export interface StorageData {
  content: {
    posts: Map<string, {
      content: ContentStructure;
      images: Array<{
        filename: string;
        alt: string;
        caption: string;
      }>;
      lastModified: Date;
    }>;
    drafts: Map<string, ContentStructure>;
  };
  images: {
    generated: Map<string, {
      filename: string;
      scenario: ImageScenario;
      timestamp: Date;
    }>;
  };
  seo: {
    keywords: string[];
    keywordAnalytics: Map<string, KeywordAnalysis>;
    metadata: Map<string, SeoMetadata>;
  };
  shopify: {
    uploadHistory: Map<string, {
      contentId: string;
      shopifyId: string;
      handle: string;
      uploadedAt: Date;
    }>;
  };
  settings: {
    defaultTone?: string;
    defaultUrgency?: 'low' | 'medium' | 'high';
    autoPublish?: boolean;
    imageGeneration?: {
      defaultAbsurdityLevel: number;
      defaultStyle: string;
    };
    seo?: {
      minSearchVolume: number;
      targetKeywords: string[];
    };
  };
}

export interface ImageMetadata {
  scenario?: unknown;
  timestamp: string;
  [key: string]: unknown;
} 