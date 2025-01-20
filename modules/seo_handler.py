import requests
from typing import List, Dict
import json
from urllib.parse import quote, urlparse, urljoin
import time
from bs4 import BeautifulSoup
import logging

class SEOKeywordTool:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def get_main_pages(self, base_url: str) -> List[str]:
        """Get URLs of main pages (home, about, products)."""
        main_paths = ['', 'about', 'about-us', 'products', 'shop']
        urls = []
        for path in main_paths:
            urls.append(urljoin(base_url.strip(), path))
        return urls

    def extract_terms_from_website(self, url: str) -> List[Dict]:
        """Extract product terms and related topics from website with frequency."""
        self.logger.info(f"Analyzing page: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get text from important elements with weights
            texts = []
            texts.extend([h.text.lower() for h in soup.find_all('h1')] * 3)  # Weight headings more
            texts.extend([h.text.lower() for h in soup.find_all('h2')] * 2)
            texts.extend([h.text.lower() for h in soup.find_all('h3')])
            texts.extend([p.text.lower() for p in soup.find_all('p')])
            
            # Extract product names and categories
            all_text = ' '.join(texts)
            words = all_text.split()
            
            # Find 2-4 word phrases (focusing on longer phrases)
            phrases = {}
            for i in range(len(words)-1):
                if i < len(words) - 3:
                    phrase = f"{words[i]} {words[i+1]} {words[i+2]} {words[i+3]}"
                    phrases[phrase] = phrases.get(phrase, 0) + 1
                if i < len(words) - 2:
                    phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                    phrases[phrase] = phrases.get(phrase, 0) + 1
                phrase = f"{words[i]} {words[i+1]}"
                phrases[phrase] = phrases.get(phrase, 0) + 1
            
            # Filter relevant phrases
            relevant_phrases = []
            relevant_keywords = [
                'putty', 'therapy', 'sensory', 'stress relief',
                'anxiety relief', 'fidget', 'educational', 'occupational therapy'
            ]
            
            for phrase, frequency in phrases.items():
                if any(keyword in phrase for keyword in relevant_keywords):
                    relevant_phrases.append({
                        'phrase': phrase,
                        'frequency': frequency,
                        'word_count': len(phrase.split())
                    })
            
            # Sort by frequency and word count
            sorted_phrases = sorted(
                relevant_phrases,
                key=lambda x: (x['frequency'], x['word_count']),
                reverse=True
            )
            
            # Take top 10 most frequent phrases
            top_phrases = sorted_phrases[:10]
            self.logger.info(f"Found {len(top_phrases)} relevant phrases from {url}")
            return top_phrases
        except Exception as e:
            self.logger.error(f"Error extracting terms from {url}: {e}")
            return []

    def get_google_suggestions(self, query: str) -> List[str]:
        """Get Google Autocomplete suggestions."""
        self.logger.debug(f"Getting suggestions for: {query}")
        base_url = f"http://suggestqueries.google.com/complete/search?client=firefox&q={quote(query)}"
        try:
            response = requests.get(base_url, headers=self.headers)
            if response.status_code == 200:
                suggestions = json.loads(response.text)[1]
                return suggestions
            return []
        except Exception as e:
            self.logger.error(f"Error getting Google suggestions: {e}")
            return []

    def get_related_topics(self, term: str) -> List[str]:
        """Get broader related topics for content ideas."""
        related_topics = []
        broader_contexts = [
            f"activities with {term}",
            f"benefits of {term}",
            f"{term} alternatives",
            f"{term} for education",
            f"{term} for therapy",
            f"{term} games",
            f"{term} exercises",
            "sensory activities",
            "stress relief techniques",
            "occupational therapy tools",
            "educational toys",
            "fidget toys benefits",
            "anxiety relief methods"
        ]
        
        for context in broader_contexts:
            suggestions = self.get_google_suggestions(context)
            related_topics.extend(suggestions)
            time.sleep(0.2)
        
        return list(set(related_topics))

    def analyze_keywords(self, website_url: str, competitor_urls: str) -> List[Dict]:
        """Find relevant long-tail keywords and broader content ideas."""
        self.logger.info("Starting keyword analysis...")
        keywords = []
        
        # Extract terms from main website pages
        self.logger.info("Analyzing main website...")
        product_terms = []
        for url in self.get_main_pages(website_url):
            terms = self.extract_terms_from_website(url)
            product_terms.extend(terms)
        
        # Add competitor terms
        self.logger.info("Analyzing competitor websites...")
        for url in competitor_urls.split('\n'):
            if url.strip():
                for page_url in self.get_main_pages(url):
                    terms = self.extract_terms_from_website(page_url)
                    product_terms.extend(terms)
        
        # Sort by frequency and get unique terms
        product_terms.sort(key=lambda x: (x['frequency'], x['word_count']), reverse=True)
        unique_terms = []
        seen = set()
        for term in product_terms:
            if term['phrase'] not in seen:
                unique_terms.append(term)
                seen.add(term['phrase'])
        
        self.logger.info(f"Found {len(unique_terms)} unique product terms")
        
        # Use only top 20 most frequent terms
        top_terms = unique_terms[:20]
        
        # Generate keywords for product terms
        self.logger.info("Generating keyword variations...")
        total_terms = len(top_terms)
        for i, term_data in enumerate(top_terms, 1):
            term = term_data['phrase']
            self.logger.info(f"Processing term {i}/{total_terms}: {term} (frequency: {term_data['frequency']})")
            suggestions = self.get_google_suggestions(term)
            
            # Get suggestions for informational and commercial intents
            intent_modifiers = [
                "how to use", "benefits of", "guide",
                "vs", "alternatives", "reviews",
                "best", "top rated"
            ]
            
            for modifier in intent_modifiers:
                combined_term = f"{term} {modifier}"
                suggestions.extend(self.get_google_suggestions(combined_term))
                time.sleep(0.2)
            
            # Process found keywords
            for keyword in suggestions:
                if keyword and len(keyword.split()) >= 3:  # Only include longer phrases
                    score = self.calculate_keyword_score(keyword)
                    keywords.append({
                        'keyword': keyword,
                        'score': score,
                        'word_count': len(keyword.split()),
                        'is_question': any(q in keyword.lower() for q in ['how', 'what', 'why', 'where', 'when']),
                        'intent': self.determine_search_intent(keyword),
                        'base_topic': term
                    })

        # Sort by score and remove duplicates
        unique_keywords = {k['keyword']: k for k in keywords}.values()
        sorted_keywords = sorted(unique_keywords, key=lambda x: x['score'], reverse=True)
        
        self.logger.info(f"Analysis complete. Found {len(sorted_keywords)} unique keywords")
        return sorted_keywords

    def calculate_keyword_score(self, keyword: str) -> int:
        """Calculate keyword score based on multiple factors."""
        score = 0
        word_count = len(keyword.split())
        
        # Prefer longer phrases (3-5 words ideal)
        if 3 <= word_count <= 5:
            score += 20
        elif word_count > 5:
            score += 10
            
        # Bonus for question-based keywords
        if any(q in keyword.lower() for q in ['how', 'what', 'why', 'where', 'when']):
            score += 15
            
        # Bonus for commercial intent
        if any(term in keyword.lower() for term in ['buy', 'price', 'cost', 'shop']):
            score += 10
            
        # Bonus for informational intent
        if any(term in keyword.lower() for term in ['how to', 'guide', 'tips']):
            score += 10
            
        return score

    def determine_search_intent(self, keyword: str) -> str:
        """Determine the search intent of the keyword."""
        keyword_lower = keyword.lower()
        
        if any(term in keyword_lower for term in ['buy', 'price', 'cost', 'shop']):
            return 'transactional'
        elif any(term in keyword_lower for term in ['how to', 'guide', 'tips']):
            return 'informational'
        elif any(term in keyword_lower for term in ['vs', 'versus', 'compared']):
            return 'commercial investigation'
        else:
            return 'navigational'