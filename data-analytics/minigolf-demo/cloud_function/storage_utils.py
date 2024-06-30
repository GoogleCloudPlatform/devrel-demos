from google.cloud import storage

storage_client = storage.Client()

def download_video(bucket, file_name, temp_file):
    # Download the video to a temporary file
    with open(temp_file, "wb") as temp_file_handle:
        bucket = storage_client.get_bucket(bucket)
        blob = bucket.blob(file_name)
        blob.download_to_filename(temp_file)

def upload_image(bucket, user_id):
    bucket = storage_client.get_bucket(bucket)
    blob = bucket.blob(f"{user_id}.png")
    blob.upload_from_filename(f"/tmp/trajectory.png")
