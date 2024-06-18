import os
import pandas as pd
from fuzzywuzzy import fuzz
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def find_misspellings(df, csv_filename):
    brand_names = df['Brand'].astype(str).unique()
    location_names = df['Location'].astype(str).unique()
    misspellings = set()

    for brand1 in brand_names:
        for brand2 in brand_names:
            if brand1 != brand2 and fuzz.partial_token_sort_ratio(brand1, brand2) > 99:
                pair = (brand1, brand2) if brand1 < brand2 else (brand2, brand1)
                misspellings.add((csv_filename, pair))

    for location1 in location_names:
        for location2 in location_names:
            if location1 != location2 and fuzz.partial_token_sort_ratio(location1, location2) > 99:
                pair = (location1, location2) if location1 < location2 else (location2, location1)
                misspellings.add((csv_filename, pair))

    return misspellings

def csv_to_xlsx(input_folder, output_folder):
    files = os.listdir(input_folder)
    unique_base_filenames = set()

    # Extract base filenames from all files in the input folder
    for file in files:
        if file.endswith('.csv'):
            # Determine base filename based on "part" prefix or "-"
            if file.startswith("part"):
                base_filename = "_".join(file.split("_")[1:]).split('-')[0]
            else:
                base_filename = file.split('-')[0]

            unique_base_filenames.add(base_filename)

    # Iterate over unique base filenames to concatenate related CSV files
    for base_filename in unique_base_filenames:
        dfs = []
        csv_filenames = []  # Maintain a list of CSV filenames for potential misspellings
        for file in files:
            if file.endswith('.csv') and base_filename in file:
                csv_filenames.append(file)  # Store the CSV filename
                file_path = os.path.join(input_folder, file)
                df = pd.read_csv(file_path, delimiter='\t')
                
                # Check for empty values in "Brand" or "Location" columns
                empty_rows = df[df['Brand'].isnull() | df['Location'].isnull()]
                if not empty_rows.empty:
                    print(f"Empty rows found in {file}:")
                    print(empty_rows)
                    print("Removing empty rows...")
                    df = df.drop(empty_rows.index)

                dfs.append(df)

        if dfs:
            # Concatenate DataFrames and sort by the last column
            combined_df = pd.concat(dfs, ignore_index=True)
            combined_df.sort_values(by=combined_df.columns[-1], inplace=True)
            
            # Convert csv_filenames list to tuple for hashability
            csv_filenames_tuple = tuple(csv_filenames)
            
            # Call find_misspellings with the concatenated DataFrame and CSV filenames
            misspellings = find_misspellings(combined_df, csv_filenames_tuple)
            if misspellings:
                print("Misspellings found in:", base_filename)
                for misspelling in misspellings:
                    print("Misspelling:", misspelling)
                print()

            # Output the combined DataFrame to an Excel file
            output_file = os.path.join(output_folder, f"{base_filename}.xlsx")
            combined_df.to_excel(output_file, index=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        files = request.files.getlist('files[]')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        csv_to_xlsx(app.config['UPLOAD_FOLDER'], app.config['UPLOAD_FOLDER'])
        flash('Files processed successfully!', 'success')
        return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
