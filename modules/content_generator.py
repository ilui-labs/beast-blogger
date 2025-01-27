from openai import OpenAI
from typing import Dict, List
from config.config import PERSONAS, OPENAI_API_KEY
from modules.seo_handler import SEOKeywordTool
import requests
import json
import logging
import re
from bs4 import BeautifulSoup

class ContentGenerator:
    def __init__(self, persona: str, test_mode: bool = False):
        self.persona = PERSONAS.get(persona, PERSONAS['professional'])
        # self.test_mode = test_mode  # Add test mode flag
        self.test_mode = test_mode  # Add test mode flag
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.logger = logging.getLogger(__name__)
        self.seo_tool = SEOKeywordTool()  # Initialize SEOKeywordTool

    def check_url(self, url: str) -> bool:
        """Check if a URL is valid and accessible"""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200
        except:
            return False

    def generate_multiple_posts(self, keywords: List[str], keyword_data: List[Dict] = None) -> List[Dict]:
        """Generate multiple blog posts with keyword data."""
        posts = []
        for i, keyword in enumerate(keywords):
            data = keyword_data[i] if keyword_data else None
            post = self.generate_post(keyword, data)
            posts.append(post)
        return posts

    def search_and_validate_urls(self, query: str, num_results: int = 3) -> list:
        """Search for URLs using SERP and validate them"""
        try:
            self.logger.info(f"\n=== OpenAI called search_urls ===")
            self.logger.info(f"Query: {query}")
            self.logger.info(f"Requested results: {num_results}")
            
            # Get pre-validated URLs from SEOKeywordTool
            urls = self.seo_tool.search_urls(query, num_results)
            
            valid_urls = []
            for url in urls:
                valid_urls.append({
                    "url": url,
                    "title": self.seo_tool.get_page_title(url),
                    "description": self.seo_tool.get_meta_description(url)
                })
                self.logger.info(f"✓ Added URL with metadata: {url}")
            
            self.logger.info(f"Found {len(valid_urls)} valid URLs")
            return valid_urls
            
        except Exception as e:
            self.logger.error(f"Error in search_urls: {str(e)}")
            self.logger.error("Full error:", exc_info=True)
            return []

    def generate_post(self, keyword: str, keyword_data: Dict = None) -> Dict:
        """Generate a single blog post using keyword data."""
        try:
            if self.test_mode:
                # Return test content if in test mode
                return {
                    'keyword': keyword,
                    'title': f"Test Title for {keyword}",
                    'excerpt': f"This is a test excerpt for a blog post about {keyword}.",
                    'content': f"This is a test blog post about {keyword}.",
                    'status': 'generated'
                }
            # Log function call
            self.logger.info("\n=== Starting Post Generation ===")
            self.logger.info(f"Keyword: {keyword}")
            self.logger.info(f"Data: {keyword_data}")

            if not keyword:
                self.logger.error("No keyword provided")
                return None

            # Track function calls
            function_calls = {
                "search_urls": 0,
                "validate_url": 0
            }

            # Define the URL search and validation functions
            functions = [
                {
                    "name": "search_urls",
                    "description": "Search for relevant URLs about a topic and validate them",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query to find relevant URLs"
                            },
                            "num_results": {
                                "type": "integer",
                                "description": "Number of URLs to return",
                                "default": 3
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "validate_url",
                    "description": "Check if a specific URL is valid and accessible",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to validate"
                            }
                        },
                        "required": ["url"]
                    }
                }
            ]

            system_prompt = f"""You are a {self.persona}. 
            When writing content:
            - First, use search_urls to find at least 5 relevant sources before writing
            - Use proper HTML anchor tags to cite sources, example: <a href="URL_HERE">relevant text</a>
            - Write comprehensive, detailed content (minimum 1000 words)
            - Include at least 4-5 main sections with descriptive subheadings using <h2> tags
            - Each section should be detailed with examples and explanations
            - Cite multiple sources naturally within each section using anchor tags
            - Include both scientific/academic and practical/user-friendly sources
            
            Internal Linking Requirements:
            - Include 1-3 relevant internal links to other Beast Putty blog posts
            - Use natural anchor text that relates to the linked content
            - Place internal links where they add value to the reader
            - Available internal posts for linking:
            {self._format_internal_links()}
            
            Content Structure:
            - Engaging introduction (2-3 paragraphs)
            - 4-5 main sections (each 200-300 words)
            - Practical examples and applications
            - Expert insights or research findings
            - Actionable conclusion with next steps
            
            Title Guidelines:
            - Write engaging, direct titles without colons
            - Focus on benefits or solutions
            - Use action words and strong verbs
            - Keep titles under 60 characters
            - Examples:
              "10 Powerful Stress Relief Activities That Actually Work"
              "The Ultimate Guide to Natural Stress Management"
              "Simple Ways to Beat Work Stress Today"
              "Proven Techniques for Better Focus at Work"
              
            HTML Requirements:
            - Use proper heading tags: <h2>, <h3>
            - Format paragraphs with <p> tags
            - Create links with <a href="URL"> tags
            - When citing sources, use this format:
              <a href="URL">According to [Source Name]</a>, or
              <a href="URL">research shows</a>
            - Use the exact URLs provided by search_urls
            - Include at least 2-5 citations with anchor tags
            
            Format your response as:
            <title>Your title here</title>
            <excerpt>Your excerpt here</excerpt>
            <content>Your HTML content here</content>
            """

            user_prompt = f"""Write a comprehensive, well-researched blog post about {keyword}.
            Intent: {keyword_data.get('intent', 'informational')}
            Key Topic: {keyword_data.get('frequent_word', '')}
            
            First, gather multiple sources using search_urls, then write detailed content 
            incorporating insights from these sources. Make sure to use proper HTML anchor 
            tags when citing sources."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            # Process function calls and generate content
            while True:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    functions=functions,
                    function_call="auto",
                    temperature=0.7,
                    max_tokens=2000
                )

                message = response.choices[0].message
                if not hasattr(message, 'function_call') or message.function_call is None:
                    self.logger.info("\n=== Function Call Summary ===")
                    self.logger.info(f"search_urls called: {function_calls['search_urls']} times")
                    self.logger.info(f"validate_url called: {function_calls['validate_url']} times")
                    break

                function_call = message.function_call
                if function_call.name == "search_urls":
                    function_calls["search_urls"] += 1
                    args = json.loads(function_call.arguments)
                    urls = self.search_and_validate_urls(args["query"], args.get("num_results", 5))  # Increased to 5
                    
                    # If we didn't get enough URLs, try a modified search
                    if len(urls) < 3:
                        self.logger.info("Not enough URLs found, trying alternative search...")
                        alternative_query = f"{args['query']} research studies benefits"
                        additional_urls = self.search_and_validate_urls(alternative_query, 3)
                        urls.extend(additional_urls)
                    
                    messages.append({
                        "role": "function",
                        "name": "search_urls",
                        "content": json.dumps({
                            "urls": urls,
                            "message": "If any URL is invalid, keep the content and request another URL"
                        })
                    })
                elif function_call.name == "validate_url":
                    function_calls["validate_url"] += 1
                    args = json.loads(function_call.arguments)
                    is_valid = self.check_url(args["url"])
                    messages.append({
                        "role": "function",
                        "name": "validate_url",
                        "content": json.dumps({"valid": is_valid, "url": args["url"]})
                    })

            # Parse and validate content
            content = message.content
            if not content:
                self.logger.error("No content generated")
                return None

            title = self.extract_tag_content(content, "title")
            body = self.extract_tag_content(content, "content")
            excerpt = self.extract_tag_content(content, "excerpt")

            if not title or not body:
                self.logger.error("Missing required content elements")
                return None

            self.logger.info("\n=== Post Generation Complete ===")
            return {
                'keyword': keyword,
                'title': title,
                'content': body,
                'excerpt': excerpt or self.generate_excerpt(body),  # Fallback to generated excerpt
                'intent': keyword_data.get('intent', ''),
                'volume': keyword_data.get('volume', 0),
                'frequent_word': keyword_data.get('frequent_word', ''),
                'tab': keyword_data.get('tab', '')
            }

        except Exception as e:
            self.logger.error(f"Error generating post: {str(e)}")
            self.logger.error("Full error:", exc_info=True)
            return None

    def generate_excerpt(self, content: str, max_length: int = 200) -> str:
        """Generate an excerpt from content if none provided"""
        try:
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', '', content)
            # Get first paragraph or sentence
            excerpt = text.split('\n')[0] if '\n' in text else text.split('.')[0]
            # Truncate if needed
            return excerpt[:max_length].strip() + '...' if len(excerpt) > max_length else excerpt.strip()
        except:
            return ""

    def extract_tag_content(self, text: str, tag: str) -> str:
        """Extract content between XML-style tags"""
        start = text.find(f"<{tag}>") + len(tag) + 2
        end = text.find(f"</{tag}>")
        return text[start:end].strip() if start > -1 and end > -1 else ""

    def get_internal_links(self) -> List[Dict]:
        """Get existing blog posts for internal linking"""
        try:
            blog_url = "https://www.beastputty.com/blogs/molding-destiny"
            response = requests.get(blog_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to fetch blog posts: {response.status_code}")
                return []

            # Parse the blog listing page
            internal_links = []
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all blog post links
            for article in soup.find_all('article'):
                try:
                    link = article.find('a')
                    if link:
                        title = link.get_text().strip()
                        url = f"https://www.beastputty.com{link['href']}"
                        internal_links.append({
                            "title": title,
                            "url": url,
                            "description": article.find('p', class_='excerpt').get_text().strip() if article.find('p', class_='excerpt') else ""
                        })
                except Exception as e:
                    self.logger.warning(f"Error parsing article: {str(e)}")
                    continue

            self.logger.info(f"Found {len(internal_links)} internal blog posts")
            return internal_links

        except Exception as e:
            self.logger.error(f"Error fetching internal links: {str(e)}")
            return []

    def _format_internal_links(self) -> str:
        """Format internal links for the prompt"""
        internal_links = self.get_internal_links()
        formatted_links = []
        for link in internal_links:
            formatted_links.append(f"- {link['title']}: {link['url']}")
        return "\n".join(formatted_links) 