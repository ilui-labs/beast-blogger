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
            title = post['title']
            excerpt = post['excerpt']
            image_url = post.get('image', '')

            # Handle local file paths
            if image_url.startswith('file://'):
                try:
                    # Convert file URL to actual file path
                    file_path = image_url[7:]  # Remove 'file://' prefix
                    print(f"Uploading image from path: {file_path}")
                    
                    # Create new article with image
                    article = shopify.Article({
                        'blog_id': 85728755847,
                        'title': title,
                        'author': "Jackson Blacklock",
                        'body_html': post['content'],
                        'summary': excerpt,
                        'published': False,
                        'image': {
                            'attachment': base64.b64encode(open(file_path, 'rb').read()).decode()
                        }
                    })
                    
                    if article.save():
                        print(f"Article and image uploaded successfully")
                        return article
                    else:
                        print(f"Error saving article: {article.errors.full_messages()}")
                        return None
                        
                except Exception as img_error:
                    print(f"Error uploading article with image: {str(img_error)}")
                    return None

            # If no image or error occurred, try without image
            variables = {
                "article": {
                    "blogId": "gid://shopify/Blog/85728755847",
                    "title": title,
                    "author": {
                        "name": "Jackson Blacklock"
                    },
                    "body": post['content'],
                    "summary": excerpt,
                    "isPublished": False
                }
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
            # Check for user errors in the response
            user_errors = response['data']['articleCreate']['userErrors']
            if user_errors:
                error_messages = ', '.join([f"{error['field']}: {error['message']}" for error in user_errors])
                raise Exception(f"User errors occurred: {error_messages}")
            article = response['data']['articleCreate']['article']
            print(f"Post uploaded successfully: {article['title']} - {article['summary']}")
            return article
            
        except Exception as e:
            print(f"Error uploading post: {post['title']}")
            print(traceback.format_exc())
            raise Exception(f"Shopify upload error: {str(e)}") 