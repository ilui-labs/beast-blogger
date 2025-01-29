import { HfInference } from '@huggingface/inference';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Initialize Hugging Face client
const hf = new HfInference(process.env.HUGGINGFACE_API_KEY);

// Initialize core services
class BeastBlogger {
  private hf: HfInference;

  constructor() {
    this.hf = hf;
  }

  async initialize() {
    try {
      // Validate environment variables
      this.validateEnv();
      console.log('Environment validated successfully');

      // Initialize services
      await this.initializeServices();
      console.log('Services initialized successfully');

    } catch (error) {
      console.error('Initialization failed:', error);
      process.exit(1);
    }
  }

  private validateEnv() {
    const requiredEnvVars = [
      'HUGGINGFACE_API_KEY',
      'NODE_ENV',
      'API_PORT',
      'API_HOST'
    ];

    for (const envVar of requiredEnvVars) {
      if (!process.env[envVar]) {
        throw new Error(`Missing required environment variable: ${envVar}`);
      }
    }
  }

  private async initializeServices() {
    // TODO: Initialize SEO Handler Service
    // TODO: Initialize Content Generator Service
    // TODO: Initialize Email Service
    // TODO: Initialize Shopify Integration
  }
}

// Start the application
const app = new BeastBlogger();
app.initialize().catch(console.error);