import sys
import os
import csv

def get_words_from_txt(txt_file):
    with open(txt_file, 'r') as file:
        words = [line.strip() for line in file if line.startswith('#')]
    return [word[1:] for word in words]

def check_brands_in_csvs(txt_file, folder):
    words = get_words_from_txt(txt_file)
    missing_brands = []

    for csv_filename in os.listdir(folder):
        if csv_filename.endswith('.csv'):
            csv_path = os.path.join(folder, csv_filename)
            with open(csv_path, 'r') as csv_file:
                reader = csv.DictReader(csv_file, delimiter='\t')
                brands = {row['Brand'] for row in reader}
                
                for word in words:
                    if word not in brands:
                        missing_brands.append((word, csv_filename))

    for word, csv_filename in missing_brands:
        name = csv_filename.split("-")[1].split("-")[0]
        print(f'Missing Brand: {word} || Blame: {name} for the file {csv_filename}')
        

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python inquisitor.py <txt_file> <csv_folder>")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    csv_folder = sys.argv[2]

    check_brands_in_csvs(txt_file, csv_folder)
