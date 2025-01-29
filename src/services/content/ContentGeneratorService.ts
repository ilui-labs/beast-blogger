import { HfInference } from '@huggingface/inference';
import { SEOMetadata } from '../seo/types';
import * as cheerio from 'cheerio';

export interface ContentStructure {
  title: string;
  excerpt: string;
  content: string;
  metadata: SEOMetadata;
  sources: Array<{
    url: string;
    name: string;
    citation: string;
  }>;
  links: Array<{
    url: string;
    text: string;
    isInternal: boolean;
  }>;
}

export class ContentGeneratorService {
  private hf: HfInference;
  private model: string = 'deepseek-ai/DeepSeek-V3';
  private persona: string = 'Write in a tone that is quirky, witty, very irreverent, and love sharing the benefits of Beast Putty and some total bullshit.';

  constructor(apiKey: string) {
    this.hf = new HfInference(apiKey);
  }

  async evaluateContent(topic: string, keywords: string[]): Promise<ContentStructure> {
    try {
      const prompt = `Create a blog post about: ${topic}\nKeywords: ${keywords.join(', ')}\n\nProvide:\n1. An engaging title\n2. A brief excerpt (max 160 chars)\n3. 3-4 key points to cover\n4. Suggested sources or references\n\nFormat as:\nTitle: [title]\nExcerpt: [excerpt]\nKey Points:\n- [point 1]\n- [point 2]\netc.\n\nSources:\n- [source name] - [url]`;

      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: prompt,
        parameters: {
          max_new_tokens: 800,
          temperature: 0.7
        }
      });

      const aiResponse = response.generated_text;
      
      // Parse the AI response
      const titleMatch = aiResponse.match(/Title:\s*([^\n]+)/);
      const excerptMatch = aiResponse.match(/Excerpt:\s*([^\n]+)/);
      const sourcesMatch = aiResponse.match(/Sources:[\s\S]*$/);

      const sources = sourcesMatch ? sourcesMatch[0]
        .split('\n')
        .slice(1)
        .filter(line => line.trim())
        .map(line => {
          const [name, url] = line.replace(/^-\s*/, '').split('-').map(s => s.trim());
          return {
            name: name || 'Reference',
            url: url || '#',
            citation: line.trim()
          };
        }) : [];

      return {
        title: titleMatch ? titleMatch[1].trim() : topic,
        excerpt: excerptMatch ? excerptMatch[1].trim() : '',
        content: '',
        metadata: {
          title: '',
          description: '',
          keywords
        },
        sources,
        links: []
      };
    } catch (error) {
      console.error('Error evaluating content:', error);
      throw error;
    }
  }

  private logger = console;

  private async validateUrl(url: string): Promise<boolean> {
    if (url.startsWith('#')) {
      return true; // Allow anchor links
    }

    try {
      const urlObj = new URL(url);
      if (!(urlObj.protocol === 'http:' || urlObj.protocol === 'https:')) {
        this.logger.warn(`Invalid protocol: ${urlObj.protocol}`);
        return false;
      }

      const response = await fetch(url, { 
        method: 'HEAD',
        headers: {
          'User-Agent': 'BeastBlogger/1.0'
        }
      });
      return response.ok;
    } catch (error) {
      this.logger.warn(`Failed to validate URL ${url}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }

  private async getInternalLinks(): Promise<Array<{ title: string; url: string; description: string }>> {
    try {
      const blog_url = 'https://www.beastputty.com/blogs/molding-destiny';
      const response = await fetch(blog_url, {
        headers: {
          'User-Agent': 'BeastBlogger/1.0'
        }
      });
      
      if (!response.ok) {
        this.logger.error(`Failed to fetch blog posts: ${response.status}`);
        return [];
      }

      const text = await response.text();
      const internal_links: Array<{ title: string; url: string; description: string }> = [];
      
      // Import cheerio properly
      import * as cheerio from 'cheerio';
      const $ = cheerio.load(text);
      
      // Find all blog post links
      $('article').each((_, article) => {
        try {
          const $article = $(article);
          const $link = $article.find('a');
          if ($link.length) {
            const title = $link.text().trim();
            const url = `https://www.beastputty.com${$link.attr('href')}`;
            const excerpt = $article.find('p.excerpt').text().trim() || '';
            
            internal_links.push({
              title,
              url,
              description: excerpt
            });
          }
        } catch (error) {
          this.logger.warn(`Error parsing article: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
      });

      this.logger.info(`Found ${internal_links.length} internal blog posts`);
      return internal_links;

    } catch (error) {
      this.logger.error(`Error fetching internal links: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return [];
    }
  }

  private async searchAndValidateUrls(query: string): Promise<Array<{ url: string; title: string }>> {
    try {
      // Simulate search results for now - in production, integrate with a real search API
      const searchResults = [
        { url: 'https://example.com/1', title: 'Example 1' },
        { url: 'https://example.com/2', title: 'Example 2' },
        { url: 'https://example.com/3', title: 'Example 3' },
      ];

      const validatedResults = await Promise.all(
        searchResults.map(async (result) => {
          const isValid = await this.validateUrl(result.url);
          return isValid ? result : null;
        })
      );

      return validatedResults.filter(Boolean) as Array<{ url: string; title: string }>;
    } catch (e) {
      this.logger.error(`Error searching and validating URLs: ${e}`);
      return [];
    }
  }

  async optimizeContent(content: ContentStructure): Promise<ContentStructure> {
    try {
      const prompt = `${this.persona}\n\nWrite a blog post with the following details:\n\nTitle: ${content.title}\nKeywords: ${content.metadata.keywords.join(', ')}\nKey Sources:\n${content.sources.map(s => `- ${s.name}`).join('\n')}\n\nProvide:\n1. Engaging, well-structured content\n2. Natural keyword integration\n3. Clear sections with proper HTML tags\n4. Internal linking suggestions\n\nFormat the content with proper HTML tags (<p>, <h2>, etc).`;

      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: prompt,
        parameters: {
          max_new_tokens: 2000,
          temperature: 0.8
        }
      });

      // Extract internal linking suggestions if provided
      const linkSuggestions = response.generated_text
        .match(/Links?:([\s\S]+?)(?=\n\n|$)/i)?.[1]
        .split('\n')
        .filter(line => line.includes('|'))
        .map(line => {
          const [text, path] = line.split('|').map(s => s.trim());
          const url = path || `#${text.toLowerCase().replace(/\s+/g, '-')}`;
          return {
            text: text.replace(/^[-*]\s*/, ''),
            url,
            isInternal: url.startsWith('#') || url.startsWith('/')
          };
        }) || [];

      // Validate links
      const validatedLinks = await Promise.all(
        linkSuggestions.map(async (link) => {
          const isValid = await this.validateUrl(link.url);
          return isValid ? link : null;
        })
      );

      // Validate sources
      const validatedSources = await Promise.all(
        content.sources.map(async (source) => {
          const isValid = await this.validateUrl(source.url);
          return isValid ? source : { ...source, url: '#' };
        })
      );

      // Clean up the content by removing the Links section
      const cleanContent = response.generated_text.replace(/Links?:[\s\S]+?(?=\n\n|$)/i, '').trim();

      return {
        ...content,
        content: cleanContent,
        links: validatedLinks.filter(Boolean),
        sources: validatedSources,
        metadata: await this.generateSEOMetadata(content.title, cleanContent)
      };
    } catch (error) {
      console.error('Error optimizing content:', error);
      throw error;
    }
  }

  private async generateSEOMetadata(title: string, content: string): Promise<SEOMetadata> {
    try {
      const prompt = `Generate SEO metadata for:\nTitle: ${title}\n\nContent Preview: ${content.substring(0, 500)}...\n\nProvide:\n- SEO Title (max 60 chars)\n- Meta Description (max 160 chars)\n\nFormat as:\nTitle: [title]\nDescription: [description]`;
      
      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: prompt,
        parameters: {
          max_new_tokens: 200,
          temperature: 0.5
        }
      });

      const aiResponse = response.generated_text;
      const titleMatch = aiResponse.match(/Title:\s*([^\n]+)/);
      const descriptionMatch = aiResponse.match(/Description:\s*([^\n]+)/);

      return {
        title: titleMatch ? titleMatch[1].trim().substring(0, 60) : title,
        description: descriptionMatch ? descriptionMatch[1].trim().substring(0, 160) : '',
        keywords: content.metadata.keywords
      };
    } catch (error) {
      console.error('Error generating SEO metadata:', error);
      throw error;
    }
  }
}