import sys
import os
import csv

def get_words_and_touchpoints_from_txt(txt_file):
    words_and_touchpoints = {}
    current_brand = None
    
    with open(txt_file, 'r') as file:
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
            with open(csv_path, 'r') as csv_file:
                reader = csv.DictReader(csv_file, delimiter='\t')
                brands = {row['Brand'] for row in reader}
                
                for word in words_and_touchpoints.keys():
                    if word not in brands:
                        missing_brands.append((word, csv_filename))
                        missing_brands_set.add(word)

    for word, csv_filename in missing_brands:
        name = csv_filename.split("-")[1].split("-")[0]
        print(f'Missing Brand: {word} || Blame: {name} for the file {csv_filename}')

    with open(output_file, 'w') as outfile:
        for brand in sorted(missing_brands_set):
            outfile.write(f'#{brand}\n')
            for touchpoint in words_and_touchpoints[brand]:
                outfile.write(f'{touchpoint}\n')

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python inquisitor.py <txt_file> <csv_folder> <output_file>")
        sys.exit(1)
    
    txt_file = sys.argv[1]
    csv_folder = sys.argv[2]
    output_file = sys.argv[3]

    check_brands_in_csvs(txt_file, csv_folder, output_file)
