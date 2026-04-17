import os
from backend.services.supabase import supabase

BUCKET_NAME = os.environ.get("SUPABASE_FIGHTER_IMAGE_BUCKET")

def upload_img(file_path, file, content_type):
    '''
        Uploads image file to Supabase storage bucket.
    '''
    try:
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path, 
            file=file,
            file_options={
                "content-type": content_type,
                "upsert": "true"
            }
            
            )
        print(f"Image uploaded successfully to {BUCKET_NAME}/{file_path}")
    except Exception as e:
        print(f"Error uploading image to {BUCKET_NAME}/{file_path}: {e}")