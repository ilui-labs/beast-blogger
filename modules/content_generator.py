from openai import OpenAI
from typing import Dict, List
from config.config import PERSONAS, OPENAI_API_KEY

class ContentGenerator:
    def __init__(self, persona: str, test_mode: bool = False):
        self.persona = PERSONAS.get(persona, PERSONAS['professional'])
        self.test_mode = test_mode  # Add test mode flag
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    def generate_blog_post(self, keyword: str) -> Dict:
        """Generate a blog post optimized for the given keyword"""
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

            # Create the prompt with persona and SEO requirements
            prompt = f"""
            You are a blog post writer. {self.persona}
            Create a comprehensive blog post optimized for the keyword: {keyword}

            IMPORTANT - For all links in the content:
            1. For internal links, ONLY use these verified URLs:
               - Main site: https://www.beastputty.com
               - Shop/Search: https://www.beastputty.com/search
               DO NOT create or guess other internal URLs.

            2. For external links, ONLY use these trusted domains and their main sections:
               - wikipedia.org/wiki/[verified_article]
               - healthline.com/health/
               - webmd.com/health/
               - mayoclinic.org/diseases-conditions/
               - psychologytoday.com/us/basics/
               - sciencedaily.com/news/
               - nih.gov/health-information/

            3. Link Guidelines:
               - Only link to main category pages or well-known articles
               - Do not create deep links that might not exist
               - When in doubt, link to the main domain section
               - For product references, always use https://www.beastputty.com/search
               - Verify that any Wikipedia articles actually exist before linking

            Include:
            1. A catchy and relevant title (ensure it is optimized for URL generation with one or two relevant keywords, avoiding keyword stuffing)
            2. A brief excerpt summarizing the main points of the post
            3. An engaging introduction
            4. At least 3 informative subheadings
            5. Relevant content under each subheading (do not repeat the title in the content)
            6. A conclusion
            7. Natural keyword placement throughout the content
            8. At least 2 verified external links from the trusted domains above
            9. At least 2 internal links using ONLY the verified URLs provided

            Format the output as follows:
            <title>The generated title</title>
            <excerpt>The generated excerpt</excerpt>
            <content>The generated blog post content in HTML format (only the HTML content between the body tags, without any head, or body tags)</content>
            """

            # Make a request to the OpenAI API using the new interface
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use the GPT-4o Mini model
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1995,  # Adjusted for 1000-1500 words
                temperature=0.85,  # Increased for more creativity
                n=1  # Number of responses to generate
            )

            generated_text = response.choices[0].message.content
            title_start = generated_text.find("<title>") + len("<title>")
            title_end = generated_text.find("</title>")
            excerpt_start = generated_text.find("<excerpt>") + len("<excerpt>")
            excerpt_end = generated_text.find("</excerpt>")
            content_start = generated_text.find("<content>") + len("<content>")
            content_end = generated_text.find("</content>")

            title = generated_text[title_start:title_end].strip()
            excerpt = generated_text[excerpt_start:excerpt_end].strip()
            content = generated_text[content_start:content_end].strip()

            return {
                'keyword': keyword,
                'title': title,
                'excerpt': excerpt,
                'content': content,
                'status': 'generated'
            }
        except Exception as e:
            raise Exception(f"Content generation error: {str(e)}")

    def generate_multiple_posts(self, keywords: List[str], keyword_data: List[Dict] = None) -> List[Dict]:
        """Generate multiple blog posts with keyword data."""
        posts = []
        for i, keyword in enumerate(keywords):
            data = keyword_data[i] if keyword_data else None
            post = self.generate_post(keyword, data)
            posts.append(post)
        return posts

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
                    'status': 'generated',
                    'intent': keyword_data.get('intent') if keyword_data else None,
                    'frequent_word': keyword_data.get('frequent_word') if keyword_data else None
                }

            # Get the additional data from keyword_data
            intent = keyword_data.get('intent') if keyword_data else None
            frequent_word = keyword_data.get('frequent_word') if keyword_data else None
            tab = keyword_data.get('tab') if keyword_data else None

            # Create an enhanced prompt with the additional data
            self.persona += f"""
            Additional Context:
            - Search Intent: {intent if intent else 'Not specified'}
            - Key Topic to Cover: {frequent_word if frequent_word else 'Not specified'}
            - Content Category: {tab if tab else 'Not specified'}

            Make sure to:
            - Align the introduction with the {intent} search intent
            - Naturally integrate the key topic "{frequent_word}" where relevant
            - Create a conclusion that satisfies the user's search intent
            """

            # Use the base generate_blog_post method with enhanced persona
            post = self.generate_blog_post(keyword)
            
            # Add the additional metadata
            post['intent'] = intent
            post['frequent_word'] = frequent_word
            post['tab'] = tab
            
            return post

        except Exception as e:
            raise Exception(f"Content generation error: {str(e)}") 