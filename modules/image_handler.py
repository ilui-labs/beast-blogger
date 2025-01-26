import requests
import os
from time import sleep
from config.config import HUGGINGFACE_API_KEY
import time
import random
import logging

class ImageHandler:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def fetch_image(self, keyword: str, max_retries: int = 3, initial_timeout: int = 20) -> str:
        """Generate an image based on the keyword using StarryAI."""
        try:
            if self.test_mode:
                self.logger.info("Test mode: returning placeholder image")
                return "https://placehold.co/1920x1080/000000/FFFFFF.png"

            self.logger.info("Generating image with StarryAI...")
            starryai_api_key = os.getenv('STARRYAI_API_KEY')
            if not starryai_api_key:
                self.logger.error("StarryAI API key not found")
                return "Error: StarryAI API key not found"

            headers = {
                'X-API-Key': starryai_api_key,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Create a new generation request
            response = requests.post(
                'https://api.starryai.com/creations/',
                headers=headers,
                json={
                    'prompt': keyword,
                    'height': 1080,
                    'width': 1920,
                    'cfg_scale': 7.5,
                    'seed': random.randint(1, 1000000),
                    'steps': 50,
                    'engine': 'stable-diffusion-xl-v1',
                    'style_preset': 'digital-art'
                },
                timeout=30
            )
            
            if response.status_code != 200:
                self.logger.error(f"StarryAI API Error: {response.status_code}")
                return "Error: StarryAI API error"
            
            result = response.json()
            if 'id' in result:
                # Poll for completion
                creation_id = result['id']
                retry_count = 0
                max_retries = 60  # 5 minutes total with exponential backoff
                base_wait = 2  # Start with 2 seconds
                
                while retry_count < max_retries:
                    try:
                        status_response = requests.get(
                            f'https://api.starryai.com/creations/{creation_id}',
                            headers=headers,
                            timeout=10
                        )
                        
                        if status_response.status_code == 429:  # Rate limit
                            wait_time = int(status_response.headers.get('Retry-After', base_wait))
                            self.logger.warning(f"Rate limited, waiting {wait_time} seconds")
                            time.sleep(wait_time)
                            continue
                            
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            status = status_data.get('status')
                            
                            if status == 'completed':
                                image_url = status_data.get('image_url')
                                if image_url:
                                    self.logger.info("Image generation completed successfully")
                                    return image_url
                                break
                            elif status == 'failed':
                                self.logger.error(f"Generation failed: {status_data.get('error')}")
                                break
                                
                        elif status_response.status_code >= 500:
                            self.logger.warning("Server error, retrying...")
                        
                    except requests.RequestException as e:
                        self.logger.warning(f"Request error: {str(e)}")
                    
                    # Exponential backoff with jitter
                    wait_time = min(30, base_wait * (2 ** retry_count)) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    retry_count += 1
                
            self.logger.warning("StarryAI generation incomplete or failed")
            return "Error: StarryAI generation failed"
            
        except Exception as e:
            self.logger.error(f"Error generating image: {str(e)}")
            self.logger.error("Full error:", exc_info=True)
            return "Error: Image generation failed"

    def generate_image_prompt(self, query: str, intent: str = None, excerpt: str = None) -> str:
        """Generate a creative prompt for image generation."""
        self.logger.info(f"Generating prompt for query: {query}")
        self.logger.info(f"Intent: {intent}, Excerpt available: {'yes' if excerpt else 'no'}")
        
        style_prefix = "Digital art style, high contrast, punk rock aesthetic, bold colors, no text, "
        
        # Extract key concepts from excerpt if available
        excerpt_terms = ""
        if excerpt:
            excerpt = excerpt.split('.')[0][:100]
            important_words = [word for word in excerpt.split() 
                             if len(word) > 3 and word.lower() not in 
                             ['with', 'the', 'and', 'for', 'that', 'this', 'from']]
            excerpt_terms = ' '.join(important_words[:3])
            self.logger.info(f"Extracted excerpt terms: {excerpt_terms}")
        
        # Core absurd scenarios (removed text references)
        absurd_scenarios = [
            f"a brain-eating zombie studying intensely with {query}, comic book style",
            f"a death metal band meditating peacefully with {query}",
            f"a business suit-wearing demon celebrating success with {query} floating around",
            f"a monster truck constructed from glowing {query}",
            f"a mad scientist's laboratory filled with bubbling {query}",
            f"an epic battle between productivity monsters using {query} as weapons",
            f"a heavy metal concert where the crowd is using {query}",
            f"a corporate boardroom of tentacled monsters using {query}",
            f"an extreme sports athlete performing stunts with {query}",
            f"a luxury sports car transforming into {query}",
            f"skeleton supermodels showcasing {query} on a runway",
            f"vampires in tuxedos admiring {query} in an art gallery",
            f"monsters studying {query} in a gothic university",
            f"ancient aliens demonstrating {query} to scientists",
            f"historical figures experimenting with {query} in a time machine",
            f"a rockstar werewolf smashing guitars made of {query} under a full moon",
            f"a haunted carnival where clowns juggle flaming {query}",
            f"a pirate ship made entirely of {query} sailing through a lava ocean",
            f"a dragon hoarding treasure chests filled with glowing {query}",
            f"a giant robot powered by radioactive {query} rampaging through a city",
            f"a post-apocalyptic biker gang wielding {query} as weapons",
            f"a medieval jousting tournament with knights riding armored unicorns and lances made of {query}",
            f"an alien invasion where UFOs beam up cows made of {query}",
            f"a rave inside a volcano where partygoers are drinking molten {query}",
            f"a secret society of ninjas battling with {query} under a blood-red moon",
            f"zombies running a five-star restaurant serving gourmet dishes made of {query}",
            f"a gladiator arena filled with mutant gladiators using {query} in combat",
            f"a team of intergalactic space pirates looting asteroids made of {query}",
            f"a gothic wedding where the cake is made of swirling {query}",
            f"a time-traveling samurai slicing through portals made of {query}",
            f"a steampunk airship powered by swirling gears of {query}",
            f"a circus ringmaster commanding lions made of {query} jumping through fiery hoops",
            f"a biker bar brawl where the bikers are throwing {query} at each other",
            f"a superhero showdown where their powers are fueled by glowing {query}"
        ]

        # Combine elements
        scenario = random.choice(absurd_scenarios)
        
        # Add excerpt terms if available
        if excerpt_terms:
            scenario = scenario.replace(query, f"{query} ({excerpt_terms})")

        # Build final prompt
        prompt = f"{style_prefix} {scenario}, no text overlay, no words, no letters, dark humor style, highly detailed, dramatic lighting, cinematic composition"
        
        # Log the final prompt
        self.logger.info(f"Generated prompt: {prompt[:100]}...")
        
        return prompt