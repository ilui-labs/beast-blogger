import streamlit as st
import pandas as pd
import asyncio
from typing import List, Dict
import io
from modules.content_generator import ContentGenerator
from modules.image_handler import ImageHandler
from modules.shopify_uploader import ShopifyUploader
from modules.dataframe_storage import DataFrameStorage
from config.config import PERSONAS
import os
from modules.seo_handler import SEOKeywordTool
import json
from datetime import datetime

class BlogAutomationApp:
    def __init__(self):
        # Force test mode to True
        os.environ['ENV'] = 'development'
        self.test_mode = False
        self.image_handler = ImageHandler(test_mode=self.test_mode)
        self.shopify_uploader = ShopifyUploader()
        self.df_storage = DataFrameStorage()
        # Set default values
        self.default_website = "https://beastputty.com"
        self.default_competitors = "https://crazyaarons.com/"

    def load_saved_keywords(self):
        """Load saved keywords from storage on startup"""
        try:
            # Query for keyword dataframes
            keyword_dfs = self.df_storage.query_by_metadata({"type": "keywords"})
            if keyword_dfs:
                # Get the most recent DataFrame
                latest_df_id = keyword_dfs[-1]  # Assuming IDs are ordered by creation time
                df = self.df_storage.get_dataframe(latest_df_id)
                st.session_state.keywords_df = df
                st.session_state.current_df_id = latest_df_id
            else:
                st.session_state.keywords_df = pd.DataFrame()
                st.session_state.current_df_id = None
        except Exception as e:
            st.error(f"Error loading saved keywords: {str(e)}")
            st.session_state.keywords_df = pd.DataFrame()
            st.session_state.current_df_id = None

    def save_keywords_df(self, df: pd.DataFrame, comment: str = "Updated keywords"):
        """Save or update the keywords DataFrame"""
        try:
            if df.empty:
                return
                
            if 'current_df_id' in st.session_state and st.session_state.current_df_id:
                # Update existing DataFrame
                self.df_storage.update_dataframe(
                    st.session_state.current_df_id,
                    df,
                    comment
                )
            else:
                # Create new DataFrame
                df_id = self.df_storage.add_dataframe(
                    df=df,
                    source="keywords",
                    metadata={
                        "type": "keywords",
                        "date": datetime.now().isoformat()
                    }
                )
                st.session_state.current_df_id = df_id
        except Exception as e:
            st.error(f"Error saving keywords: {str(e)}")

    def delete_keyword_row(self, index: int):
        """Delete a keyword row and update storage"""
        try:
            # Remove row from DataFrame
            st.session_state.keywords_df = st.session_state.keywords_df.drop(index).reset_index(drop=True)
            # Save updated DataFrame
            self.save_keywords_df(st.session_state.keywords_df, "Deleted keyword row")
        except Exception as e:
            st.error(f"Error deleting keyword: {str(e)}")

    def save_generated_post(self, post: Dict):
        """Save a generated post to the database"""
        try:
            # Create a DataFrame with the post data
            post_data = {
                "Selected": False,
                "Keyword": post["keyword"],
                "Title": post["title"],
                "Excerpt": post["excerpt"],
                "Content": post["content"],
                "Image": post.get("image"),
                "Intent": post.get("intent", ""),
                "Volume": post.get("volume", 0),
                "Frequent Word": post.get("frequent_word", ""),
                "Tab": post.get("tab", ""),
                "Status": "pending",
                "Generated Date": datetime.now().isoformat()
            }
            
            df = pd.DataFrame([post_data])
            
            # Query for existing posts DataFrame
            posts_dfs = self.df_storage.query_by_metadata({"type": "generated_posts"})
            
            if posts_dfs:
                # Get the most recent DataFrame
                latest_df_id = posts_dfs[-1]
                existing_df = self.df_storage.get_dataframe(latest_df_id)
                
                # Append new post
                combined_df = pd.concat([existing_df, df]).reset_index(drop=True)
                
                # Update existing DataFrame
                self.df_storage.update_dataframe(
                    latest_df_id,
                    combined_df,
                    "Added new generated post"
                )
            else:
                # Create new DataFrame
                df_id = self.df_storage.add_dataframe(
                    df=df,
                    source="generated_posts",
                    metadata={
                        "type": "generated_posts",
                        "date": datetime.now().isoformat()
                    }
                )
                
            return True
        except Exception as e:
            st.error(f"Error saving generated post: {str(e)}")
            return False

    def load_saved_posts(self):
        """Load saved posts from storage"""
        try:
            # Query for posts dataframes
            posts_dfs = self.df_storage.query_by_metadata({"type": "generated_posts"})
            if posts_dfs:
                # Get the most recent DataFrame
                latest_df_id = posts_dfs[-1]
                df = self.df_storage.get_dataframe(latest_df_id)
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"Error loading saved posts: {str(e)}")
            return pd.DataFrame()

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
            self.load_saved_keywords()
        if 'all_keywords' not in st.session_state:
            st.session_state.all_keywords = []
        if 'generated_posts' not in st.session_state:
            st.session_state.generated_posts = []
        if 'editor_key' not in st.session_state:
            st.session_state.editor_key = 0
        if 'saved_posts_df' not in st.session_state:
            st.session_state.saved_posts_df = self.load_saved_posts()

        # Create main tabs
        main_tab1, main_tab2, main_tab3 = st.tabs(["Blog Post Generation", "Saved Posts", "Settings"])

        with main_tab1:
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
                            
                            # Append to existing DataFrame if it exists
                            if not st.session_state.keywords_df.empty:
                                combined_df = pd.concat([
                                    st.session_state.keywords_df,
                                    temp_df
                                ]).drop_duplicates(subset=['query']).reset_index(drop=True)
                            else:
                                combined_df = temp_df
                            
                            st.session_state.keywords_df = combined_df
                            self.save_keywords_df(combined_df, "Added new keywords from Lowfruits")
                            st.rerun()

            # Show keywords DataFrame with delete functionality
            if not st.session_state.keywords_df.empty:
                st.markdown("---")
                st.subheader("Keywords for Processing")
                
                # Create column configuration
                column_config = {
                    "Selected": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select keywords to process",
                        default=False,
                    ),
                    "Delete": st.column_config.CheckboxColumn(
                        "Delete",
                        help="Mark for deletion",
                        default=False
                    )
                }
                
                # Add delete column if not present
                if 'Delete' not in st.session_state.keywords_df.columns:
                    st.session_state.keywords_df['Delete'] = False

                # Show editable dataframe
                edited_df = st.data_editor(
                    st.session_state.keywords_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config=column_config,
                    disabled=["query", "tab", "intent", "volume", "frequent_word"],
                    key=f"keyword_editor_{st.session_state.editor_key}"
                )

                # Handle deletions and updates
                if not edited_df.equals(st.session_state.keywords_df):
                    # Process deletions
                    to_delete = edited_df[edited_df['Delete']].index
                    if not to_delete.empty:
                        edited_df = edited_df.drop(to_delete).reset_index(drop=True)
                        edited_df['Delete'] = False  # Reset delete flags
                    
                    st.session_state.keywords_df = edited_df.copy()
                    self.save_keywords_df(edited_df, "Updated keywords")
                    st.session_state.editor_key += 1
                    st.rerun()

            # Show selection buttons and dataframe if we have keywords (moved outside tabs)
            if not st.session_state.keywords_df.empty:
                st.markdown("---")  # Add separator
                st.subheader("Keywords for Processing")
                
                # Create a container for the buttons
                button_container = st.container()
                
                # Create progress containers with improved layout
                progress_container = st.container()
                with progress_container:
                    col1 = st.columns(1)[0]
                    with col1:
                        status_text = st.empty()
                        progress_bar = st.empty()
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
                        try:
                            selected_keywords = st.session_state.keywords_df[st.session_state.keywords_df['Selected']]
                            if len(selected_keywords) == 0:
                                st.warning("⚠️ Please select at least one keyword")
                            else:
                                st.write(f"🎯 Generating posts for {len(selected_keywords)} keywords")
                                
                                # Create progress containers with improved layout
                                progress_container = st.container()
                                status_text = progress_container.empty()
                                progress_bar = progress_container.empty()
                                
                                # Create posts container
                                posts_container = st.container()
                                total_keywords = len(selected_keywords)

                                # Create a container for displaying generated posts
                                for index, row in selected_keywords.iterrows():
                                    try:
                                        # Ensure safe division for progress calculation
                                        current_progress = min(1.0, max(0.0, float(index) / float(total_keywords))) if total_keywords > 0 else 0.0
                                        status_text.text(f"🔄 Processing: {row['query']} ({index + 1}/{total_keywords})")
                                        progress_bar.progress(current_progress)
                                        
                                        # Generate post using content_generator
                                        post = self.content_generator.generate_post(row['query'], dict(row))
                                        
                                        if post:
                                            # Initialize image as None
                                            post['image'] = None
                                            
                                            try:
                                                with st.spinner("Generating image..."):
                                                    image_prompt = self.image_handler.generate_image_prompt(
                                                        query=post['keyword'],
                                                        intent=row.get('intent', ''),
                                                        excerpt=post.get('excerpt', '')
                                                    )
                                                    
                                                    if not image_prompt:
                                                        st.warning("⚠️ Failed to generate image prompt, continuing without image")
                                                    else:
                                                        st.info(f"ℹ️ Generated prompt: {image_prompt}")
                                                        
                                                        image_url = self.image_handler.fetch_image(image_prompt)
                                                        if not image_url or image_url.startswith("Error:"):
                                                            st.warning(f"⚠️ Image generation failed: {image_url}, continuing without image")
                                                        else:
                                                            post['image'] = image_url
                                                            st.success("✅ Image generated successfully")
                                            except Exception as img_error:
                                                st.warning(f"⚠️ Image generation error: {str(img_error)}, continuing without image")
                                            
                                            # Save post to database
                                            if self.save_generated_post(post):
                                                # Refresh saved posts immediately
                                                st.session_state.saved_posts_df = self.load_saved_posts()
                                                
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
                                                        button_key = f"upload_{len(st.session_state.generated_posts)}"
                                                        
                                                        # Initialize upload status in session state if not exists
                                                        if f"upload_status_{button_key}" not in st.session_state:
                                                            st.session_state[f"upload_status_{button_key}"] = None
                                                        
                                                        # Show upload button and status
                                                        if st.button("📤 Upload Now", key=button_key, type="primary"):
                                                            try:
                                                                with st.spinner("📡 Uploading to Shopify..."):
                                                                    result = asyncio.run(self.shopify_uploader.upload_post(post))
                                                                    st.session_state[f"upload_status_{button_key}"] = {
                                                                        "success": True,
                                                                        "message": f"✨ {result}"
                                                                    }
                                                                    
                                                                    # Update status in saved posts
                                                                    mask = st.session_state.saved_posts_df["Title"] == post["title"]
                                                                    st.session_state.saved_posts_df.loc[mask, "Status"] = "uploaded"
                                                                    
                                                                    # Save updated status
                                                                    self.df_storage.update_dataframe(
                                                                        self.df_storage.query_by_metadata({"type": "generated_posts"})[-1],
                                                                        st.session_state.saved_posts_df,
                                                                        "Updated post status after upload"
                                                                    )
                                                            except Exception as upload_error:
                                                                st.session_state[f"upload_status_{button_key}"] = {
                                                                    "success": False,
                                                                    "message": f"❌ Upload failed: {str(upload_error)}"
                                                                }
                                                                # Update status in saved posts
                                                                mask = st.session_state.saved_posts_df["Title"] == post["title"]
                                                                st.session_state.saved_posts_df.loc[mask, "Status"] = f"failed: {str(upload_error)}"
                                                        
                                                        # Display upload status if available
                                                        if st.session_state[f"upload_status_{button_key}"]:
                                                            status = st.session_state[f"upload_status_{button_key}"]
                                                            if status["success"]:
                                                                st.success(status["message"])
                                                            else:
                                                                st.error(status["message"])
                                                
                                                # Force UI refresh
                                                st.experimental_rerun()

                                        else:
                                            st.error(f"❌ Failed to generate post for: {row['query']}")

                                    except Exception as e:
                                        st.error(f"⚠️ Error processing {row['query']}: {str(e)}")

                                    # Update final progress
                                    current_progress = min(1.0, max(0.0, float(index + 1) / float(total_keywords)))
                                    progress_bar.progress(current_progress)
                                    status_text.text(f"📊 Processed {index + 1} of {total_keywords} keywords")

                                status_text.text("🎉 Processing complete!")
                                progress_bar.progress(1.0)
                                
                                # Refresh saved posts
                                st.session_state.saved_posts_df = self.load_saved_posts()
                        except Exception as e:
                            st.error(f"⚠️ Error in post generation process: {str(e)}")

        with main_tab2:
            st.header("Saved Posts")
            
            if not st.session_state.saved_posts_df.empty:
                # Create column configuration
                column_config = {
                    "Selected": st.column_config.CheckboxColumn(
                        "Select",
                        help="Select posts to upload",
                        default=False,
                    ),
                    "Title": st.column_config.TextColumn(
                        "Title",
                        width="large",
                    ),
                    "Status": st.column_config.TextColumn(
                        "Status",
                        width="small",
                    ),
                    "Generated Date": st.column_config.DatetimeColumn(
                        "Generated Date",
                        format="YYYY-MM-DD HH:mm",
                    )
                }
                
                # Show editable dataframe
                edited_df = st.data_editor(
                    st.session_state.saved_posts_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config=column_config,
                    disabled=["Keyword", "Title", "Excerpt", "Content", "Image", "Intent", "Volume", "Frequent Word", "Tab", "Generated Date"],
                    key="saved_posts_editor"
                )
                
                # Handle selection changes
                if not edited_df.equals(st.session_state.saved_posts_df):
                    st.session_state.saved_posts_df = edited_df
                    self.df_storage.update_dataframe(
                        self.df_storage.query_by_metadata({"type": "generated_posts"})[-1],
                        edited_df,
                        "Updated post selection"
                    )
                
                # Upload button for selected posts
                if st.button("📤 Upload Selected Posts", type="primary"):
                    selected_posts = st.session_state.saved_posts_df[st.session_state.saved_posts_df['Selected']]
                    if len(selected_posts) == 0:
                        st.warning("⚠️ Please select at least one post to upload")
                    else:
                        for _, post in selected_posts.iterrows():
                            try:
                                with st.spinner(f"📡 Uploading: {post['Title']}"):
                                    post_dict = {
                                        "keyword": post["Keyword"],
                                        "title": post["Title"],
                                        "excerpt": post["Excerpt"],
                                        "content": post["Content"],
                                        "image": post["Image"]
                                    }
                                    result = asyncio.run(self.shopify_uploader.upload_post(post_dict))
                                    st.success(f"✨ {result}")
                                    
                                    # Update status in DataFrame
                                    mask = st.session_state.saved_posts_df["Title"] == post["Title"]
                                    st.session_state.saved_posts_df.loc[mask, "Status"] = "uploaded"
                            except Exception as e:
                                st.error(f"❌ Failed to upload {post['Title']}: {str(e)}")
                                # Update status in DataFrame
                                mask = st.session_state.saved_posts_df["Title"] == post["Title"]
                                st.session_state.saved_posts_df.loc[mask, "Status"] = f"failed: {str(e)}"
                        
                        # Save updated status
                        self.df_storage.update_dataframe(
                            self.df_storage.query_by_metadata({"type": "generated_posts"})[-1],
                            st.session_state.saved_posts_df,
                            "Updated post status after upload"
                        )
            else:
                st.info("No saved posts found. Generate some posts in the Blog Post Generation tab!")

        with main_tab3:
            st.header("Settings")
            # Add any global settings here

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
        """Create a DataFrame from the generated posts and persist it"""
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
                "Tab": post.get("tab", ""),
                "Status": "pending"  # Track upload status
            })
        
        posts_df = pd.DataFrame(posts_data)
        
        # Store in DataFrame storage with metadata
        metadata = {
            "generation_date": datetime.now().isoformat(),
            "total_posts": len(posts_data),
            "source": "post_generation",
            "status": "pending_upload"
        }
        
        # If we already have a DataFrame for this generation session, update it
        if 'current_generation_df_id' in st.session_state:
            self.df_storage.update_dataframe(
                st.session_state.current_generation_df_id,
                posts_df,
                "Updated with new generated posts"
            )
        else:
            # Create new DataFrame
            df_id = self.df_storage.add_dataframe(
                df=posts_df,
                source="post_generation",
                metadata=metadata
            )
            st.session_state.current_generation_df_id = df_id
        
        return posts_df

    def get_selected_posts(self, generated_posts_df):
        """Get the selected posts from the UI and update their status"""
        selected_posts = []
        
        # Create a copy for status updates
        updated_df = generated_posts_df.copy()
        
        for idx, row in generated_posts_df.iterrows():
            if row["Selected"]:
                post = {
                    "keyword": row["Keyword"],
                    "title": row["Title"],
                    "excerpt": row["Excerpt"],
                    "content": row["Content"],
                    "image": row["Image"]
                }
                selected_posts.append(post)
                # Mark as queued for upload
                updated_df.at[idx, "Status"] = "queued"
        
        # Update the stored DataFrame with new status
        if 'current_generation_df_id' in st.session_state:
            self.df_storage.update_dataframe(
                st.session_state.current_generation_df_id,
                updated_df,
                "Updated post status to queued"
            )
        
        return selected_posts

    async def upload_posts(self, selected_posts: List[Dict]):
        """Upload selected posts to Shopify and update their status"""
        try:
            upload_count = 0
            current_df = self.df_storage.get_dataframe(st.session_state.current_generation_df_id)
            
            for post in selected_posts:
                try:
                    await self.shopify_uploader.upload_post(post)
                    upload_count += 1
                    
                    # Update status in DataFrame
                    mask = current_df["Keyword"] == post["keyword"]
                    current_df.loc[mask, "Status"] = "uploaded"
                except Exception as e:
                    # Mark failed uploads
                    mask = current_df["Keyword"] == post["keyword"]
                    current_df.loc[mask, "Status"] = f"failed: {str(e)}"
            
            # Update the stored DataFrame with final status
            self.df_storage.update_dataframe(
                st.session_state.current_generation_df_id,
                current_df,
                f"Updated status after uploading {upload_count} posts"
            )
            
            return f"Uploaded {upload_count} posts successfully!"
        except Exception as e:
            return f"Error uploading posts: {str(e)}"


if __name__ == "__main__":
    app = BlogAutomationApp()
    app.create_interface()