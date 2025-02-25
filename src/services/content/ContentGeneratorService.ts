import { ChatOpenAI } from '@langchain/openai';
import { PromptTemplate } from '@langchain/core/prompts';
import { StructuredOutputParser } from 'langchain/output_parsers';
import { z } from 'zod';
import { CheerioWebBaseLoader } from '@langchain/community/document_loaders/web/cheerio';
import { StorageService } from '../storage/StorageService';
import { createHash } from 'crypto';
import type { ContentStructure, ValidatedLink } from '@types';

export class ContentGeneratorService {
  private llm: ChatOpenAI;
  private persona: string = 'Write in a tone that is quirky, witty, very irreverent, and love sharing the benefits of Beast Putty and some total bullshit.';
  private readonly internalDomain = 'www.beastputty.com';

  constructor(
    openAiKey: string,
    private storageService: StorageService
  ) {
    this.llm = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.8,
      openAIApiKey: openAiKey,
    });
  }

  private async validateUrl(url: string): Promise<boolean> {
    if (url.startsWith('#')) {
      return true; // Allow anchor links
    }

    try {
      const urlObj = new URL(url);
      if (!(urlObj.protocol === 'http:' || urlObj.protocol === 'https:')) {
        console.warn(`Invalid protocol: ${urlObj.protocol}`);
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
      console.warn(`Failed to validate URL ${url}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }

  private async getInternalLinks(): Promise<Array<{ url: string; text: string; }>> {
    try {
      const loader = new CheerioWebBaseLoader(
        'https://www.beastputty.com/blogs/molding-destiny',
        {
          selector: 'article'
        }
      );
      
      const docs = await loader.load();
      const links: Array<{ url: string; text: string; }> = [];

      for (const doc of docs) {
        const cheerio = doc.metadata.cheerio;
        if (cheerio) {
          const $article = cheerio('article');
          const $link = $article.find('a');
          if ($link.length) {
            const text = $link.text().trim();
            const url = `https://www.beastputty.com${$link.attr('href')}`;
            links.push({ url, text });
          }
        }
      }

      return links;
    } catch (error) {
      console.error('Error fetching internal links:', error instanceof Error ? error.message : 'Unknown error');
      return [];
    }
  }

  private async validateLinks(links: Array<{ url: string; text: string; }>): Promise<ValidatedLink[]> {
    const validatedLinks = await Promise.all(
      links.map(async (link) => {
        const isValid = await this.validateUrl(link.url);
        const isInternal = link.url.includes(this.internalDomain) || link.url.startsWith('/') || link.url.startsWith('#');
        return {
          ...link,
          isValid,
          isInternal
        };
      })
    );

    return validatedLinks.filter(link => link.isValid);
  }

  async generateContent(topic: string, keywords: string[]): Promise<ContentStructure> {
    try {
      // Check if we have a draft for this topic
      const topicHash = this.hashContent(topic + keywords.join(','));
      const existingDraft = await this.storageService.getDraft(topicHash);
      if (existingDraft) {
        return existingDraft;
      }

      // First, get relevant internal links
      const internalLinks = await this.getInternalLinks();
      const validatedInternalLinks = await this.validateLinks(internalLinks);

      const parser = StructuredOutputParser.fromZodSchema(
        z.object({
          title: z.string(),
          excerpt: z.string().max(160),
          content: z.string(),
          keywords: z.array(z.string()),
          suggestedLinks: z.array(z.object({
            url: z.string(),
            text: z.string()
          }))
        })
      );

      const prompt = new PromptTemplate({
        template: `{persona}

Write a blog post about: {topic}
Keywords to include: {keywords}

Available internal links to reference:
{internalLinks}

The content should:
1. Be engaging and humorous
2. Use only basic HTML tags (h1-h6, p, a, b, i)
3. Include at least 2-3 relevant internal links from the provided list
4. Be well-structured with clear sections

Provide a JSON object with:
- title: A catchy title
- excerpt: A brief summary (max 160 characters)
- content: The full HTML content using only h1-h6, p, a, b, and i tags
- keywords: An array of relevant keywords used
- suggestedLinks: Array of links to include, using the format { url, text }

{format_instructions}`,
        inputVariables: ['persona', 'topic', 'keywords', 'internalLinks'],
        partialVariables: {
          format_instructions: parser.getFormatInstructions(),
        },
      });

      const input = await prompt.format({
        persona: this.persona,
        topic,
        keywords: keywords.join(', '),
        internalLinks: validatedInternalLinks.map(link => `- ${link.text} (${link.url})`).join('\n')
      });

      const response = await this.llm.invoke(input);
      const parsed = await parser.parse(response.content.toString());

      // Validate suggested links
      const validatedSuggestedLinks = await this.validateLinks(parsed.suggestedLinks);

      // Replace link placeholders in content with validated links
      let finalContent = parsed.content;
      for (const link of validatedSuggestedLinks) {
        const placeholder = `{{link:${link.text}}}`;
        const htmlLink = `<a href="${link.url}">${link.text}</a>`;
        finalContent = finalContent.replace(placeholder, htmlLink);
      }

      const content: ContentStructure = {
        title: parsed.title,
        excerpt: parsed.excerpt,
        content: finalContent,
        metadata: {
          keywords: parsed.keywords
        },
        links: validatedSuggestedLinks
      };

      // Store as draft
      await this.storageService.saveDraft(topicHash, content);

      return content;
    } catch (error) {
      console.error('Error generating content:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to generate content');
    }
  }

  private hashContent(content: string): string {
    return createHash('sha256').update(content).digest('hex');
  }
}