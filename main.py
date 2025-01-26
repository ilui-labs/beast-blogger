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
        self.test_mode = False
        self.image_handler = ImageHandler(test_mode=self.test_mode)
        self.shopify_uploader = ShopifyUploader()
        # Set default values
        self.default_website = "https://beastputty.com"
        self.default_competitors = "https://crazyaarons.com/"

    def process_lowfruits_file(self, uploaded_file) -> List[Dict]:
        """Process a single lowfruits.io Excel or CSV file."""
        try:
            # Determine file type and read accordingly
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:  # xlsx
                df = pd.read_excel(uploaded_file)
            
            # Convert column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Extract relevant columns
            keywords_data = []
            for _, row in df.iterrows():
                keyword_info = {
                    'query': row['query'],
                    'tab': row['tab'],
                    'intent': row['intent'] if 'intent' in df.columns else None,
                    'volume': row['volume'] if 'volume' in df.columns else 0,
                    'frequent_word': row['frequent word'] if 'frequent word' in df.columns else ''
                }
                keywords_data.append(keyword_info)
            return keywords_data
        except Exception as e:
            st.error(f"Error processing file {uploaded_file.name}: {str(e)}")
            return []

    def create_interface(self):
        st.title("Shopify Blog Post Automation Tool")

        # Initialize session state variables
        if 'keywords_df' not in st.session_state:
            st.session_state.keywords_df = pd.DataFrame()
        if 'all_keywords' not in st.session_state:
            st.session_state.all_keywords = []
        if 'generated_posts' not in st.session_state:
            st.session_state.generated_posts = []

        # Input fields
        persona = st.selectbox("Select Writing Persona", list(PERSONAS.keys()), index=0)
        
        # Initialize content generator once
        self.content_generator = ContentGenerator(persona, test_mode=self.test_mode)

        # Create tabs for different keyword sources
        keyword_tab1, keyword_tab2 = st.tabs(["Lowfruits Upload", "SERP Analysis"])

        with keyword_tab1:
            # File Upload Section
            uploaded_files = st.file_uploader(
                "Upload Lowfruits.io Excel or CSV Files",
                type=['xlsx', 'csv'],
                accept_multiple_files=True
            )

            if uploaded_files:
                st.write(f"Uploaded {len(uploaded_files)} files")
                
                if st.button("Process Lowfruits Files"):
                    with st.spinner("Processing keyword files..."):
                        temp_df = pd.DataFrame()
                        for file in uploaded_files:
                            st.write(f"Processing {file.name}...")
                            keywords = self.process_lowfruits_file(file)
                            temp_df = pd.concat([temp_df, pd.DataFrame(keywords)])
                        
                        # Add selection column and update session state
                        temp_df.insert(0, 'Selected', False)
                        st.session_state.keywords_df = temp_df
                        st.rerun()  # Rerun to show the updated dataframe

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
                            temp_df = pd.DataFrame([{
                                'query': kw['query'],
                                'intent': kw.get('intent', ''),
                                'volume': kw.get('volume', 0),
                                'frequent_word': kw.get('frequent_word', ''),
                                'tab': kw.get('tag', 'SERP')
                            } for kw in serp_keywords])

                            # Add selection column and update session state
                            temp_df.insert(0, 'Selected', False)
                            st.session_state.keywords_df = pd.concat([
                                st.session_state.keywords_df, 
                                temp_df
                            ]).drop_duplicates(subset=['query'])
                            
                            st.success(f"Found {len(serp_keywords)} keywords!")
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error in SERP analysis: {str(e)}")
                            st.error("Full error:", exc_info=True)

                except Exception as e:
                    st.error(f"Error: {str(e)}")

        # Show selection buttons and dataframe if we have keywords (moved outside tabs)
        if not st.session_state.keywords_df.empty:
            st.markdown("---")  # Add separator
            st.subheader("Keywords for Processing")
            
            # Create a container for the buttons
            button_container = st.container()
            col1, col2, col3 = button_container.columns([1, 1, 2])
            
            with col1:
                if st.button("✅ Select All", type="primary", use_container_width=True):
                    st.session_state.keywords_df['Selected'] = True
                    st.rerun()
                    
            with col2:
                if st.button("❌ Clear All", type="secondary", use_container_width=True):
                    st.session_state.keywords_df['Selected'] = False
                    st.rerun()

            with col3:
                if st.button("🚀 Generate Posts for Selected Keywords", type="primary", use_container_width=True):
                    selected_keywords = st.session_state.keywords_df[st.session_state.keywords_df['Selected']]
                    if len(selected_keywords) == 0:
                        st.warning("⚠️ Please select at least one keyword")
                    else:
                        st.write(f"🎯 Generating posts for {len(selected_keywords)} keywords")
                        
                        # Create progress containers
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        posts_container = st.container()

                        for index, row in selected_keywords.iterrows():
                            try:
                                status_text.text(f"🔄 Processing: {row['query']}")
                                
                                # Generate post using content_generator
                                post = self.content_generator.generate_post(row['query'], dict(row))
                                
                                if post:
                                    # Try to generate image with graceful fallback
                                    try:
                                        image_prompt = self.image_handler.generate_image_prompt(
                                            query=post['keyword'],
                                            intent=row.get('intent', ''),
                                            excerpt=post.get('excerpt', '')
                                        )
                                        image_url = self.image_handler.fetch_image(image_prompt)
                                        if image_url.startswith("Error:"):
                                            st.warning(f"⚠️ {image_url}")
                                            post['image'] = "https://placehold.co/1920x1080/CCCCCC/000000.png?text=Image+Generation+Failed"
                                            st.info("ℹ️ Using placeholder image - post will still be created")
                                        else:
                                            post['image'] = image_url
                                            st.success("✅ Image generated successfully")
                                    except Exception as img_error:
                                        st.warning(f"⚠️ Image generation skipped: {str(img_error)}")
                                        post['image'] = "https://placehold.co/1920x1080/CCCCCC/000000.png?text=Image+Generation+Failed"
                                        st.info("ℹ️ Using placeholder image - post will still be created")

                                    # Add to session state
                                    st.session_state.generated_posts.append(post)
                                    
                                    # Show post in UI with improved layout
                                    with posts_container:
                                        post_col1, post_col2 = st.columns([4, 1])
                                        with post_col1:
                                            st.success(f"✅ Generated: {post['title']}")
                                            with st.expander("Preview"):
                                                st.write(post['excerpt'])
                                        with post_col2:
                                            if st.button("📤 Upload Now", key=f"upload_{len(st.session_state.generated_posts)}", type="primary"):
                                                with st.spinner("📡 Uploading to Shopify..."):
                                                    result = asyncio.run(self.shopify_uploader.upload_post(post))
                                                    st.success(f"✨ {result}")

                                else:
                                    st.error(f"❌ Failed to generate post for: {row['query']}")

                            except Exception as e:
                                st.error(f"⚠️ Error processing {row['query']}: {str(e)}")

                            # Update progress
                            progress = (index + 1) / len(selected_keywords)
                            progress_bar.progress(progress)
                            status_text.text(f"📊 Processed {index + 1} of {len(selected_keywords)} keywords")

                        status_text.text("🎉 Processing complete!")

            # Initialize the editor key in session state if it doesn't exist
            if 'editor_key' not in st.session_state:
                st.session_state.editor_key = 0

            # Show editable dataframe with data_editor instead of dataframe
            edited_df = st.data_editor(
                st.session_state.keywords_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Selected": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select keywords to process",
                        default=False,
                    )
                },
                disabled=["query", "tab", "intent", "volume", "frequent_word"],  # Make all columns except Selected read-only
                key=f"keyword_editor_{st.session_state.editor_key}"  # Dynamic key based on state
            )

            # Only update if the dataframe has actually changed
            if not edited_df.equals(st.session_state.keywords_df):
                st.session_state.keywords_df = edited_df.copy()
                st.session_state.editor_key += 1  # Increment the key to force a refresh
                st.rerun()

        # Show all generated posts
        if st.session_state.generated_posts:
            st.header("Generated Posts")
            posts_df = self.create_posts_dataframe(st.session_state.generated_posts)
            edited_posts_df = st.data_editor(
                posts_df,
                hide_index=True,
                use_container_width=True
            )

            # Bulk upload button for remaining posts
            if st.button("Upload All Remaining Posts"):
                selected_posts = self.get_selected_posts(edited_posts_df)
                with st.spinner("Uploading selected posts..."):
                    upload_status = asyncio.run(self.upload_posts(selected_posts))
                    st.write(upload_status)

    def generate_posts(self, persona: str, keyword: str, num_posts: int, keyword_data: Dict = None):
        """Generate blog posts with additional keyword data"""
        try:
            st.write(f"Starting generation for keyword: {keyword}")
            content_generator = ContentGenerator(persona, test_mode=self.test_mode)
            
            # Convert pandas Series to dictionary if needed
            if hasattr(keyword_data, 'to_dict'):
                keyword_data = keyword_data.to_dict()
                st.write(f"Keyword data: {keyword_data}")
            
            st.write("Generating content...")
            generated_posts = []
            for _ in range(num_posts):
                post = content_generator.generate_post(keyword, keyword_data)
                if post:  # Only add if post generation was successful
                    # Add images to post
                    try:
                        image_prompt = self.image_handler.generate_image_prompt(
                            query=post['keyword'],
                            intent=keyword_data.get('intent', ''),
                            excerpt=post.get('excerpt', '')
                        )
                        st.write(f"Generated image prompt: {image_prompt}")
                        
                        post['image'] = self.image_handler.fetch_image(image_prompt)
                        st.write("✅ Image fetched successfully")
                    except Exception as img_error:
                        st.error(f"Error fetching image: {str(img_error)}")
                        post['image'] = None
                    
                    generated_posts.append(post)
                    st.write(f"✅ Generated post {len(generated_posts)}")
                else:
                    st.warning("⚠️ Failed to generate post")

            if generated_posts:
                st.write("Post generation complete")
                return generated_posts
            else:
                st.error("No posts were generated successfully")
                return []
            
        except Exception as e:
            st.error(f"Error in generate_posts: {str(e)}")
            st.error("Full error:", exc_info=True)
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
                "Image": post["image"],
                "Intent": post.get("intent", ""),
                "Volume": post.get("volume", 0),
                "Frequent Word": post.get("frequent_word", ""),
                "Tab": post.get("tab", "")
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