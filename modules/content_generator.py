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
            Include:
            1. A catchy and relevant title (ensure it is optimized for URL generation with one or two relevant keywords, avoiding keyword stuffing)
            2. A brief excerpt summarizing the main points of the post
            3. An engaging introduction
            4. At least 3 informative subheadings
            5. Relevant content under each subheading (do not repeat the title in the content)
            6. A conclusion
            7. Natural keyword placement throughout the content
            8. At least 2 relevant external links to authoritative sources or weird websites that kind of relate to the word or phrase.
            9. At least 2 relevant and real internal links to other pages on the website, https://www.beastputty.com
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

    def generate_multiple_posts(self, keywords: List[str]) -> List[Dict]:
        """Generate multiple blog posts for the given keywords"""
        posts = []
        for keyword in keywords:
            post = self.generate_blog_post(keyword)  # No await needed since it's synchronous
            posts.append(post)
        return posts 