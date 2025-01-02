import requests
from config.config import UNSPLASH_ACCESS_KEY

# Example URL: https://api.unsplash.com/search/photos?query=Unleash%20Your%20Inner%20Focus%20Monster%20with%20Beast%20Putty:%20The%20Only%20Putty%20That%20Puts%20the%20%27Focus%27%20in%20%27Funky%27&client_id=Q2iEX-MN4BtHLMa-8CbKfTonYNIWGbNtTSUDOeDeatU&orientation=landscape

class ImageHandler:
    def __init__(self, test_mode: bool = False):
        self.unsplash_access_key = UNSPLASH_ACCESS_KEY
        self.test_mode = test_mode  # Add test mode flag

    def fetch_image(self, keyword: str) -> str:
        """Fetch a relevant image URL from Unsplash based on the keyword."""
        try:
            if self.test_mode:
                # Return a test image URL if in test mode
                return "https://placehold.co/600x400/000000/FFFFFF.png"  # Placeholder image URL
            # Search for images related to the keyword
            url = f"https://api.unsplash.com/search/photos?query={keyword}&client_id={self.unsplash_access_key}&orientation=landscape"
            response = requests.get(url)
            response.raise_for_status()  # Raise an error for bad responses
            data = response.json()

            # Check if any images were found
            if data['results']:
                # Return the URL of the first image
                return data['results'][0]['urls']['regular']  # You can choose different sizes if needed
            else:
                return "No image found"  # Handle case where no images are found
        except Exception as e:
            print(f"Error fetching image: {str(e)}")
            return "Error fetching image" 