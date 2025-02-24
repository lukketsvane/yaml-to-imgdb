import os
import glob
import yaml

# Define input and output directories.
INPUT_DIR = "data-yaml"  # Folder containing your YAML files
OUTPUT_DIR = "ts-data"   # Folder where the .ts files will be saved

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Iterate over all YAML files in the input directory.
for yaml_path in glob.glob(os.path.join(INPUT_DIR, "*.yaml")):
    with open(yaml_path, "r") as f:
        try:
            data = yaml.safe_load(f)
        except Exception as e:
            print(f"Error parsing {yaml_path}: {e}")
            continue

    # Assume each YAML file contains a list of timeline items
    # Each item should have: id, year, imageUrl, name.
    if not isinstance(data, list):
        print(f"Skipping {yaml_path}: YAML content is not a list.")
        continue

    # Use the YAML file's base name to generate the export variable name.
    base_name = os.path.splitext(os.path.basename(yaml_path))[0]
    # e.g., if file is "os.yaml" then we get "osData"
    export_var = f"{base_name}Data"

    # Prepare the TypeScript file content.
    ts_lines = []
    ts_lines.append('import type { TimelineItem } from "./types";\n\n')
    ts_lines.append(f"export const {export_var}: TimelineItem[] = [\n")

    for item in data:
        # Validate required keys in each timeline item.
        if not all(key in item for key in ("id", "year", "imageUrl", "name")):
            print(f"Skipping an item in {yaml_path}: missing one of the required keys.")
            continue

        ts_lines.append("  {\n")
        ts_lines.append(f"    id: {item['id']},\n")
        ts_lines.append(f"    year: {item['year']},\n")
        ts_lines.append(f"    imageUrl: \"{item['imageUrl']}\",\n")
        ts_lines.append(f"    name: \"{item['name']}\"\n")
        ts_lines.append("  },\n")

    ts_lines.append("];\n")

    # Write the TS file to the output directory.
    ts_filename = os.path.join(OUTPUT_DIR, f"{base_name}.ts")
    with open(ts_filename, "w") as ts_file:
        ts_file.write("".join(ts_lines))
    
    print(f"Generated {ts_filename}")
