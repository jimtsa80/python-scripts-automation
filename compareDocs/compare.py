import sys
from docx import Document

def read_docx(file_path):
    """Read the text from a DOCX file."""
    doc = Document(file_path)
    text = []
    for para in doc.paragraphs:
        text.append(para.text)
    return '\n'.join(text)

def compare_texts(text1, text2):
    """Compare two texts and return the differences."""
    lines1 = text1.splitlines()
    lines2 = text2.splitlines()
    
    diff = []
    for line in lines1:
        if line not in lines2:
            diff.append(f"- {line}")
    for line in lines2:
        if line not in lines1:
            diff.append(f"+ {line}")
    
    return '\n'.join(diff)

def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_docs.py <file1.docx> <file2.docx>")
        sys.exit(1)

    file1 = sys.argv[1]
    file2 = sys.argv[2]

    text1 = read_docx(file1)
    text2 = read_docx(file2)

    differences = compare_texts(text1, text2)
    print("Differences:")
    print(differences)

if __name__ == "__main__":
    main()
