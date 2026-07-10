import re
import sys

def parse_line(line):
    m = re.match(r"\[(\d+\.\d+)-(\d+\.\d+)\] ([^:]+): (.*)", line.strip())
    if m:
        return float(m.group(1)), float(m.group(2)), m.group(3), m.group(4)
    return None

def ends_with_sentence(text):
    return text.rstrip().endswith(('.', '!', '?'))

def merge_transcript(filename):
    merged_lines = []
    prev_start = prev_end = None
    prev_speaker = prev_text = None

    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            result = parse_line(line)
            if not result:
                continue

            start, end, speaker, text = result
            if prev_speaker is None:
                prev_start, prev_end, prev_speaker, prev_text = start, end, speaker, text
                continue

            if speaker == prev_speaker and not ends_with_sentence(prev_text):
                prev_end = end
                prev_text += ' ' + text
            else:
                merged_lines.append(f"[{prev_start:.2f}-{prev_end:.2f}] {prev_speaker}: {prev_text}")
                prev_start, prev_end, prev_speaker, prev_text = start, end, speaker, text

        if prev_speaker is not None:
            merged_lines.append(f"[{prev_start:.2f}-{prev_end:.2f}] {prev_speaker}: {prev_text}")

    return merged_lines

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python merge_transcript.py <input_file.txt>")
        sys.exit(1)

    input_file = sys.argv[1]
    merged = merge_transcript(input_file)

    # Overwrite input file
    with open(input_file, "w", encoding="utf-8") as f:
        for line in merged:
            f.write(line + "\n")