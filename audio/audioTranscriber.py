import os
import sys
import subprocess
import traceback

import librosa
import soundfile as sf
import numpy as np
from tqdm import tqdm
from faster_whisper import WhisperModel

from resemblyzer import preprocess_wav, VoiceEncoder
from pydub import AudioSegment
from spectralcluster import SpectralClusterer

import re  # <-- Only standard regex needed for sentences

###################
# CONFIGURATION   #
###################
INPUT_FILE = "Victorian govt secretly handed $63 million to Tennis Australia.mp4"
CLEANED_AUDIO = "cleaned.wav"
CHUNK_FOLDER = "chunks"
OUTPUT_DIR = "transcripts"
MODEL_SIZE = "large-v3"
USE_GPU = False

for folder in [CHUNK_FOLDER, OUTPUT_DIR]:
    os.makedirs(folder, exist_ok=True)

if not os.path.isfile(INPUT_FILE):
    print(f"❌ Input file '{INPUT_FILE}' not found in {os.getcwd()}")
    sys.exit(1)

########################
# STEP 1: NORMALIZATION
########################
def denoise_audio(input_path, output_path):
    print("🔧 Normalizing audio with ffmpeg...")
    cmd = [
        "ffmpeg", "-i", input_path,
        "-ar", "16000", "-ac", "1",
        "-af", "loudnorm",
        output_path, "-y"
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print("ffmpeg stderr:", result.stderr.decode())
        raise RuntimeError("ffmpeg failed")
    print("✅ Normalization done.")

######################
# STEP 2: SPLIT AUDIO
######################
def split_audio(input_path, chunk_length_sec=30):
    print("🔪 Splitting audio into 30s chunks...")
    y, sr = librosa.load(input_path, sr=16000)
    total_duration = librosa.get_duration(y=y, sr=sr)
    num_chunks = int(np.ceil(total_duration / chunk_length_sec))
    chunk_paths = []
    for i in range(num_chunks):
        start_sample = int(i * chunk_length_sec * sr)
        end_sample = int(min((i + 1) * chunk_length_sec * sr, len(y)))
        chunk = y[start_sample:end_sample]
        chunk_path = os.path.join(CHUNK_FOLDER, f"chunk_{i:04d}.wav")
        sf.write(chunk_path, chunk, sr)
        chunk_paths.append((chunk_path, start_sample / sr, end_sample / sr))
    print(f"✅ Split into {len(chunk_paths)} chunks.")
    return chunk_paths

############################
# STEP 3: TRANSCRIBE CHUNKS
############################
def transcribe_chunks(chunk_tuples, output_folder, model_size=MODEL_SIZE, use_gpu=USE_GPU):
    print("🧠 Loading Whisper model...")
    compute_type = "float16" if use_gpu else "int8"
    device = "cuda" if use_gpu else "cpu"
    model = WhisperModel(model_size, compute_type=compute_type, device=device)
    print("✅ Whisper loaded.")

    chunk_segments = []
    for chunk_path, chunk_start, chunk_end in tqdm(chunk_tuples, desc="Transcribing"):
        segments, _ = model.transcribe(chunk_path, beam_size=5, vad_filter=False)
        lines = []
        for seg in segments:
            abs_start = seg.start + chunk_start
            abs_end   = seg.end + chunk_start
            text = seg.text.strip()
            lines.append(f"{abs_start:.2f}-{abs_end:.2f}: {text}")
            chunk_segments.append({
                "start": abs_start,
                "end": abs_end,
                "text": text
            })
        txt_path = os.path.join(output_folder, os.path.splitext(os.path.basename(chunk_path))[0] + ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    print(f"✅ All chunks transcribed ({len(chunk_segments)} segments).")
    return chunk_segments

###########################
# STEP 4: DIARIZATION
###########################
def diarize_with_resemblyzer(audio_path):
    print("👥 Performing diarization with Resemblyzer/SpectralCluster...")
    wav = preprocess_wav(audio_path)
    encoder = VoiceEncoder()
    _, partial_embeds, wav_splits = encoder.embed_utterance(wav, return_partials=True)
    clusterer = SpectralClusterer(
        min_clusters=2,
        max_clusters=8
    )
    labels = clusterer.predict(partial_embeds)
    SAMPLING_RATE = 16000
    diarization_segments = []
    last_label = labels[0]
    segment_start = 0
    for i, label in enumerate(list(labels) + [None]):
        if label != last_label or i == len(labels):
            seg_start_time = wav_splits[segment_start].start / SAMPLING_RATE
            seg_end_time   = wav_splits[i-1].stop / SAMPLING_RATE
            diarization_segments.append({
                "start": seg_start_time,
                "end": seg_end_time,
                "speaker": f"Speaker_{last_label + 1}"
            })
            segment_start = i
            last_label = label
    print(f"✅ Diarization segments: {len(diarization_segments)}")
    return diarization_segments

###############################################
# STEP 5: ALIGN DIARIZATION TO TRANSCRIPTIONS
###############################################
def assign_speakers_to_segments(segments, speakers):
    print("🎤 Assigning speakers to text...")
    speaker_segs = []
    for seg in segments:
        best_speaker = None
        best_overlap = 0.0
        for sp in speakers:
            overlap = min(seg['end'], sp['end']) - max(seg['start'], sp['start'])
            if overlap > 0 and overlap > best_overlap:
                best_overlap = overlap
                best_speaker = sp['speaker']
        if not best_speaker:
            best_speaker = "Unknown"
        speaker_segs.append({
            "start": seg['start'],
            "end": seg['end'],
            "speaker": best_speaker,
            "text": seg['text']
        })
    print(f"✅ Speakers assigned to {len(speaker_segs)} segments.")
    return speaker_segs

########################################################
# STEP 5.5: SPLIT SEGMENTS INTO SENTENCES BY REGEX
########################################################
def break_segments_by_sentence(speaker_segs):
    """
    Splits each segment into sentences (.?!), assigns timings proportionally.
    Returns a new list of dicts with start, end, speaker, text for each sentence.
    """
    new_segs = []
    # Regex: split after . ? ! followed by a space or end of string
    sentence_splitter = re.compile(r'(?<=[.!?])\s+')
    for seg in speaker_segs:
        text = seg['text']
        sentences = sentence_splitter.split(text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            continue
        total_len = sum(len(s) for s in sentences)
        seg_duration = seg['end'] - seg['start']
        offset = seg['start']
        for s in sentences:
            proportion = len(s) / total_len if total_len > 0 else 1.0 / len(sentences)
            sent_duration = proportion * seg_duration
            end_time = offset + sent_duration
            new_segs.append({
                "start": offset,
                "end": end_time,
                "speaker": seg['speaker'],
                "text": s
            })
            offset = end_time
    return new_segs

########################################################
# STEP 6: MULTIPLE OUTPUT FORMATS
########################################################
def save_final_transcript(speaker_segs, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for seg in speaker_segs:
            f.write(f"[{seg['start']:.2f}-{seg['end']:.2f}] {seg['speaker']}: {seg['text']}\n")
    print(f"✅ Output: {output_file}")

def save_plain_transcript(speaker_segs, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for seg in speaker_segs:
            f.write(f"{seg['speaker']}: {seg['text']}\n")
    print(f"✅ Output: {output_file}")

def save_just_text(speaker_segs, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        for seg in speaker_segs:
            f.write(f"{seg['text']}\n")
    print(f"✅ Output: {output_file}")

def save_merged_by_speaker(speaker_segs, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        if not speaker_segs:
            return
        last_speaker = speaker_segs[0]['speaker']
        paragraph = []
        for seg in speaker_segs:
            if seg['speaker'] == last_speaker:
                paragraph.append(seg['text'])
            else:
                f.write(f"{last_speaker}: {' '.join(paragraph)}\n\n")
                last_speaker = seg['speaker']
                paragraph = [seg['text']]
        if paragraph:
            f.write(f"{last_speaker}: {' '.join(paragraph)}\n\n")
    print(f"✅ Output: {output_file}")

###############################
# RUN THE PIPELINE
###############################
if __name__ == "__main__":
    print("----- PIPELINE START -----")
    try:
        denoise_audio(INPUT_FILE, CLEANED_AUDIO)
        chunk_tuples = split_audio(CLEANED_AUDIO)
        chunk_segments = transcribe_chunks(chunk_tuples, OUTPUT_DIR)
        diarization = diarize_with_resemblyzer(CLEANED_AUDIO)
        speaker_transcript = assign_speakers_to_segments(chunk_segments, diarization)

        # Use regex-based sentence splitting
        sent_segs = break_segments_by_sentence(speaker_transcript)

        out_full   = os.path.join(OUTPUT_DIR, "full_transcript.txt")
        out_plain  = os.path.join(OUTPUT_DIR, "plain_transcript.txt")
        out_text   = os.path.join(OUTPUT_DIR, "text_only.txt")
        out_merged = os.path.join(OUTPUT_DIR, "merged_by_speaker.txt")

        save_final_transcript(sent_segs, out_full)
        save_plain_transcript(sent_segs, out_plain)
        save_just_text(sent_segs, out_text)
        save_merged_by_speaker(sent_segs, out_merged)

        print(
            "\n🎉 Pipeline complete! Outputs saved:\n"
            f"  {out_full}\n"
            f"  {out_plain}\n"
            f"  {out_text}\n"
            f"  {out_merged}\n"
        )
    except Exception as e:
        print("❌ Pipeline failed:", e)
        traceback.print_exc()