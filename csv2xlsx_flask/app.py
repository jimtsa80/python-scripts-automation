import os
import csv
import pandas as pd
from fuzzywuzzy import fuzz
from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import subprocess

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'csv', 'txt', 'xlsx', 'xls'}

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
                pair = (f"<b>{brand1}</b>", f"<b>{brand2}</b>") if brand1 < brand2 else (f"<b>{brand2}</b>", f"<b>{brand1}</b>")
                misspellings.add((csv_filename, pair))

    for location1 in location_names:
        for location2 in location_names:
            if location1 != location2 and fuzz.partial_token_sort_ratio(location1, location2) > 99:
                pair = (f"<b>{location1}</b>", f"<b>{location2}</b>") if location1 < location2 else (f"<b>{location2}</b>", f"<b>{location1}</b>")
                misspellings.add((csv_filename, pair))

    return misspellings

def csv_to_xlsx(input_folder, output_folder):
    files = os.listdir(input_folder)
    unique_base_filenames = set()
    messages = []

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
                try:
                    df = pd.read_csv(file_path, delimiter='\t', encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(file_path, delimiter='\t', encoding='latin1')
                
                # Check for empty values in "Brand" or "Location" columns
                empty_rows = df[df['Brand'].isnull() | df['Location'].isnull()]
                if not empty_rows.empty:
                    messages.append(f"Empty rows found in {file} and removed.")

                df = df.dropna(subset=['Brand', 'Location'])
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
                messages.append(f"Misspellings found in {base_filename}:")
                for misspelling in misspellings:
                    messages.append(f"Misspelling: {misspelling}")

            # Output the combined DataFrame to an Excel file
            output_file = os.path.join(output_folder, f"{base_filename}.xlsx")
            combined_df.to_excel(output_file, index=False)
            messages.append(f"Created {output_file} successfully.")

    return messages

def get_words_and_touchpoints_from_txt(txt_file):
    words_and_touchpoints = {}
    current_brand = None
    
    with open(txt_file, 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if line.startswith('#'):
                current_brand = line[1:]
                words_and_touchpoints[current_brand] = []
            elif current_brand:
                words_and_touchpoints[current_brand].append(line)
    
    return words_and_touchpoints

def check_brands_in_csvs(txt_file, folder, output_file):
    words_and_touchpoints = get_words_and_touchpoints_from_txt(txt_file)
    missing_brands = []
    missing_brands_set = set()

    for csv_filename in os.listdir(folder):
        if csv_filename.endswith('.csv'):
            csv_path = os.path.join(folder, csv_filename)
            try:
                with open(csv_path, 'r', encoding='utf-8') as csv_file:
                    reader = csv.DictReader(csv_file, delimiter='\t')
                    brands = {row['Brand'] for row in reader}
                    
                    for word in words_and_touchpoints.keys():
                        if word not in brands:
                            missing_brands.append((word, csv_filename))
                            missing_brands_set.add(word)
            except UnicodeDecodeError:
                with open(csv_path, 'r', encoding='latin1') as csv_file:
                    reader = csv.DictReader(csv_file, delimiter='\t')
                    brands = {row['Brand'] for row in reader}
                    
                    for word in words_and_touchpoints.keys():
                        if word not in brands:
                            missing_brands.append((word, csv_filename))
                            missing_brands_set.add(word)

    missing_messages = []
    for word, csv_filename in missing_brands:
        name = csv_filename.split("-")[1].split("-")[0]
        missing_message = f'Missing Brand: <b>{word}</b> || Blame: <b>{name}</b> for the file <b>{csv_filename}</b>'
        missing_messages.append(missing_message)

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for brand in sorted(missing_brands_set):
            outfile.write(f'#{brand}\n')
            for touchpoint in words_and_touchpoints[brand]:
                outfile.write(f'{touchpoint}\n')
    
    return missing_messages

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        files = request.files.getlist('files[]')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        messages = csv_to_xlsx(app.config['UPLOAD_FOLDER'], app.config['UPLOAD_FOLDER'])
        for message in messages:
            flash(message, 'success')
        return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/check_brands', methods=['GET', 'POST'])
def check_brands():
    if request.method == 'POST':
        txt_file = request.files['txt_file']
        csv_files = request.files.getlist('csv_files[]')
        if txt_file and allowed_file(txt_file.filename):
            txt_filename = secure_filename(txt_file.filename)
            txt_path = os.path.join(app.config['UPLOAD_FOLDER'], txt_filename)
            txt_file.save(txt_path)
            
            for file in csv_files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            output_file = os.path.join(app.config['UPLOAD_FOLDER'], 'output.txt')
            messages = check_brands_in_csvs(txt_path, app.config['UPLOAD_FOLDER'], output_file)
            for message in messages:
                flash(message, 'success')
        else:
            flash('Please upload a valid TXT file.', 'error')
        
        return redirect(url_for('check_brands'))

    return render_template('check_brands.html')

@app.route('/baseball_reshaper', methods=['GET', 'POST'])
def baseball_reshaper():
    if request.method == 'POST':
        if 'xlsx_file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['xlsx_file']
        
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Construct absolute path to run.bat
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'run.bat'))
            print(script_path)
            
            try:
                # Run the batch script with the uploaded file
                subprocess.run([script_path, file_path], check=True, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                flash('Scripts executed successfully!', 'success')
                return redirect(url_for('baseball_reshaper'))
            
            except subprocess.CalledProcessError as e:
                flash(f'Error running scripts: {e.stderr}', 'error')
                return redirect(url_for('baseball_reshaper'))

            flash('Scripts executed successfully!', 'success')
            return redirect(url_for('baseball_reshaper'))

    return render_template('baseball_reshaper.html')

@app.route('/clear_baseball_reshaper', methods=['POST'])
def clear_baseball_reshaper():
    # Logic to clear any temporary files or messages
    return redirect(url_for('baseball_reshaper'))

@app.route('/clear', methods=['POST'])
def clear():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    flash('Cleared all uploaded files.', 'success')
    return redirect(url_for('index'))

@app.route('/clear_check_brands', methods=['POST'])
def clear_check_brands():
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    flash('Cleared all uploaded files.', 'success')
    return redirect(url_for('check_brands'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.context_processor
def inject_now():
    return {'current_year': datetime.now().year}

if __name__ == '__main__':
    app.run(debug=True)
