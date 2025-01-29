import { HfInference } from '@huggingface/inference';
import { ContentStructure } from '../content/ContentGeneratorService';

export interface ImageScenario {
  description: string;
  prompt: string;
  relevantKeywords: string[];
  absurdityLevel: number; // 1-10 scale
  beastPuttyConnection: string;
}

export interface GeneratedImage {
  url: string;
  alt: string;
  caption: string;
  scenario: ImageScenario;
}

export class ImageHandlerService {
  private hf: HfInference;
  private model: string = 'deepseek-ai/janus-pro';
  private persona: string = 'You are a creative director who loves absurd humor and finding ways to connect Beast Putty to everyday situations in the most ridiculous ways possible.';

  constructor(apiKey: string) {
    this.hf = new HfInference(apiKey);
  }

  async generateScenario(content: ContentStructure): Promise<ImageScenario> {
    try {
      const prompt = `${this.persona}\n\nCreate an absurd scenario for an image based on this blog post:\nTitle: ${content.title}\nKeywords: ${content.metadata.keywords.join(', ')}\n\nThe scenario should:\n1. Be completely ridiculous and unexpected\n2. Incorporate Beast Putty in a creative way\n3. Relate to the blog content theme\n4. Be visually interesting\n\nFormat the response as:\nDescription: [brief scenario description]\nPrompt: [detailed image generation prompt]\nKeywords: [relevant keywords]\nAbsurdity Level: [1-10]\nBeast Putty Connection: [how Beast Putty fits in]`;

      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: prompt,
        parameters: {
          max_new_tokens: 500,
          temperature: 0.9
        }
      });

      const aiResponse = response.generated_text;
      
      // Parse the response
      const descriptionMatch = aiResponse.match(/Description:\s*([^\n]+)/);
      const promptMatch = aiResponse.match(/Prompt:\s*([^\n]+)/);
      const keywordsMatch = aiResponse.match(/Keywords:\s*([^\n]+)/);
      const absurdityMatch = aiResponse.match(/Absurdity Level:\s*(\d+)/);
      const connectionMatch = aiResponse.match(/Beast Putty Connection:\s*([^\n]+)/);

      return {
        description: descriptionMatch ? descriptionMatch[1].trim() : '',
        prompt: promptMatch ? promptMatch[1].trim() : '',
        relevantKeywords: keywordsMatch ? keywordsMatch[1].split(',').map(k => k.trim()) : [],
        absurdityLevel: absurdityMatch ? parseInt(absurdityMatch[1]) : 5,
        beastPuttyConnection: connectionMatch ? connectionMatch[1].trim() : ''
      };
    } catch (error) {
      console.error('Error generating image scenario:', error);
      throw error;
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
- Absurdity Level: ${scenario.absurdityLevel}/10`;

      const response = await this.hf.textToImage({
        model: this.model,
        inputs: prompt,
        parameters: {
          negative_prompt: "blurry, low quality, distorted, unrealistic",
          num_inference_steps: 50,
          guidance_scale: 7.5
        }
      });

      if (!response) {
        throw new Error('Failed to generate image');
      }

      // Convert the image to base64 URL
      const imageUrl = `data:image/jpeg;base64,${response}`;

      return {
        url: imageUrl,
        alt: scenario.description,
        caption: `${scenario.description} - ${scenario.beastPuttyConnection}`,
        scenario
      };
    } catch (error) {
      console.error('Error generating image:', error);
      throw error;
    }
  }

  async enhanceContentWithImages(content: ContentStructure): Promise<ContentStructure> {
    try {
      const scenario = await this.generateScenario(content);
      const image = await this.generateImage(scenario);

      const enhancedContent = { ...content };
      enhancedContent.images = [
        ...enhancedContent.images,
        {
          url: image.url,
          alt: image.alt,
          caption: image.caption
        }
      ];

      // Add image reference to HTML content
      const imageHtml = `
        <figure class="content-image">
          <img src="${image.url}" alt="${image.alt}" />
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
      console.error('Error enhancing content with images:', error);
      throw error;
    }
  }
}