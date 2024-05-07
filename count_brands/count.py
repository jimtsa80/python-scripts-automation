import os
import pandas as pd

def process_folder(folder_path):

    results_df = pd.DataFrame(columns=['Filename', 'Brand', 'Location', 'Total_Duration'])
    
    for file_name in os.listdir(folder_path):
        if file_name.endswith('.csv') or file_name.endswith('.xlsx'):
            file_path = os.path.join(folder_path, file_name)
            filename, brand_duration_counts = process_file(file_path)
            
            for (brand, location), total_duration in brand_duration_counts.items():
                df = pd.DataFrame({'Filename': [filename],
                                   'Brand': [brand],
                                   'Location': [location],
                                   'Total_Duration': [total_duration]})
                results_df = pd.concat([results_df, df], ignore_index=True)
    
    return results_df

def process_file(file_path):
    _, extension = os.path.splitext(file_path)
    if extension == '.csv':
        df = pd.read_csv(file_path, delimiter='\t')
    elif extension == '.xlsx':
        df = pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format")
    
    brand_duration_counts = df.groupby(['Brand', 'Location'])['Duration'].sum()

    filename = os.path.basename(file_path)
    
    return filename, brand_duration_counts


def main():

    folder_path = input("Enter the folder path containing results files: ")
    
    results_df = process_folder(folder_path)
    
    output_file = 'output.xlsx'
    results_df.to_excel(output_file, index=False)
    
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()
