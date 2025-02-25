/**
 * @fileoverview SEO Handler Service for Beast Blogger
 * 
 * This service integrates with Google Search Console and Google Ads APIs to provide:
 * 1. Keyword Analysis
 * 2. Competitor Research
 * 3. SEO Metadata Generation
 * 4. Long-tail Keyword Discovery
 * 
 * The service works in conjunction with:
 * - StorageService: For caching analysis results
 * - ContentGeneratorService: For content optimization
 * - EmailService: For notifications and reports
 * 
 * Main outputs:
 * - Keyword Analysis: Search volume, competition, trends
 * - Competitor Data: Top competing URLs with metrics
 * - SEO Metadata: Optimized titles, descriptions, keywords
 * - Long-tail Keywords: Related keyword variations
 * 
 * @example Output Shapes:
 * ```json
 * // analyzeKeyword output
 * {
 *   "keyword": "beast putty benefits",
 *   "searchVolume": 1200,
 *   "competition": 0.65,
 *   "cpc": 1.25,
 *   "organicRankingPotential": 75,
 *   "trends": [
 *     { "month": "2024-01", "volume": 1100 },
 *     { "month": "2024-02", "volume": 1300 }
 *   ],
 *   "searchConsoleData": {
 *     "clicks": 45,
 *     "impressions": 1000,
 *     "ctr": 0.045,
 *     "position": 4.5
 *   },
 *   "competitors": [
 *     {
 *       "url": "https://competitor.com/putty",
 *       "title": "Benefits of Putty",
 *       "description": "Learn about putty benefits",
 *       "metrics": {
 *         "authority": 65,
 *         "backlinks": 120,
 *         "socialShares": 45
 *       }
 *     }
 *   ],
 *   "suggestions": [
 *     "beast putty for muscle recovery",
 *     "how to use beast putty"
 *   ]
 * }
 * 
 * // generateSeoMetadata output
 * {
 *   "title": "Beast Putty: Ultimate Guide to Benefits & Uses",
 *   "description": "Discover the amazing benefits of Beast Putty. Learn how this innovative therapy tool can improve muscle recovery, reduce stress & enhance workout results.",
 *   "keywords": ["beast putty", "muscle recovery", "therapy tool"]
 * }
 * 
 * // findLongTailKeywords output
 * [
 *   "beast putty for shoulder pain",
 *   "how to use beast putty for recovery",
 *   "beast putty vs therapy putty comparison",
 *   "best beast putty exercises for athletes",
 *   "beast putty resistance levels guide"
 * ]
 * ```
 */

import { ChatOpenAI } from '@langchain/openai';
import { PromptTemplate } from '@langchain/core/prompts';
import { StructuredOutputParser } from 'langchain/output_parsers';
import { z } from 'zod';
import { google, searchconsole_v1 } from 'googleapis';
import { GoogleAdsApi } from 'google-ads-api';
import { StorageService } from '../storage/StorageService';
import { createHash } from 'crypto';
import type {
  SearchAnalyticsRow,
  KeywordData,
  CompetitorData,
  KeywordAnalysis,
  SeoMetadata,
  DataSourceConfig
} from '@types';

interface GoogleClients {
  searchConsole: searchconsole_v1.Searchconsole;
  ads: GoogleAdsApi;
}

/**
 * SEO Handler Service
 * 
 * @remarks
 * This service is the central hub for all SEO-related operations in Beast Blogger.
 * It combines data from multiple sources to provide comprehensive SEO insights.
 * 
 * @example
 * ```typescript
 * const seoHandler = new SeoHandlerService(openai, storageService, config);
 * const analysis = await seoHandler.analyzeKeyword('beast putty benefits');
 * ```
 */
export class SeoHandlerService {
  private config: DataSourceConfig;
  private model: ChatOpenAI;
  private googleClients: GoogleClients | null = null;
  
  constructor(
    private openai: ChatOpenAI,
    private storageService: StorageService,
    config: DataSourceConfig
  ) {
    this.config = config;
    this.model = new ChatOpenAI({
      modelName: 'gpt-4',
      temperature: 0.7,
    });

    this.initializeGoogleClients().catch(error => {
      console.error('Failed to initialize Google clients:', error);
    });
  }

  private async initializeGoogleClients(): Promise<void> {
    if (!this.config.searchConsole?.credentials || !this.config.googleAds) {
      throw new Error('Search Console and Google Ads credentials are required');
    }

    const developerToken = process.env.GOOGLE_ADS_DEVELOPER_TOKEN;
    if (!developerToken) {
      throw new Error('Google Ads developer token is required');
    }

    try {
      const auth = new google.auth.GoogleAuth({
        credentials: this.config.searchConsole.credentials,
        scopes: ['https://www.googleapis.com/auth/webmasters.readonly']
      });

      const adsClient = new GoogleAdsApi({
        client_id: this.config.googleAds.clientId,
        client_secret: this.config.googleAds.clientSecret,
        developer_token: developerToken
      });

      this.googleClients = {
        searchConsole: google.searchconsole({ version: 'v1', auth }),
        ads: adsClient
      };
    } catch (error) {
      console.error('Failed to initialize Google clients:', error);
      throw new Error('Google API initialization failed');
    }
  }

  private ensureGoogleClients(): GoogleClients {
    if (!this.googleClients) {
      throw new Error('Google clients not initialized');
    }
    return this.googleClients;
  }

  /**
   * Analyzes a keyword for SEO potential
   * 
   * @param keyword - The keyword to analyze
   * @returns {Promise<KeywordAnalysis>} Analysis containing search metrics, competition data, and suggestions
   * 
   * @example Response Shape
   * ```json
   * {
   *   "keyword": "beast putty benefits",
   *   "searchVolume": 1200,
   *   "competition": 0.65,
   *   "cpc": 1.25,
   *   "organicRankingPotential": 75,
   *   "trends": [
   *     { "month": "2024-01", "volume": 1100 }
   *   ],
   *   "searchConsoleData": {
   *     "clicks": 45,
   *     "impressions": 1000,
   *     "ctr": 0.045,
   *     "position": 4.5
   *   },
   *   "competitors": [
   *     {
   *       "url": "https://competitor.com/putty",
   *       "title": "Benefits of Putty",
   *       "description": "Learn about putty benefits",
   *       "metrics": {
   *         "authority": 65,
   *         "backlinks": 120,
   *         "socialShares": 45
   *       }
   *     }
   *   ],
   *   "suggestions": [
   *     "beast putty for muscle recovery",
   *     "how to use beast putty"
   *   ]
   * }
   * ```
   */
  async analyzeKeyword(keyword: string): Promise<KeywordAnalysis> {
    const cachedAnalysis = await this.storageService.getKeywordAnalytics(keyword);
    if (cachedAnalysis && this.isAnalysisFresh(cachedAnalysis.timestamp)) {
      return cachedAnalysis;
    }

    const [keywordData, searchConsoleData, competitors] = await Promise.all([
      this.getKeywordPlannerData(keyword),
      this.getSearchConsoleData(
        keyword,
        new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        new Date().toISOString().split('T')[0]
      ),
      this.getCompetitorData(keyword)
    ]);

    const analysis: KeywordAnalysis = {
      keyword,
      searchVolume: keywordData.searchVolume,
      competition: keywordData.competition,
      cpc: keywordData.cpc,
      organicRankingPotential: this.calculateRankingPotential(keywordData, competitors),
      trends: keywordData.trends,
      searchConsoleData: searchConsoleData[0],
      competitors,
      suggestions: await this.generateKeywordSuggestions(keyword)
    };

    await this.storageService.saveKeywordAnalytics(keyword, {
      ...analysis,
      timestamp: new Date()
    });

    return analysis;
  }

  /**
   * Generates SEO metadata for content
   * 
   * @param content - The content to generate metadata for
   * @returns {Promise<SeoMetadata>} Optimized SEO metadata
   * 
   * @example Response Shape
   * ```json
   * {
   *   "title": "Beast Putty: Ultimate Guide to Benefits & Uses",
   *   "description": "Discover the amazing benefits of Beast Putty. Learn how this innovative therapy tool can improve muscle recovery, reduce stress & enhance workout results.",
   *   "keywords": ["beast putty", "muscle recovery", "therapy tool"]
   * }
   * ```
   */
  async generateSeoMetadata(content: string): Promise<SeoMetadata> {
    const parser = StructuredOutputParser.fromZodSchema(
      z.object({
        title: z.string().max(60),
        description: z.string().max(160),
        keywords: z.array(z.string()),
      })
    );

    const prompt = new PromptTemplate({
      template: `Generate SEO metadata for the following content:
{content}

Create a JSON object with:
- title: An engaging title (max 60 characters)
- description: A compelling meta description (max 160 characters)
- keywords: An array of relevant keywords

{format_instructions}`,
      inputVariables: ['content'],
      partialVariables: {
        format_instructions: parser.getFormatInstructions(),
      },
    });

    try {
      const input = await prompt.format({ content });
      const response = await this.model.invoke(input);
      const metadata = await parser.parse(response.content.toString());

      // Store metadata with content hash as key
      const contentHash = this.hashContent(content);
      await this.storageService.saveSeoMetadata(contentHash, metadata);

      return metadata;
    } catch (error) {
      console.error('Error generating SEO metadata:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to generate SEO metadata');
    }
  }

  private hashContent(content: string): string {
    return createHash('sha256').update(content).digest('hex');
  }

  /**
   * Finds long-tail keyword variations
   * 
   * @param mainKeyword - The seed keyword to find variations for
   * @returns {Promise<string[]>} Array of long-tail keyword suggestions
   * 
   * @example Response Shape
   * ```json
   * [
   *   "beast putty for shoulder pain",
   *   "how to use beast putty for recovery",
   *   "beast putty vs therapy putty comparison",
   *   "best beast putty exercises for athletes",
   *   "beast putty resistance levels guide"
   * ]
   * ```
   */
  async findLongTailKeywords(mainKeyword: string): Promise<string[]> {
    const parser = StructuredOutputParser.fromZodSchema(
      z.object({
        keywords: z.array(z.string()).length(5),
      })
    );

    const prompt = new PromptTemplate({
      template: `Generate 5 long-tail keyword variations for: {keyword}

Consider:
- Search intent
- Question-based queries
- Specific modifiers

Provide a JSON object with an array of 5 keywords.

{format_instructions}`,
      inputVariables: ['keyword'],
      partialVariables: {
        format_instructions: parser.getFormatInstructions(),
      },
    });

    try {
      const input = await prompt.format({ keyword: mainKeyword });
      const response = await this.model.invoke(input);
      const parsed = await parser.parse(response.content.toString());
      return parsed.keywords;
    } catch (error) {
      console.error('Error finding long-tail keywords:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to find long-tail keywords');
    }
  }

  /**
   * Gets performance data from Search Console
   * 
   * @param keyword - The keyword to get data for
   * @param startDate - Start date for the data range
   * @param endDate - End date for the data range
   * @returns {Promise<SearchAnalyticsRow[]>} Array of search analytics data rows
   * 
   * @example Response Shape
   * ```json
   * [
   *   {
   *     "keys": ["beast putty"],
   *     "clicks": 45,
   *     "impressions": 1000,
   *     "ctr": 0.045,
   *     "position": 4.5
   *   }
   * ]
   * ```
   */
  private async getSearchConsoleData(keyword: string, startDate: string, endDate: string): Promise<SearchAnalyticsRow[]> {
    if (!this.config.searchConsole?.credentials) {
      return [];
    }

    const { searchConsole } = this.ensureGoogleClients();

    const response = await searchConsole.searchanalytics.query({
      siteUrl: this.config.searchConsole.siteUrl || '',
      requestBody: {
        startDate,
        endDate,
        dimensions: ['query'],
        dimensionFilterGroups: [{
          filters: [{
            dimension: 'query',
            operator: 'equals',
            expression: keyword
          }]
        }]
      }
    });

    return (response.data.rows || []).map((row: searchconsole_v1.Schema$ApiDataRow) => ({
      keys: row.keys || [],
      clicks: Number(row.clicks) || 0,
      impressions: Number(row.impressions) || 0,
      ctr: Number(row.ctr) || 0,
      position: Number(row.position) || 0
    }));
  }

  /**
   * Gets keyword metrics from Google Ads
   * 
   * @param keyword - The keyword to get data for
   * @returns {Promise<KeywordData>} Keyword metrics and trends
   * 
   * @example Response Shape
   * ```json
   * {
   *   "searchVolume": 1200,
   *   "competition": 0.65,
   *   "cpc": 1.25,
   *   "trends": [
   *     {
   *       "month": "2024-01",
   *       "volume": 1100
   *     }
   *   ]
   * }
   * ```
   */
  private async getKeywordPlannerData(keyword: string): Promise<KeywordData> {
    if (!this.config.googleAds?.clientId) {
      throw new Error('Google Ads configuration is required for keyword data');
    }

    try {
      const customerId = this.config.googleAds.clientId;

      // Using the REST endpoint for KeywordPlanIdeaService
      const response = await fetch(
        `https://googleads.googleapis.com/v18/customers/${customerId}/keywordPlanIdeas:generateKeywordIdeas`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.config.googleAds.refreshToken}`,
            'developer-token': process.env.GOOGLE_ADS_DEVELOPER_TOKEN!,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            keywordSeed: {
              keywords: [keyword]
            },
            language: 'languageConstants/1000', // en
            geoTargetConstants: ['geoTargetConstants/2840'], // US
            keywordPlanNetwork: 'GOOGLE_SEARCH'
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(`Google Ads API error: ${JSON.stringify(error)}`);
      }

      interface KeywordIdeaResponse {
        results?: Array<{
          keywordIdeaMetrics?: {
            avgMonthlySearches?: string;
            competition?: string;
            avgCpcMicros?: string;
          };
        }>;
      }

      const data = await response.json() as KeywordIdeaResponse;
      const keywordIdea = data.results?.[0] || {};

      return {
        searchVolume: Number(keywordIdea.keywordIdeaMetrics?.avgMonthlySearches) || 0,
        competition: this.normalizeCompetition(keywordIdea.keywordIdeaMetrics?.competition),
        cpc: Number(keywordIdea.keywordIdeaMetrics?.avgCpcMicros) / 1_000_000 || 0,
        trends: [] // Monthly trends would need a separate API call
      };
    } catch (error) {
      console.error('Error fetching keyword data:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to fetch keyword data from Google Ads');
    }
  }

  private normalizeCompetition(competition: string | undefined): number {
    const competitionMap: Record<string, number> = {
      'UNKNOWN': 0,
      'LOW': 0.33,
      'MEDIUM': 0.66,
      'HIGH': 1
    };
    return competitionMap[competition || 'UNKNOWN'] || 0;
  }

  /**
   * Calculates ranking potential for a keyword
   * 
   * @param keywordData - Keyword metrics from Google Ads
   * @param competitors - Competitor data for analysis
   * @returns {number} Score from 0-100 indicating ranking potential
   */
  private calculateRankingPotential(keywordData: KeywordData, competitors: CompetitorData[]): number {
    // Calculate a score from 0-100 based on:
    // - Lower competition is better (0-1 scale, inverted)
    const competitionScore = (1 - keywordData.competition) * 40;
    
    // - Higher search volume is better (log scale normalized to 0-30)
    const volumeScore = Math.min(30, Math.log10(keywordData.searchVolume) * 10);
    
    // - Competitor metrics (authority, backlinks) - lower average is better
    const avgCompetitorAuthority = competitors.reduce((sum, comp) => sum + comp.metrics.authority, 0) / competitors.length;
    const authorityScore = Math.max(0, 30 - (avgCompetitorAuthority / 3));
    
    return Math.round(competitionScore + volumeScore + authorityScore);
  }

  /**
   * Generates keyword suggestions using AI
   * 
   * @param keyword - The seed keyword
   * @returns {Promise<string[]>} Array of related keyword suggestions
   */
  private async generateKeywordSuggestions(keyword: string): Promise<string[]> {
    const prompt = new PromptTemplate({
      template: `Generate 5 related keyword suggestions for "{keyword}" that would be valuable for SEO.
Consider:
- Search intent variations
- Long-tail variations
- Related topics
- Common modifiers

Format the response as a simple comma-separated list.`,
      inputVariables: ['keyword']
    });

    const formattedPrompt = await prompt.format({ keyword });
    const response = await this.openai.invoke(formattedPrompt);
    return response.content.toString().split(',').map(k => k.trim());
  }

  /**
   * Gets competitor data for a keyword
   * 
   * @param keyword - The keyword to analyze competition for
   * @returns {Promise<CompetitorData[]>} Array of competitor data with metrics
   * 
   * @example Response Shape
   * ```json
   * [
   *   {
   *     "url": "https://competitor.com/putty",
   *     "title": "Benefits of Putty",
   *     "description": "Learn about putty benefits",
   *     "metrics": {
   *       "authority": 65,
   *       "backlinks": 120,
   *       "socialShares": 45
   *     }
   *   }
   * ]
   * ```
   */
  private async getCompetitorData(keyword: string): Promise<CompetitorData[]> {
    if (!this.config.searchConsole?.credentials) {
      throw new Error('Search Console credentials are required for competitor data');
    }

    try {
      const { searchConsole } = this.ensureGoogleClients();

      const response = await searchConsole.searchanalytics.query({
        siteUrl: this.config.searchConsole.siteUrl || '',
        requestBody: {
          startDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          endDate: new Date().toISOString().split('T')[0],
          dimensions: ['query', 'page'],
          dimensionFilterGroups: [{
            filters: [{
              dimension: 'query',
              operator: 'contains',
              expression: keyword
            }]
          }],
          rowLimit: 10
        }
      });

      const competitors = await Promise.all(
        ((response.data.rows || []) as searchconsole_v1.Schema$ApiDataRow[])
          .slice(0, 3)
          .map(async (row: searchconsole_v1.Schema$ApiDataRow) => {
            const url = (row.keys || [])[1] || '';
            let title = '';
            let description = '';

            try {
              const pageResponse = await fetch(url, {
                headers: { 'User-Agent': 'BeastBlogger/1.0' }
              });
              const html = await pageResponse.text();
              const titleMatch = html.match(/<title>(.*?)<\/title>/i);
              const descMatch = html.match(/<meta[^>]*name="description"[^>]*content="([^"]*)"[^>]*>/i);
              
              title = titleMatch?.[1] || url;
              description = descMatch?.[1] || '';
            } catch (error) {
              console.warn(`Failed to fetch metadata for ${url}:`, error);
              title = url;
              description = '';
            }

            return {
              url,
              title,
              description,
              metrics: {
                authority: Math.round((Number(row.position) || 0) * 10),
                backlinks: Math.round(Number(row.impressions) || 0),
                socialShares: Math.round(Number(row.clicks) || 0)
              }
            };
          })
      );

      return competitors;
    } catch (error) {
      console.error('Error fetching competitor data:', error instanceof Error ? error.message : 'Unknown error');
      throw new Error('Failed to fetch competitor data from Search Console');
    }
  }

  private isAnalysisFresh(timestamp: Date): boolean {
    const cacheAge = Date.now() - new Date(timestamp).getTime();
    const ONE_WEEK = 7 * 24 * 60 * 60 * 1000;
    return cacheAge < ONE_WEEK;
  }
}