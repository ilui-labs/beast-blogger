export interface SearchAnalyticsRow {
  keys: string[];
  clicks: number;
  impressions: number;
  ctr: number;
  position: number;
}

export interface KeywordData {
  searchVolume: number;
  competition: number;
  cpc: number;
  trends: Array<{
    month: string;
    volume: number;
  }>;
}

export interface CompetitorData {
  url: string;
  title: string;
  description: string;
  metrics: {
    authority: number;
    backlinks: number;
    socialShares: number;
  };
}

export interface KeywordAnalysis {
  keyword: string;
  searchVolume: number;
  competition: number;
  cpc: number;
  organicRankingPotential: number;
  trends: Array<{ month: string; volume: number }>;
  searchConsoleData?: {
    clicks: number;
    impressions: number;
    ctr: number;
    position: number;
  };
  competitors: CompetitorData[];
  suggestions: string[];
  timestamp?: Date;
}

export interface SeoMetadata {
  title: string;
  description: string;
  keywords: string[];
  canonicalUrl?: string;
}

export interface GoogleCredentials {
  type: string;
  project_id: string;
  private_key_id: string;
  private_key: string;
  client_email: string;
  client_id: string;
  auth_uri: string;
  token_uri: string;
  auth_provider_x509_cert_url: string;
  client_x509_cert_url: string;
}

export interface DataSourceConfig {
  googleAds?: {
    clientId: string;
    clientSecret: string;
    refreshToken: string;
  };
  searchConsole?: {
    credentials: GoogleCredentials;
    siteUrl?: string;
  };
} 