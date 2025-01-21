import streamlit as st
import pandas as pd
import asyncio
from typing import List, Dict
import io
from modules.content_generator import ContentGenerator
from modules.image_handler import ImageHandler
from modules.shopify_uploader import ShopifyUploader
from config.config import PERSONAS
import os
from modules.seo_handler import SEOKeywordTool

class BlogAutomationApp:
    def __init__(self):
        # Force test mode to True
        os.environ['ENV'] = 'development'
        self.test_mode = True
        self.image_handler = ImageHandler(test_mode=self.test_mode)
        self.shopify_uploader = ShopifyUploader()
        # Set default values
        self.default_website = "https://beastputty.com"
        self.default_competitors = "https://crazyaarons.com/"

    def process_lowfruits_file(self, uploaded_file) -> List[Dict]:
        """Process a single lowfruits.io Excel file."""
        try:
            df = pd.read_excel(uploaded_file)
            # Extract relevant columns
            keywords_data = []
            for _, row in df.iterrows():
                keyword_info = {
                    'query': row['Query'],
                    'tab': row['Tab'],
                    'intent': row['Intent'] if 'Intent' in row else None,
                    'volume': row['Volume'] if 'Volume' in row else 0
                }
                keywords_data.append(keyword_info)
            return keywords_data
        except Exception as e:
            st.error(f"Error processing file {uploaded_file.name}: {str(e)}")
            return []

    def create_interface(self):
        st.title("Shopify Blog Post Automation Tool")

        # Input fields
        persona = st.selectbox("Select Writing Persona", list(PERSONAS.keys()), index=0)

        # Initialize keywords in session state if not exists
        if 'all_keywords' not in st.session_state:
            st.session_state.all_keywords = []

        # Create tabs for different keyword sources
        keyword_tab1, keyword_tab2 = st.tabs(["Lowfruits Upload", "SERP Analysis"])

        with keyword_tab1:
            # File Upload Section
            st.subheader("Keyword Files Upload")
            st.markdown("""
            Upload your lowfruits.io Excel files containing keyword data.
            Files should include columns: Query, Tab, Intent, and Frequent Word.
            """)
            
            uploaded_files = st.file_uploader(
                "Upload Lowfruits.io Excel Files",
                type=['xlsx'],
                accept_multiple_files=True
            )

            if uploaded_files:
                st.write(f"Uploaded {len(uploaded_files)} files")
                
                # Process button for lowfruits files
                if st.button("Process Lowfruits Files"):
                    # Process each file
                    with st.spinner("Processing keyword files..."):
                        for file in uploaded_files:
                            st.write(f"Processing {file.name}...")
                            keywords = self.process_lowfruits_file(file)
                            st.session_state.all_keywords.extend(keywords)

        with keyword_tab2:
            # SERP Analysis Section
            st.subheader("SERP Keyword Analysis")
            website_url = st.text_input(
                "Your Website URL",
                value=self.default_website if self.test_mode else "",
                placeholder="https://example.com"
            )
            competitor_urls = st.text_area(
                "Competitor URLs (one per line)",
                value=self.default_competitors if self.test_mode else "",
                placeholder="https://competitor1.com\nhttps://competitor2.com"
            )

            if st.button("Run SERP Analysis"):
                try:
                    if not os.getenv('HUGGINGFACE_API_KEY'):
                        st.error("Hugging Face API key not found. Please add HUGGINGFACE_API_KEY to your environment variables.")
                        return

                    with st.spinner("Analyzing keywords..."):
                        # Create status containers
                        status_container = st.empty()
                        progress_container = st.empty()
                        
                        try:
                            seo_tool = SEOKeywordTool()
                            
                            # Show progress
                            status_container.info("Analyzing keywords and generating variations...")
                            serp_keywords = seo_tool.analyze_keywords(website_url, competitor_urls)
                            
                            if not serp_keywords:
                                st.warning("No keywords found. Try adjusting your search parameters.")
                                return
                            
                            # Convert SERP keywords to match lowfruits format
                            with progress_container:
                                progress_bar = st.progress(0)
                                for i, kw in enumerate(serp_keywords):
                                    keyword_info = {
                                        'query': kw['query'],
                                        'tab': 'SERP',
                                        'intent': kw['intent'],
                                        'volume': kw.get('volume', 0)
                                    }
                                    st.session_state.all_keywords.append(keyword_info)
                                    progress_bar.progress((i + 1) / len(serp_keywords))
                            
                            status_container.success(f"✅ Found {len(serp_keywords)} keywords")
                            
                        except Exception as e:
                            st.error("Error during analysis. Please check your inputs and try again.")
                            st.error(f"Details: {str(e)}")
                            
                except Exception as e:
                    st.error(f"Configuration error: {str(e)}")

            # Add a small info section
            with st.expander("About SERP Analysis"):
                st.markdown("""
                This tool uses AI to:
                - Generate relevant keyword variations
                - Determine search intent
                - Estimate search volumes
                - Categorize keywords by topic
                
                Rate limited to prevent API overuse.
                """)

        # Show combined keywords section
        if st.session_state.all_keywords:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader("All Processed Keywords")
            with col2:
                if st.button("Clear All Keywords", type="secondary"):
                    st.session_state.all_keywords = []
                    st.rerun()
            
            df = pd.DataFrame(st.session_state.all_keywords)
            st.dataframe(
                df[['query', 'intent', 'volume', 'tab']],
                use_container_width=True,
                column_config={
                    'query': 'Keyword',
                    'intent': 'Intent',
                    'volume': st.column_config.NumberColumn('Volume', format="%d"),
                    'tab': 'Source'
                },
                hide_index=True
            )

        # Generate Posts Section
        if 'all_keywords' in st.session_state and st.session_state.all_keywords:
            st.subheader("Generate Blog Posts")
            
            # Show total keywords to be processed
            st.write(f"Total keywords to process: {len(st.session_state.all_keywords)}")
            
            if st.button("Generate Blog Posts"):
                keywords_df = pd.DataFrame(st.session_state.all_keywords)
                generated_posts = []
                
                with st.spinner("Generating blog posts..."):
                    total = len(keywords_df)
                    progress_bar = st.progress(0)
                    
                    for index, row in keywords_df.iterrows():
                        keyword_data = row.to_dict()  # Convert Series to dict
                        posts = self.generate_posts(
                            persona=persona,
                            keyword=keyword_data['query'],  # Use the query from the dict
                            num_posts=1,
                            keyword_data=keyword_data
                        )
                        generated_posts.extend(posts)
                        
                        # Update progress
                        progress = (index + 1) / total
                        progress_bar.progress(progress)
                        st.write(f"Processed {index + 1} of {total} keywords")
                
                st.session_state.generated_posts_df = self.create_posts_dataframe(generated_posts)

        # Show generated posts if available
        if 'generated_posts_df' in st.session_state:
            edited_df = st.data_editor(
                st.session_state.generated_posts_df,
                num_rows="dynamic",
                use_container_width=True
            )
            st.session_state.generated_posts_df = edited_df

        # Upload button for selected posts
        if st.button("Upload Selected Posts"):
            selected_posts = self.get_selected_posts(st.session_state.generated_posts_df)
            upload_status = asyncio.run(self.upload_posts(selected_posts))
            st.write(upload_status)

    def generate_posts(self, persona: str, keyword: str, num_posts: int, keyword_data: Dict = None):
        """Generate blog posts with additional keyword data"""
        try:
            content_generator = ContentGenerator(persona, test_mode=self.test_mode)
            
            # Convert pandas Series to dictionary if needed
            if hasattr(keyword_data, 'to_dict'):
                keyword_data = keyword_data.to_dict()
            
            # Pass the keyword data to the content generator
            generated_posts = content_generator.generate_multiple_posts(
                [keyword] * num_posts,
                keyword_data=[keyword_data] * num_posts if keyword_data else None
            )

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