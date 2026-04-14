import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")
    return create_client(url, key)

def upload_to_supabase(file_obj, file_name, folder="media"):
    """
    Uploads a file-like object to a Supabase Storage bucket and returns the public URL.
    Ensure bucket 'media' is public.
    """
    supabase = get_supabase_client()
    
    # Path inside the bucket
    bucket_name = os.environ.get("SUPABASE_BUCKET", "media")
    file_path = f"{folder}/{file_name}"
    
    # Upload file
    # file_obj can be request.FILES['image'] in Django view
    file_bytes = file_obj.read()
    
    # Upload to standard storage bucket (requires configuration in Supabase dashboard)
    supabase.storage.from_(bucket_name).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": file_obj.content_type if hasattr(file_obj, 'content_type') else "application/octet-stream"}
    )
    
    # Retrieve public URL
    public_url = supabase.storage.from_(bucket_name).get_public_url(file_path)
    
    return public_url
