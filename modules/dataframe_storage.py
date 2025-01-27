import json
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Union
import pandas as pd
from pathlib import Path

class DataFrameStorage:
    def __init__(self, data_dir: str = "data"):
        """Initialize the DataFrame storage system."""
        self.data_dir = Path(data_dir)
        self.db_file = self.data_dir / "db.json"
        self.dataframes: Dict[str, Dict] = {}
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Create data directory and load existing data if available."""
        try:
            self.data_dir.mkdir(exist_ok=True)
            if self.db_file.exists():
                with open(self.db_file, 'r') as f:
                    stored_data = json.load(f)
                    for df_id, df_info in stored_data.items():
                        df_data = pd.read_json(df_info['data'])
                        df_info['data'] = df_data
                        self.dataframes[df_id] = df_info
        except Exception as e:
            print(f"Error initializing storage: {str(e)}")
            self.dataframes = {}

    def _save_to_disk(self) -> None:
        """Save all DataFrames to disk."""
        try:
            serialized_data = {}
            for df_id, df_info in self.dataframes.items():
                serialized_info = df_info.copy()
                serialized_info['data'] = df_info['data'].to_json()
                serialized_data[df_id] = serialized_info

            with open(self.db_file, 'w') as f:
                json.dump(serialized_data, f, indent=2)
        except Exception as e:
            raise Exception(f"Error saving to disk: {str(e)}")

    def add_dataframe(self, df: pd.DataFrame, source: str, metadata: Optional[Dict] = None) -> str:
        """Add a new DataFrame with metadata."""
        df_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        df_info = {
            'id': df_id,
            'created_at': timestamp,
            'modified_at': timestamp,
            'source': source,
            'metadata': metadata or {},
            'data': df,
            'versions': [{
                'timestamp': timestamp,
                'data': df.to_json(),
                'comment': 'Initial version'
            }]
        }
        
        self.dataframes[df_id] = df_info
        self._save_to_disk()
        return df_id

    def update_dataframe(self, df_id: str, df: pd.DataFrame, comment: str = "") -> None:
        """Update an existing DataFrame and maintain version history."""
        if df_id not in self.dataframes:
            raise KeyError(f"DataFrame with id {df_id} not found")

        timestamp = datetime.now().isoformat()
        df_info = self.dataframes[df_id]
        
        # Add new version
        df_info['versions'].append({
            'timestamp': timestamp,
            'data': df.to_json(),
            'comment': comment
        })
        
        # Update current data
        df_info['data'] = df
        df_info['modified_at'] = timestamp
        
        self._save_to_disk()

    def get_dataframe(self, df_id: str) -> pd.DataFrame:
        """Retrieve a DataFrame by its ID."""
        if df_id not in self.dataframes:
            raise KeyError(f"DataFrame with id {df_id} not found")
        return self.dataframes[df_id]['data']

    def get_version_history(self, df_id: str) -> List[Dict]:
        """Get version history for a DataFrame."""
        if df_id not in self.dataframes:
            raise KeyError(f"DataFrame with id {df_id} not found")
        return self.dataframes[df_id]['versions']

    def query_by_metadata(self, query: Dict) -> List[str]:
        """Query DataFrames by metadata and return matching IDs."""
        matching_ids = []
        for df_id, df_info in self.dataframes.items():
            metadata = df_info['metadata']
            if all(metadata.get(k) == v for k, v in query.items()):
                matching_ids.append(df_id)
        return matching_ids

    def bulk_upload(self, file_path: str, source: str) -> List[str]:
        """Bulk upload DataFrames from a file."""
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(file_path)
            else:
                raise ValueError("Unsupported file format")

            df_id = self.add_dataframe(df, source, {'original_file': file_path})
            return [df_id]
        except Exception as e:
            raise Exception(f"Error during bulk upload: {str(e)}")

    def get_metadata(self, df_id: str) -> Dict:
        """Get metadata for a DataFrame."""
        if df_id not in self.dataframes:
            raise KeyError(f"DataFrame with id {df_id} not found")
        return self.dataframes[df_id]['metadata']

    def restore_version(self, df_id: str, version_index: int) -> None:
        """Restore a DataFrame to a previous version."""
        if df_id not in self.dataframes:
            raise KeyError(f"DataFrame with id {df_id} not found")
            
        df_info = self.dataframes[df_id]
        if version_index >= len(df_info['versions']):
            raise IndexError("Version index out of range")
            
        version_data = pd.read_json(df_info['versions'][version_index]['data'])
        self.update_dataframe(df_id, version_data, f"Restored to version {version_index}") 