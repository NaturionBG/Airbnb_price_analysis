import os
import pandas as pd
import requests
import boto3
from botocore.exceptions import ClientError
from tqdm import tqdm


EXCEL_FILE = "dataset.xlsx"         
URL_COLUMN = "image"                
BUCKET_NAME = "airbnb-images"            
MINIO_ENDPOINT = "http://localhost:9000"  
ACCESS_KEY = "naturion"           
SECRET_KEY = "naturionbg"          


s3 = boto3.client(
    's3',
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    use_ssl=False,        
)


try:
    s3.head_bucket(Bucket=BUCKET_NAME)
except ClientError:
    s3.create_bucket(Bucket=BUCKET_NAME)
    print(f"Bucket '{BUCKET_NAME}' created.")


df = pd.read_excel(EXCEL_FILE)
urls = df[URL_COLUMN].dropna().tolist()
print(f"Found {len(urls)} image URLs to upload.")


existing = set()
try:
    paginator = s3.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=BUCKET_NAME):
        if 'Contents' in page:
            existing.update(obj['Key'] for obj in page['Contents'])
except ClientError:
    pass  

uploaded = 0
failed = 0

for idx, url in enumerate(tqdm(urls, desc="Uploading")):
    object_key = f"image_{idx+1}.jpg"

    if object_key in existing:
        tqdm.write(f"Skipping {object_key} (already exists)")
        continue

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        s3.upload_fileobj(response.raw, BUCKET_NAME, object_key)
        uploaded += 1

    except Exception as e:
        tqdm.write(f"Failed to upload {object_key}: {e}")
        failed += 1

print(f"\nUploaded: {uploaded} new images, Failed: {failed}, Total URLs: {len(urls)}")