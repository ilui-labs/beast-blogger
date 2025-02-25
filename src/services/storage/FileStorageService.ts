import fs from 'fs/promises';
import path from 'path';
import { createHash } from 'crypto';
import type { ImageMetadata } from '@types';

export class FileStorageService {
  private readonly baseDir: string;
  private readonly imageDir: string;

  constructor(baseDir: string = 'storage') {
    this.baseDir = baseDir;
    this.imageDir = path.join(this.baseDir, 'images');
    this.initializeDirectories();
  }

  private async initializeDirectories(): Promise<void> {
    try {
      await fs.mkdir(this.baseDir, { recursive: true });
      await fs.mkdir(this.imageDir, { recursive: true });
    } catch (error) {
      console.error('Error initializing storage directories:', error);
    }
  }

  async saveImageFromUrl(url: string, metadata: Record<string, unknown> = {}): Promise<string> {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`Failed to fetch image: ${response.statusText}`);

      const buffer = await response.arrayBuffer();
      const hash = createHash('sha256').update(Buffer.from(buffer)).digest('hex');
      const ext = this.getImageExtension(response.headers.get('content-type') || '');
      const filename = `${hash}${ext}`;
      const filePath = path.join(this.imageDir, filename);

      await fs.writeFile(filePath, Buffer.from(buffer));
      await this.saveImageMetadata(filename, metadata);

      return filename;
    } catch (error) {
      console.error('Error saving image:', error);
      throw error;
    }
  }

  async getImageUrl(filename: string): Promise<string> {
    const filePath = path.join(this.imageDir, filename);
    try {
      await fs.access(filePath);
      // In production, this would be your CDN or public URL
      return `/storage/images/${filename}`;
    } catch {
      throw new Error(`Image not found: ${filename}`);
    }
  }

  private async saveImageMetadata(filename: string, metadata: Record<string, unknown>): Promise<void> {
    const metadataPath = path.join(this.imageDir, `${filename}.meta.json`);
    await fs.writeFile(metadataPath, JSON.stringify({
      ...metadata,
      timestamp: new Date().toISOString()
    }));
  }

  async getImageMetadata(filename: string): Promise<ImageMetadata | null> {
    const metadataPath = path.join(this.imageDir, `${filename}.meta.json`);
    try {
      const data = await fs.readFile(metadataPath, 'utf8');
      return JSON.parse(data);
    } catch {
      return null;
    }
  }

  private getImageExtension(contentType: string): string {
    const extensions: Record<string, string> = {
      'image/jpeg': '.jpg',
      'image/png': '.png',
      'image/gif': '.gif',
      'image/webp': '.webp'
    };
    return extensions[contentType] || '.jpg';
  }

  async deleteImage(filename: string): Promise<void> {
    const filePath = path.join(this.imageDir, filename);
    const metadataPath = path.join(this.imageDir, `${filename}.meta.json`);
    
    try {
      await fs.unlink(filePath);
      await fs.unlink(metadataPath).catch(() => {}); // Ignore if metadata doesn't exist
    } catch (error) {
      console.error('Error deleting image:', error);
      throw error;
    }
  }
}