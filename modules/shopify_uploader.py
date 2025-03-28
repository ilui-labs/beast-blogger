import shopify
from config.config import SHOPIFY_ACCESS_TOKEN, SHOPIFY_STORE_URL, SHOPIFY_API_VERSION
from datetime import datetime
import traceback
import json
from typing import Dict
import os
import base64

class ShopifyUploader:
    def __init__(self):
        self.shopify_access_token = SHOPIFY_ACCESS_TOKEN
        self.shopify_store_url = SHOPIFY_STORE_URL
        session = shopify.Session(self.shopify_store_url, SHOPIFY_API_VERSION, self.shopify_access_token)
        shopify.ShopifyResource.activate_session(session)

    async def upload_post(self, post: dict):
        """Upload a blog post to Shopify."""
        try:
            # Validate post dictionary
            required_keys = ['title', 'content', 'excerpt']
            for key in required_keys:
                if key not in post:
                    raise ValueError(f"Missing required key: {key}")

            title = post['title']
            excerpt = post['excerpt']
            image_url = post.get('image', '')

            # Validate title and content
            if not title or not title.strip():
                raise ValueError("Title cannot be empty")
            if not post['content'] or not post['content'].strip():
                raise ValueError("Content cannot be empty")

            # Prepare article data
            article_data = {
                "blogId": "gid://shopify/Blog/85728755847",
                "title": title,
                "author": {
                    "name": "Jackson Blacklock"
                },
                "body": post['content'],
                "summary": excerpt,
                "isPublished": False
            }

            # Add image if URL is provided and valid
            if image_url and isinstance(image_url, str) and image_url.startswith('http'):
                article_data["image"] = {
                    "altText": title,
                    "originalSource": image_url
                }
            else:
                # Log that no valid image was provided but continue with upload
                print(f"No valid image provided for post: {title}, continuing without image")

            variables = {
                "article": article_data
            }
            
            mutation = """
                mutation CreateArticle($article: ArticleCreateInput!) {
                    articleCreate(article: $article) {
                        article {
                            id
                            title
                            handle
                            body
                            summary
                            tags
                            image {
                                altText
                                originalSrc
                            }
                        }
                        userErrors {
                            code
                            field
                            message
                        }
                    }
                }
            """
            
            response = shopify.GraphQL().execute(mutation, variables)
            response = json.loads(response)
            
            # Check if the response has the expected structure
            if not isinstance(response, dict):
                raise Exception(f"Unexpected response format: {response}")
            
            if 'data' not in response:
                raise Exception(f"Response missing 'data' field: {response}")
            
            if 'articleCreate' not in response['data']:
                raise Exception(f"Response missing 'articleCreate' field: {response}")
            
            # Check for user errors in the response
            user_errors = response['data']['articleCreate'].get('userErrors', [])
            if user_errors:
                error_messages = ', '.join([f"{error.get('field', 'unknown')}: {error.get('message', 'Unknown error')}" for error in user_errors])
                raise Exception(f"User errors occurred: {error_messages}")
            
            article = response['data']['articleCreate'].get('article')
            if not article:
                raise Exception("No article data in response")
            
            print(f"Post uploaded successfully: {article.get('title', 'Unknown Title')}")
            return article
            
        except Exception as e:
            print(f"Error uploading post: {post.get('title', 'Unknown Title')}")
            print(traceback.format_exc())
            raise Exception(f"Shopify upload error: {str(e)}")