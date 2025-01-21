import requests
import os
from time import sleep
from config.config import HUGGINGFACE_API_KEY
import time
import random
import logging
from PIL import Image

class ImageHandler:
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode
        self.api_url = "https://api-inference.huggingface.co/models/Lykon/dreamshaper-8"
        self.headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        
        # Set up image directory
        self.image_dir = os.path.join(os.getcwd(), 'generated_images')
        if not os.path.exists(self.image_dir):
            try:
                os.makedirs(self.image_dir)
            except Exception as e:
                self.logger.warning(f"Could not create images directory: {str(e)}")
                self.image_dir = os.path.join(os.path.expanduser('~'), 'generated_images')
                os.makedirs(self.image_dir, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def fetch_image(self, keyword: str, max_retries: int = 3, initial_timeout: int = 20) -> str:
        """Generate an image based on the keyword using Hugging Face API."""
        try:
            if self.test_mode:
                self.logger.info("Test mode: returning placeholder image")
                return "https://placehold.co/1920x1080/000000/FFFFFF.png"  # 16:9 placeholder

            retries = 0
            timeout = initial_timeout

            while retries < max_retries:
                self.logger.info(f"Making API request to generate image (attempt {retries + 1}/{max_retries})...")
                
                try:
                    response = requests.post(
                        self.api_url,
                        headers=self.headers,
                        json={"inputs": keyword},
                        timeout=timeout  # Add timeout parameter
                    )

                    # Handle different response codes
                    if response.status_code == 200:
                        # Success - process and return image
                        return self.save_and_return_image(response)
                    elif response.status_code == 503 or response.status_code == 500:
                        # Model busy or server error
                        retries += 1
                        if retries >= max_retries:
                            self.logger.error(f"Max retries ({max_retries}) reached. Model unavailable.")
                            return "Error: Model unavailable"
                            
                        # Exponential backoff with jitter
                        wait_time = min(timeout * (2 ** retries) + random.uniform(1, 5), 120)
                        self.logger.warning(f"Model busy or server error. Retry {retries}/{max_retries} in {wait_time:.1f} seconds...")
                        sleep(wait_time)
                        continue
                    else:
                        self.logger.error(f"API Error: {response.status_code}")
                        self.logger.error(f"Response content: {response.text}")
                        return "Error: API error"

                except requests.Timeout:
                    retries += 1
                    if retries >= max_retries:
                        self.logger.error("Max retries reached due to timeouts")
                        return "Error: Request timeout"
                    
                    timeout = min(timeout * 2, 120)  # Double timeout up to 2 minutes
                    self.logger.warning(f"Request timed out. Retry {retries}/{max_retries} with {timeout}s timeout...")
                    continue

            return "Error: Max retries reached"

        except Exception as e:
            self.logger.error(f"Error generating image: {str(e)}")
            self.logger.error("Full error:", exc_info=True)
            return "Error generating image"

    def save_and_return_image(self, response) -> str:
        """Save the image and return its file URL"""
        try:
            images_dir = os.path.join(os.getcwd(), 'generated_images')
            os.makedirs(images_dir, exist_ok=True)
            
            timestamp = int(time.time())
            filename = f"beast_putty_{timestamp}.png"
            filepath = os.path.join(images_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            self.logger.info(f"Successfully saved image to: {filepath}")
            return f"file://{filepath}"
            
        except Exception as e:
            self.logger.error(f"Error saving image: {str(e)}")
            return "Error saving image"

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