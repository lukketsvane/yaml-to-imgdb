# Industrial Design Product Catalog

Automate image fetching & processing for industrial design products based on YAML data. Generates ready-to-use assets and a consolidated datatable.

## ▶️ Setup

1. **Environment Variables**:
   - `SERP_API_KEY`: For Google Images search
   - `REPLICATE_API_TOKEN`: For background removal
   - `IBB_API_KEY`: For image hosting
   
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🛠 Usage

1. Add designer data to YAML files in `data-store/`:
```yaml
Dieter Rams:
  T3 Radio: 1958
  606 Shelving System: { year: 1960, image: "custom-url.jpg" }
```

2. Run processing pipeline:
```bash
python run-all.py
```

## 📁 Data Structure

- **Original YAMLs**: `data-store/[designer].yaml`
- **Processed outputs**: `data-store-processed/`
  - Cleaned PNG images
  - Updated YAMLs with image URLs
  - Consolidated `datatable.yaml`

## ⚙️ Workflow

1. **Image Discovery**: Google Images search with white background
2. **Background Removal**: AI-powered processing
3. **Image Hosting**: Automatic upload to imgBB
4. **Data Export**: TypeScript-ready format generation
