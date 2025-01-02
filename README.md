# Beast Blogger

This is a blog application built with Python and Flask. 

## Setup

1. Clone the repo
2. Create a virtual environment: `python -m venv .venv`
3. Activate the virtual environment:
   - On macOS/Linux: `source .venv/bin/activate`
   - On Windows: `.venv\Scripts\activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in the required values
6. Run the app: `python main.py`

## Environment Variables

The following environment variables need to be set in the `.env` file:

- `OPENAI_API_KEY`: API key for OpenAI 
- `SHOPIFY_ACCESS_TOKEN`: Access token for the Shopify API
- `SHOPIFY_STORE_URL`: URL of the Shopify store (e.g. xxxx.myshopify.com)  
- `UNSPLASH_ACCESS_KEY`: Access key for the Unsplash API
- `ENV`: Set to "production" for production mode 