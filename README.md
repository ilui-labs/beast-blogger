# Beast Blogger

This is a blog post automation tool built with Python and Streamlit. It helps generate SEO-optimized blog content for Shopify stores.

## Features

- SEO Keyword Research Tool
  - Analyze your website and competitors
  - Identify underserved keyword opportunities
  - Export results as CSV
- AI-Powered Blog Generation
  - Multiple writing personas
  - Customizable content style
  - SEO-optimized posts

## Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment:
   - On macOS/Linux: `source .venv/bin/activate`
   - On Windows: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in the required values
6. Run the app: `streamlit run main.py`

Note: This application requires Python 3.8 or higher.

## Environment Variables

The following environment variables need to be set in the `.env` file:

- `OPENAI_API_KEY`: API key for OpenAI 
- `SHOPIFY_ACCESS_TOKEN`: Access token for the Shopify API
- `SHOPIFY_STORE_URL`: URL of the Shopify store (e.g. xxxx.myshopify.com)  
- `UNSPLASH_ACCESS_KEY`: Access key for the Unsplash API
- `ENV`: Set to "production" for production mode 

## Usage

1. Select a writing persona for your content
2. Enter your website URL and competitor URLs for keyword analysis
3. Use the generated keyword suggestions or enter your own keywords
4. Generate SEO-optimized blog posts automatically

## SEO Keyword Tool

The SEO Keyword Tool helps identify potential longtail keywords for your content strategy. To use:

1. Navigate to the SEO Tool section
2. Enter your website URL
3. Enter up to 3 competitor URLs
4. Click "Find Keywords"

The tool will analyze both your site and competitor sites to identify:
- Underserved keywords with good traffic potential
- Low competition longtail variations
- Related topic clusters

Results are provided as a CSV list that can be exported for content planning. 