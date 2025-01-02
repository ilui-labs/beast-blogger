import streamlit as st
import pandas as pd
import asyncio
from typing import List, Dict
from modules.content_generator import ContentGenerator
from modules.image_handler import ImageHandler
from modules.shopify_uploader import ShopifyUploader
from config.config import PERSONAS
import os

class BlogAutomationApp:
    def __init__(self):
        self.test_mode = os.getenv('ENV') != 'production'
        self.image_handler = ImageHandler(test_mode=self.test_mode)
        self.shopify_uploader = ShopifyUploader()

    def create_interface(self):
        st.title("Shopify Blog Post Automation Tool")

        # Input fields
        persona = st.selectbox("Select Writing Persona", list(PERSONAS.keys()), index=0)
        keywords_input = st.text_input("Enter comma-separated keywords")

        if st.button("Generate Blog Posts"):
            keywords = [keyword.strip() for keyword in keywords_input.split(",") if keyword.strip()]
            generated_posts = []
            for keyword in keywords:
                generated_posts.extend(self.generate_posts(persona, keyword, 1))
            st.session_state.generated_posts_df = self.create_posts_dataframe(generated_posts)

        if 'generated_posts_df' in st.session_state:
            edited_df = st.data_editor(st.session_state.generated_posts_df, num_rows="dynamic", use_container_width=True)
            st.session_state.generated_posts_df = edited_df

        if st.button("Upload Selected Posts"):
            selected_posts = self.get_selected_posts(st.session_state.generated_posts_df)
            upload_status = asyncio.run(self.upload_posts(selected_posts))
            st.write(upload_status)

    def generate_posts(self, persona: str, keyword: str, num_posts: int):
        """Generate blog posts and return as JSON for dynamic rendering"""
        try:
            content_generator = ContentGenerator(persona, test_mode=self.test_mode)
            generated_posts = content_generator.generate_multiple_posts([keyword] * num_posts)

            # Add images to posts
            for post in generated_posts:
                image_query = f"{post['title']} {post['keyword']}"
                post['image'] = self.image_handler.fetch_image(image_query)

            return generated_posts
        except Exception as e:
            st.error(f"Error generating posts: {str(e)}")
            return []

    def create_posts_dataframe(self, generated_posts):
        """Create a DataFrame from the generated posts"""
        posts_data = []
        for post in generated_posts:
            posts_data.append({
                "Selected": True,
                "Keyword": post["keyword"],
                "Title": post["title"],
                "Excerpt": post["excerpt"],
                "Content": post["content"],
                "Image": post["image"]
            })
        return pd.DataFrame(posts_data)

    def get_selected_posts(self, generated_posts_df):
        """Get the selected posts from the UI"""
        selected_posts = []
        for _, row in generated_posts_df.iterrows():
            if row["Selected"]:
                post = {
                    "keyword": row["Keyword"],
                    "title": row["Title"],
                    "excerpt": row["Excerpt"],
                    "content": row["Content"],
                    "image": row["Image"]
                }
                selected_posts.append(post)
        return selected_posts

    async def upload_posts(self, selected_posts: List[Dict]):
        """Upload selected posts to Shopify"""
        try:
            upload_count = 0
            for post in selected_posts:
                await self.shopify_uploader.upload_post(post)
                upload_count += 1

            return f"Uploaded {upload_count} posts successfully!"
        except Exception as e:
            return f"Error uploading posts: {str(e)}"


if __name__ == "__main__":
    app = BlogAutomationApp()
    app.create_interface()