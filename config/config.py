import os
from dotenv import load_dotenv

load_dotenv()

# API Keys and Credentials
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SHOPIFY_ACCESS_TOKEN = os.getenv('SHOPIFY_ACCESS_TOKEN')
SHOPIFY_STORE_URL = os.getenv('SHOPIFY_STORE_URL')
SHOPIFY_API_VERSION = '2024-10'  # Update with the desired API version
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY')

# Blog Post Configuration
MAX_POSTS = 50
MIN_POSTS = 1
DEFAULT_POSTS = 5

# Personas
PERSONAS = {
    'beastly': 'Write in a tone that is quirky, witty, very irreverent, and love sharing the benefits of Beast Putty and some total bullshit.',
    'professional': 'Write in a formal, authoritative tone with industry-specific terminology.',
    'casual': 'Write in a friendly, conversational tone that\'s easy to understand.',
    'playful': 'Write in an entertaining, light-hearted tone with occasional humor.',
    'educational': 'Write in an informative, clear tone focused on teaching concepts.'
}

# Error Messages
ERROR_MESSAGES = {
    'api_error': 'An error occurred while connecting to the {service} API. Please try again.',
    'invalid_input': 'Please check your input parameters and try again.',
    'upload_error': 'Failed to upload blog post to Shopify. Please verify your credentials.',
    'keyword_error': 'Unable to fetch keywords. Please check your seed topic and try again.'
} 