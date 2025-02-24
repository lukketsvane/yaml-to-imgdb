import os
import base64
import mimetypes
import replicate
import requests
from tqdm import tqdm

if 'REPLICATE_API_TOKEN' not in os.environ:
    raise ValueError("REPLICATE_API_TOKEN environment variable not set")

client = replicate.Client(api_token=os.environ['REPLICATE_API_TOKEN'])
model_version = "alexgenovese/remove-background-bria-2:8a67c9d842f7c06fef1b6bcf44bfdccb48b6cca3b420843e705d4a64e04f8974"

os.makedirs('data-store-processed', exist_ok=True)

for root, dirs, files in os.walk('data-store'):
    for file in tqdm(files, desc=f"Processing {root}"):
        if not file.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        
        source_path = os.path.join(root, file)
        relative_path = os.path.relpath(source_path, 'data-store')
        dest_relative = os.path.splitext(relative_path)[0] + '.png'
        dest_path = os.path.join('data-store-processed', dest_relative)
        
        if os.path.exists(dest_path):
            continue
        
        try:
            with open(source_path, 'rb') as f:
                image_data = f.read()
        except Exception as e:
            print(f"Error reading {source_path}: {e}")
            continue
        
        mime_type = mimetypes.guess_type(source_path)[0] or 'application/octet-stream'
        base64_data = base64.b64encode(image_data).decode('utf-8')
        data_url = f"data:{mime_type};base64,{base64_data}"
        
        try:
            output_url = client.run(model_version, input={"image": data_url})
        except Exception as e:
            print(f"API error processing {source_path}: {e}")
            continue
        
        try:
            response = requests.get(output_url)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Failed to download processed image for {source_path}: {e}")
            continue
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        with open(dest_path, 'wb') as f:
            f.write(response.content)
        
        print(f"Successfully processed: {source_path} -> {dest_path}")
