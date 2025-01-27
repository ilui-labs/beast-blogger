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
                'accept': 'application/json',
                'content-type': 'application/json',
                'X-API-Key': starryai_api_key
            }
            
            # Create generated_images directory if it doesn't exist
            os.makedirs('generated_images', exist_ok=True)
            
            # Create a new generation request with parameters from API docs
            generation_params = {
                'prompt': keyword,
                'model': 'lyra',
                'aspectRatio': 'square',
                'highResolution': False,
                'images': 1,
                'steps': 30
            }
            
            self.logger.info(f"Sending generation request with params: {generation_params}")
            
            response = requests.post(
                'https://api.starryai.com/creations/',
                headers=headers,
                json=generation_params,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"StarryAI API Error: {response.status_code}"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg += f" - {error_data['error']}"
                except:
                    pass
                self.logger.error(error_msg)
                return f"Error: {error_msg}"
            
            result = response.json()
            creation_id = result.get('id')
            if not creation_id:
                self.logger.error("No generation ID received from API")
                return "Error: Invalid API response"
                
            # Poll for completion with improved error handling
            retry_count = 0
            max_retries = 30  # 5 minutes total with exponential backoff
            base_wait = 10     # Start with 10 seconds
            
            self.logger.info(f"Generation started with ID: {creation_id}")
            
            while retry_count < max_retries:
                try:
                    # Use the GET creation endpoint from the docs
                    status_response = requests.get(
                        f'https://api.starryai.com/creations/{creation_id}',
                        headers=headers,
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        
                        # Check if the image is ready or expired
                        if status_data.get('expired', False):
                            self.logger.warning("Image generation has expired")
                            return "Error: Image generation expired"
                        
                        # Check generation status
                        status = status_data.get('status')
                        
                        if status in ['completed', 'succeeded']:
                            # Log full status data for debugging
                            self.logger.info(f"Full status data: {status_data}")
                            
                            # Extract image URL from the images array
                            image_url = None
                            images = status_data.get('images', [])
                            
                            # Find the first non-expired image
                            for img in images:
                                if not img.get('expired', True):
                                    image_url = img.get('url')
                                    break
                            
                            # If no image found, try direct URL extraction
                            if not image_url and images:
                                image_url = images[0].get('url')
                            
                            # Fallback to other URL extraction methods if no valid image found
                            if not image_url:
                                image_url = (
                                    status_data.get('imageUrl') or 
                                    status_data.get('image_url') or 
                                    status_data.get('url') or 
                                    next((artifact.get('url') for artifact in status_data.get('artifacts', []) if artifact.get('url')), None)
                                )
                            
                            if image_url:
                                # Generate a unique filename
                                timestamp = int(time.time())
                                safe_keyword = ''.join(c if c.isalnum() else '_' for c in keyword[:20])
                                filename = f'generated_images/beast_putty_{safe_keyword}_{timestamp}.png'
                                
                                # Download and save the image
                                try:
                                    image_response = requests.get(image_url, timeout=30)
                                    if image_response.status_code == 200:
                                        with open(filename, 'wb') as f:
                                            f.write(image_response.content)
                                        self.logger.info(f"Image saved locally: {filename}")
                                except Exception as e:
                                    self.logger.error(f"Failed to save image: {str(e)}")
                                
                                self.logger.info("Image generation completed successfully")
                                return image_url
                            
                            # If no URL found, log detailed error
                            self.logger.error("No image URL found in completed response")
                            self.logger.error(f"Status data keys: {list(status_data.keys())}")
                            self.logger.error(f"Images data: {images}")
                            return "Error: No image URL found"
                        
                        elif status in ['processing', 'queued', 'submitted', 'in progress']:
                            # Wait and retry
                            wait_time = min(60, base_wait * (2 ** retry_count)) + random.uniform(0, 2)
                            self.logger.info(f"Image status: {status}. Waiting {wait_time:.1f} seconds")
                            time.sleep(wait_time)
                            retry_count += 1
                        
                        else:
                            # Handle other statuses
                            self.logger.error(f"Unexpected status: {status}")
                            self.logger.error(f"Full status data: {status_data}")
                            return f"Error: Unexpected generation status - {status}"
                    
                    else:
                        self.logger.warning(f"Unexpected status code: {status_response.status_code}")
                        return f"Error: Unexpected API response {status_response.status_code}"
                
                except requests.RequestException as e:
                    self.logger.warning(f"Request error: {str(e)}")
                    time.sleep(base_wait)
                    retry_count += 1
            
            self.logger.warning("StarryAI generation timed out")
            return "Error: Generation timed out"
            
        except Exception as e:
            self.logger.error(f"Unexpected error generating image: {str(e)}")
            self.logger.error("Full error:", exc_info=True)
            return "Error: Unexpected image generation failure"

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