import { HfInference } from '@huggingface/inference';

export interface SEOAnalysisResult {
  keywords: string[];
  competitionScore: number;
  searchVolume: number;
  rankingPotential: number;
  suggestions: string[];
}

export class SEOHandler {
  private hf: HfInference;

  constructor(hfClient: HfInference) {
    this.hf = hfClient;
  }

  async analyzeKeywords(targetKeywords: string[]): Promise<SEOAnalysisResult> {
    try {
      const analysis: SEOAnalysisResult = {
        keywords: targetKeywords,
        competitionScore: 0,
        searchVolume: 0,
        rankingPotential: 0,
        suggestions: []
      };

      // Analyze each keyword and aggregate results
      const results = await Promise.all(targetKeywords.map(async (keyword) => {
        const response = await this.hf.textGeneration({
          model: 'deepseek-ai/janus-pro',
          inputs: `Analyze SEO metrics for: ${keyword}\n\nProvide:\n- Competition Score (0-100)\n- Monthly Search Volume (0-100)\n- Ranking Potential (0-100)\n- Related Keywords`,
          parameters: {
            max_new_tokens: 200,
            temperature: 0.7
          }
        });

        const aiResponse = response.generated_text.toLowerCase();
        
        const competitionMatch = aiResponse.match(/competition.*?(\d+)/i);
        const volumeMatch = aiResponse.match(/volume.*?(\d+)/i);
        const potentialMatch = aiResponse.match(/potential.*?(\d+)/i);
        const suggestionsMatch = aiResponse.match(/related keywords:?([^\n]+)/i);

        return {
          competition: competitionMatch ? parseInt(competitionMatch[1]) : 0,
          volume: volumeMatch ? parseInt(volumeMatch[1]) : 0,
          potential: potentialMatch ? parseInt(potentialMatch[1]) : 0,
          suggestions: suggestionsMatch ? suggestionsMatch[1].split(',').map(s => s.trim()) : []
        };
      }));

      // Calculate average scores
      analysis.competitionScore = Math.round(results.reduce((sum, r) => sum + r.competition, 0) / results.length);
      analysis.searchVolume = Math.round(results.reduce((sum, r) => sum + r.volume, 0) / results.length);
      analysis.rankingPotential = Math.round(results.reduce((sum, r) => sum + r.potential, 0) / results.length);
      
      // Collect unique suggestions
      analysis.suggestions = Array.from(new Set(
        results.flatMap(r => r.suggestions)
      )).slice(0, 10); // Limit to top 10 suggestions

      return analysis;
    } catch (error) {
      console.error('Error analyzing keywords:', error);
      throw error;
    }
  }

  async evaluateCompetition(keyword: string): Promise<number> {
    try {
      const response = await this.hf.textGeneration({
        model: 'deepseek-ai/janus-pro',
        inputs: `Evaluate competition level for keyword: ${keyword}\n\nAnalyze:\n- Domain Authority of ranking sites\n- Content quality\n- Backlink profiles\n\nProvide a competition score (0-100)`,
        parameters: {
          max_new_tokens: 150,
          temperature: 0.7
        }
      });

      const aiResponse = response.generated_text.toLowerCase();
      const scoreMatch = aiResponse.match(/score.*?(\d+)/i);
      
      return scoreMatch ? parseInt(scoreMatch[1]) : 50;
    } catch (error) {
      console.error('Error evaluating competition:', error);
      throw error;
    }
  }

  async findLongTailOpportunities(mainKeyword: string): Promise<string[]> {
    try {
      const response = await this.hf.textGeneration({
        model: 'deepseek-ai/janus-pro',
        inputs: `Discover long-tail keyword opportunities for: ${mainKeyword}\n\nConsider:\n- Search intent variations\n- Question formats\n- Specific modifiers\n- Location-based variations\n\nProvide 5 specific long-tail keywords`,
        parameters: {
          max_new_tokens: 200,
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
      console.error('Error finding long-tail opportunities:', error);
      throw error;
    }
  }
}