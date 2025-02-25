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