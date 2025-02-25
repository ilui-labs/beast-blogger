import { ChatOpenAI } from '@langchain/openai';
import { PromptTemplate } from '@langchain/core/prompts';
import { StructuredOutputParser } from 'langchain/output_parsers';
import { z } from 'zod';
import OpenAI from 'openai';
import { StorageService } from '../storage/StorageService';
import { ContentStructure, ImageScenario, GeneratedImage } from '@types';

export class ImageHandlerService {
  private llm: ChatOpenAI;
  private openai: OpenAI;
  private persona: string = 'You are a creative director who loves absurd humor and finding ways to connect Beast Putty to everyday situations in the most ridiculous ways possible.';

  constructor(
    openAiKey: string,
    private storageService: StorageService
  ) {
    this.llm = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.9,
      openAIApiKey: openAiKey,
    });

    this.openai = new OpenAI({
      apiKey: openAiKey,
    });
  }

  async generateScenario(content: ContentStructure): Promise<ImageScenario> {
    try {
      const parser = StructuredOutputParser.fromZodSchema(
        z.object({
          description: z.string(),
          prompt: z.string(),
          relevantKeywords: z.array(z.string()),
          absurdityLevel: z.number().min(1).max(10),
          beastPuttyConnection: z.string(),
        })
      );

      const prompt = new PromptTemplate({
        template: `{persona}

Create an absurd scenario for an image based on this blog post:
Title: {title}
Keywords: {keywords}

The scenario should:
1. Be completely ridiculous and unexpected
2. Incorporate Beast Putty in a creative way
3. Relate to the blog content theme
4. Be visually interesting

{format_instructions}`,
        inputVariables: ['persona', 'title', 'keywords'],
        partialVariables: {
          format_instructions: parser.getFormatInstructions(),
        },
      });

      const input = await prompt.format({
        persona: this.persona,
        title: content.title,
        keywords: content.metadata.keywords.join(', '),
      });

      const response = await this.llm.invoke(input);
      return await parser.parse(response.content.toString());
    } catch (error) {
      console.error('Error generating image scenario:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to generate image scenario');
    }
  }

  async generateImage(scenario: ImageScenario): Promise<GeneratedImage> {
    try {
      const prompt = `Create a creative and absurd image that captures this scenario:
${scenario.description}

Specific details:
${scenario.prompt}

Make sure to incorporate these elements:
- Beast Putty connection: ${scenario.beastPuttyConnection}
- Keywords: ${scenario.relevantKeywords.join(', ')}
- Absurdity Level: ${scenario.absurdityLevel}/10

Style: Digital art style, vibrant colors, neon colors, high detail, surreal`;

      const response = await this.openai.images.generate({
        model: 'dall-e-3',
        prompt,
        n: 1,
        size: '1024x1024',
        quality: 'standard',
        style: 'vivid'
      });

      if (!response.data || response.data.length === 0) {
        throw new Error('Failed to generate image');
      }

      const imageUrl = response.data[0].url;
      if (!imageUrl) {
        throw new Error('No image URL in response');
      }

      // Store the generated image
      const imageId = `img_${Date.now()}_${Math.random().toString(36).substring(2)}`;
      await this.storageService.saveGeneratedImage(imageId, imageUrl, scenario);

      return {
        url: await this.storageService.getGeneratedImage(imageId).then(img => img!.url),
        alt: scenario.description,
        caption: `${scenario.description} - ${scenario.beastPuttyConnection}`,
        scenario
      };
    } catch (error) {
      console.error('Error generating image:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to generate image');
    }
  }

  async enhanceContentWithImages(content: ContentStructure): Promise<ContentStructure> {
    try {
      const scenario = await this.generateScenario(content);
      const image = await this.generateImage(scenario);

      const enhancedContent = { 
        ...content,
        images: [
          ...(content.images || []),
          {
            url: image.url,
            alt: image.alt,
            caption: image.caption
          }
        ],
        htmlContent: content.htmlContent || content.content
      };

      // Add image reference to HTML content
      const imageHtml = `
        <figure class="content-image">
          <img src="${image.url}" alt="${image.alt}" loading="lazy" />
          <figcaption>${image.caption}</figcaption>
        </figure>
      `;

      // Insert the image after the first section
      const insertPoint = enhancedContent.htmlContent.indexOf('</section>');
      if (insertPoint !== -1) {
        enhancedContent.htmlContent = 
          enhancedContent.htmlContent.slice(0, insertPoint + 9) + 
          imageHtml + 
          enhancedContent.htmlContent.slice(insertPoint + 9);
      }

      return enhancedContent;
    } catch (error) {
      console.error('Error enhancing content with images:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to enhance content with images');
    }
  }
}