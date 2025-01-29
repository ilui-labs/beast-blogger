import { HfInference } from '@huggingface/inference';

export interface KeywordAnalysis {
  keyword: string;
  searchVolume: number;
  competition: number;
  organicRankingPotential: number;
}

export interface SeoMetadata {
  title: string;
  description: string;
  keywords: string[];
  canonicalUrl?: string;
}

export class SeoHandlerService {
  private hf: HfInference;
  private model: string = 'deepseek-ai/janus-pro';

  constructor(hfClient: HfInference) {
    this.hf = hfClient;
  }

  async analyzeKeyword(keyword: string): Promise<KeywordAnalysis> {
    try {
      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: `Analyze the SEO potential for the keyword: ${keyword}\n\nProvide scores for:\n- Search Volume (0-100)\n- Competition (0-100)\n- Organic Ranking Potential (0-100)`,
        parameters: {
          max_new_tokens: 100,
          temperature: 0.7
        }
      });

      const aiResponse = response.generated_text.toLowerCase();
      
      const searchVolumeMatch = aiResponse.match(/search volume.*?(\d+)/i);
      const competitionMatch = aiResponse.match(/competition.*?(\d+)/i);
      const potentialMatch = aiResponse.match(/ranking potential.*?(\d+)/i);

      return {
        keyword,
        searchVolume: searchVolumeMatch ? parseInt(searchVolumeMatch[1]) : 0,
        competition: competitionMatch ? parseInt(competitionMatch[1]) : 0,
        organicRankingPotential: potentialMatch ? parseInt(potentialMatch[1]) : 0
      };
    } catch (error) {
      console.error('Error analyzing keyword:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to analyze keyword');
    }
  }

  async generateSeoMetadata(content: string): Promise<SeoMetadata> {
    try {
      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: `Generate SEO metadata for the following content:\n${content}\n\nProvide:\n- Title (max 60 chars)\n- Description (max 160 chars)\n- Keywords (comma-separated)`,
        parameters: {
          max_new_tokens: 200,
          temperature: 0.7
        }
      });

      const aiResponse = response.generated_text;
      
      const titleMatch = aiResponse.match(/Title:?\s*([^\n]+)/i);
      const descriptionMatch = aiResponse.match(/Description:?\s*([^\n]+)/i);
      const keywordsMatch = aiResponse.match(/Keywords:?\s*([^\n]+)/i);

      return {
        title: titleMatch ? titleMatch[1].trim().substring(0, 60) : '',
        description: descriptionMatch ? descriptionMatch[1].trim().substring(0, 160) : '',
        keywords: keywordsMatch ? keywordsMatch[1].split(',').map(k => k.trim()) : []
      };
    } catch (error) {
      console.error('Error generating SEO metadata:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to generate SEO metadata');
    }
  }

  async findLongTailKeywords(mainKeyword: string): Promise<string[]> {
    try {
      const response = await this.hf.textGeneration({
        model: this.model,
        inputs: `Generate 5 long-tail keyword variations for: ${mainKeyword}\n\nConsider:\n- Search intent\n- Question-based queries\n- Specific modifiers`,
        parameters: {
          max_new_tokens: 150,
          temperature: 0.8
        }
      });

      const aiResponse = response.generated_text;
      return aiResponse
        .split('\n')
        .filter(line => line.trim().length > 0)
        .map(line => line.replace(/^\d+\.\s*/, '').trim())
        .filter(keyword => keyword.length > 0)
        .slice(0, 5);
    } catch (error) {
      console.error('Error finding long-tail keywords:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to find long-tail keywords');
    }
  }
}