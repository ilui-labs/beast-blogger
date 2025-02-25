import type { ContentStructure } from '@types';
import type { ImageScenario } from '@types';
import type { KeywordAnalysis, SeoMetadata } from '@types';
import { FileStorageService } from './FileStorageService';
import type { StorageData } from '@types';
import fs from 'fs/promises';

export class StorageService {
  private storage: StorageData = {
    content: {
      posts: new Map(),
      drafts: new Map()
    },
    images: {
      generated: new Map()
    },
    seo: {
      keywords: [],
      keywordAnalytics: new Map(),
      metadata: new Map()
    },
    shopify: {
      uploadHistory: new Map()
    },
    settings: {}
  };

  private readonly storageFile = 'storage.json';
  private fileStorage: FileStorageService;

  constructor(baseDir: string = 'storage') {
    this.fileStorage = new FileStorageService(baseDir);
  }

  async load(): Promise<void> {
    try {
      const data = await fs.readFile(this.storageFile, 'utf8');
      const parsed = JSON.parse(data);
      
      this.storage = {
        content: {
          posts: new Map(parsed.content?.posts || []),
          drafts: new Map(parsed.content?.drafts || [])
        },
        images: {
          generated: new Map(parsed.images?.generated || [])
        },
        seo: {
          keywords: parsed.seo?.keywords || [],
          keywordAnalytics: new Map(parsed.seo?.keywordAnalytics || []),
          metadata: new Map(parsed.seo?.metadata || [])
        },
        shopify: {
          uploadHistory: new Map(parsed.shopify?.uploadHistory || [])
        },
        settings: parsed.settings || {}
      };
    } catch (error) {
      console.log('No existing storage found, starting fresh');
    }
  }

  async save(): Promise<void> {
    const data = JSON.stringify({
      content: {
        posts: Array.from(this.storage.content.posts.entries()),
        drafts: Array.from(this.storage.content.drafts.entries())
      },
      images: {
        generated: Array.from(this.storage.images.generated.entries())
      },
      seo: {
        keywords: this.storage.seo.keywords,
        keywordAnalytics: Array.from(this.storage.seo.keywordAnalytics.entries()),
        metadata: Array.from(this.storage.seo.metadata.entries())
      },
      shopify: {
        uploadHistory: Array.from(this.storage.shopify.uploadHistory.entries())
      },
      settings: this.storage.settings
    });
    await fs.writeFile(this.storageFile, data, 'utf8');
  }

  // Content Methods
  async getPost(id: string) {
    const post = this.storage.content.posts.get(id);
    if (!post) return null;

    // Load image URLs
    const imagesWithUrls = await Promise.all(
      post.images.map(async (img) => ({
        ...img,
        url: await this.fileStorage.getImageUrl(img.filename)
      }))
    );

    return {
      ...post,
      images: imagesWithUrls
    };
  }

  async updatePost(id: string, content: ContentStructure, imageUrls: string[]): Promise<void> {
    // Save images from URLs
    const savedImages = await Promise.all(
      imageUrls.map(async (url) => {
        const filename = await this.fileStorage.saveImageFromUrl(url);
        return {
          filename,
          alt: content.title, // Default alt text
          caption: content.title // Default caption
        };
      })
    );

    this.storage.content.posts.set(id, {
      content,
      images: savedImages,
      lastModified: new Date()
    });
    await this.save();
  }

  async deletePost(id: string): Promise<void> {
    const post = this.storage.content.posts.get(id);
    if (post) {
      // Delete associated images
      await Promise.all(
        post.images.map(img => this.fileStorage.deleteImage(img.filename))
      );
      this.storage.content.posts.delete(id);
      await this.save();
    }
  }

  // Image Methods
  async saveGeneratedImage(id: string, url: string, scenario: ImageScenario): Promise<string> {
    const filename = await this.fileStorage.saveImageFromUrl(url, { scenario });
    
    this.storage.images.generated.set(id, {
      filename,
      scenario,
      timestamp: new Date()
    });
    await this.save();

    return filename;
  }

  async getGeneratedImage(id: string) {
    const image = this.storage.images.generated.get(id);
    if (!image) return null;

    const url = await this.fileStorage.getImageUrl(image.filename);
    return { ...image, url };
  }

  // SEO Methods
  getKeywords(): string[] {
    return this.storage.seo.keywords;
  }

  async updateKeywords(keywords: string[]): Promise<void> {
    this.storage.seo.keywords = keywords;
    await this.save();
  }

  async getKeywordAnalytics(keyword: string): Promise<KeywordAnalysis & { timestamp: Date } | null> {
    const analysis = this.storage.seo.keywordAnalytics.get(keyword);
    if (!analysis) return null;
    
    // Ensure timestamp is a Date object
    return {
      ...analysis,
      timestamp: analysis.timestamp ? new Date(analysis.timestamp) : new Date()
    };
  }

  async saveKeywordAnalytics(keyword: string, analysis: KeywordAnalysis & { timestamp: Date }): Promise<void> {
    this.storage.seo.keywordAnalytics.set(keyword, analysis);
    await this.save();
  }

  async saveSeoMetadata(contentHash: string, metadata: SeoMetadata): Promise<void> {
    this.storage.seo.metadata.set(contentHash, metadata);
    await this.save();
  }

  async getSeoMetadata(contentHash: string): Promise<SeoMetadata | null> {
    const metadata = this.storage.seo.metadata.get(contentHash);
    return metadata || null;
  }

  // Shopify Methods
  async recordShopifyUpload(contentId: string, shopifyId: string, handle: string): Promise<void> {
    this.storage.shopify.uploadHistory.set(shopifyId, {
      contentId,
      shopifyId,
      handle,
      uploadedAt: new Date()
    });
    await this.save();
  }

  // Settings Methods
  getSettings() {
    return this.storage.settings;
  }

  async updateSettings(settings: Partial<StorageData['settings']>): Promise<void> {
    this.storage.settings = { ...this.storage.settings, ...settings };
    await this.save();
  }

  // Draft Methods
  async getDraft(topicHash: string): Promise<ContentStructure | null> {
    return this.storage.content.drafts.get(topicHash) || null;
  }

  async saveDraft(topicHash: string, content: ContentStructure): Promise<void> {
    this.storage.content.drafts.set(topicHash, content);
    await this.save();
  }

  async deleteDraft(topicHash: string): Promise<void> {
    this.storage.content.drafts.delete(topicHash);
    await this.save();
  }

  async listDrafts(): Promise<Array<{ hash: string; content: ContentStructure }>> {
    return Array.from(this.storage.content.drafts.entries()).map(([hash, content]) => ({
      hash,
      content
    }));
  }
} 