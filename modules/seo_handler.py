import os
import logging
from typing import List, Dict
import requests
from pydantic import BaseModel, Field
import json
import time
from bs4 import BeautifulSoup
from googlesearch import search as google_search
from urllib.parse import urlparse

class KeywordData(BaseModel):
    query: str = Field(description="The search query or keyword")
    intent: str = Field(description="Search intent: informational, transactional, commercial, or navigational")
    tag: str = Field(description="Category or topic tag for the keyword")
    volume: int = Field(description="Estimated monthly search volume (0 if unknown)")

class SEOKeywordTool:
    def __init__(self):
        # Switch to a different model that's better at following instructions
        self.api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        self.headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def generate_text(self, prompt: str) -> str:
        """Generate text using Hugging Face API"""
        try:
            self.logger.info("Making API request to Hugging Face...")
            payload = {
                "inputs": f"<s>[INST] {prompt} [/INST]",  # Mistral instruction format
                "parameters": {
                    "max_length": 1000,
                    "temperature": 0.1,
                    "return_full_text": False,
                    "top_p": 0.1  # More focused output
                }
            }
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            
            if response.status_code != 200:
                self.logger.error(f"API Error: {response.status_code}")
                return ""
                
            self.logger.info("Received response from API")
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0].get('generated_text', '')
                self.logger.info(f"Generated text: {generated_text[:100]}...")
                return generated_text
            
            self.logger.warning("Empty or invalid response from API")
            return ""
            
        except Exception as e:
            self.logger.error(f"Generation error: {str(e)}")
            return ""

    def clean_and_parse_json(self, response: str) -> dict:
        """Clean and parse JSON response, handling duplicates"""
        try:
            self.logger.info("\n=== Starting JSON Cleaning ===")
            
            # Find the first complete JSON object
            depth = 0
            start = response.find('{')
            
            if start == -1:
                self.logger.error("No JSON object found")
                return {}
                
            for i in range(start, len(response)):
                if response[i] == '{':
                    depth += 1
                elif response[i] == '}':
                    depth -= 1
                    if depth == 0:
                        json_str = response[start:i+1]
                        self.logger.info("\nExtracted first complete JSON object:")
                        self.logger.info(json_str)
                        
                        try:
                            data_package = json.loads(json_str)
                            if 'main' in data_package and 'variations' in data_package:
                                self.logger.info("Successfully parsed JSON")
                                return data_package
                            else:
                                self.logger.warning("JSON missing required structure")
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSON parse error: {str(e)}")
                        break
            
            self.logger.error("No valid JSON object found")
            return {}
            
        except Exception as e:
            self.logger.error(f"JSON parsing error: {str(e)}")
            return {}

    def analyze_keywords(self, website_url: str, competitor_urls: str) -> List[Dict]:
        """Analyze keywords and generate variations"""
        try:
            # Process base topics
            base_topics = [
                "stress relief activities",
                "therapy putty exercises",
                "sensory toys benefits",
                "stress relief tools",
                "anxiety relief products",
                "educational sensory toys",
                "occupational therapy tools",
                "fidget toys for anxiety",
                "stress balls benefits",
                "hand therapy exercises",
                "sensory integration activities",
                "focus improvement tools",
                "desk toys for productivity",
                "mindfulness tools",
                "therapeutic putty exercises",
                "hand strengthening activities",
                "stress management products",
                "concentration improvement toys",
                "calming sensory tools",
                "fine motor skill toys"
            ]
            
            keywords = []
            prompt_template = """Analyze this topic: {topic}
            Context: {context}
            
            Return a JSON object with:
            1. Main keyword analysis
            2. Related keyword variations
            
            Format:
            {{
                "main": {{
                    "query": "primary keyword",
                    "intent": "informational/commercial/transactional",
                    "tag": "topic category",
                    "volume": estimated monthly searches,
                    "frequent_word": "most common relevant word"
                }},
                "variations": [
                    {{
                        "query": "variation 1",
                        "intent": "intent type",
                        "tag": "subtopic tags",
                        "volume": estimated searches,
                        "frequent_word": "common word"
                    }},
                    // ... more variations
                ]
            }}

            Remember:
            1. Return ONLY the JSON object
            2. Make sure it's valid JSON
            3. No explanations or additional text
            4. Use the exact format shown above"""
            
            context = f"""Website: {website_url}
            Industry: Stress relief and sensory products
            Competitors: {competitor_urls}"""
            
            self.logger.info(f"Processing {len(base_topics)} base topics")
            
            for topic in base_topics:
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"Processing topic: {topic}")
                
                prompt = prompt_template.format(
                    topic=topic,
                    context=context
                )
                
                response = self.generate_text(prompt)
                if response:
                    try:
                        self.logger.info("\n=== Processing Response ===")
                        self.logger.info("Raw response from model:")
                        self.logger.info("-" * 50)
                        self.logger.info(response)
                        self.logger.info("-" * 50)
                        
                        data_package = self.clean_and_parse_json(response)
                        
                        if not data_package:
                            self.logger.error("Failed to get valid data package")
                            continue
                        
                        # Add main keyword
                        if 'main' in data_package:
                            keywords.append(data_package['main'])
                            self.logger.info(f"Added main keyword: {data_package['main']}")
                        
                        # Add variations
                        if 'variations' in data_package:
                            for var in data_package['variations']:
                                keywords.append(var)
                                self.logger.info(f"Added variation: {var}")
                    
                    except Exception as e:
                        self.logger.error(f"Error parsing response: {e}")
                        self.logger.error(f"Problematic response: {response}")
                else:
                    self.logger.warning(f"No response generated for topic: {topic}")
                
                self.logger.info("Waiting for rate limit...")
                time.sleep(2)
            
            self.logger.info(f"Analysis complete. Found {len(keywords)} keywords")
            self.logger.info("Final keywords list:")
            for kw in keywords:
                self.logger.info(f"  {kw}")
            return keywords
            
        except Exception as e:
            self.logger.error(f"Error in keyword analysis: {str(e)}")
            return []

    def search_urls(self, query: str, num_results: int = 3) -> List[str]:
        """Search for relevant URLs using Google Search"""
        try:
            self.logger.info(f"Searching URLs for query: {query}")
            
            # List of trusted domains
            trusted_domains = [
                'mayoclinic.org',
                'healthline.com',
                'medicalnewstoday.com',
                'verywellmind.com',
                'psychologytoday.com',
                'health.harvard.edu',
                'nih.gov',
                'webmd.com',
                'sciencedaily.com',
                'betterhealth.vic.gov.au',
                'helpguide.org'
            ]
            
            found_urls = []
            # Use googlesearch-python to find URLs
            search_results = google_search(
                query, 
                num_results=num_results * 3,  # Get extra results to filter
                lang="en"
            )
            
            for url in search_results:
                # Parse the domain
                domain = urlparse(url).netloc.lower()
                if any(trusted in domain for trusted in trusted_domains):
                    try:
                        # Verify the URL is accessible
                        response = requests.head(url, timeout=5, allow_redirects=True)
                        if response.status_code == 200:
                            found_urls.append(url)
                            self.logger.info(f"Found valid URL: {url}")
                            if len(found_urls) >= num_results:
                                break
                    except:
                        continue
                        
                time.sleep(0.5)  # Be nice to search engines
            
            self.logger.info(f"Found {len(found_urls)} valid URLs")
            return found_urls
            
        except Exception as e:
            self.logger.error(f"Error searching URLs: {str(e)}")
            return []

    def get_page_title(self, url: str) -> str:
        """Get the title of a webpage with better error handling"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup.title.string.strip() if soup.title else ""
        except:
            return ""

    def get_meta_description(self, url: str) -> str:
        """Get the meta description with better error handling"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            return meta['content'].strip() if meta and 'content' in meta.attrs else ""
        except:
            return ""