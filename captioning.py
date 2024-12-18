import os 
import cv2
import torch
from transformers import BlipForConditionalGeneration, BlipProcessor
from tqdm import tqdm
import csv
from src.model_query import ModelQuery

PROMPT_PATH = os.path.join(os.getcwd(), "src/prompt.txt")

def extract_frames(video_path, frame_rate=1):
    """
    Extract frames from a video file at a specified frame rate.
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS)
    interval = int(fps // frame_rate)

    success, frame = cap.read()
    count = 0
    while success:
        if count % interval == 0:
            frames.append(frame)
        success, frame = cap.read()
        count += 1
    cap.release()
    return frames


def generate_caption(model, processor, frame):
    """
    Generate a caption for a single frame using BLIP.
    """
    inputs = processor(images=frame, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
    caption = model.generate(**inputs)
    return processor.decode(caption[0], skip_special_tokens=True)


def video_captioning(video_path, frame_rate, model, processor):
    """
    Generate captions for a video by processing frames at a specified frame rate.
    """
    frames = extract_frames(video_path, frame_rate)
    
    captions = []
    print("Generating captions for frames...")
    for frame in tqdm(frames):
        caption = generate_caption(model, processor, frame)
        captions.append(caption)
        
    return captions


if __name__ == "__main__":
    
    print("Loading models...")
    blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
    blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base").to(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    model_query = ModelQuery()
    path_videos = os.path.join(os.getcwd(), "real_videos")
    
    video_files = [f for f in os.listdir(path_videos) if f.endswith(('.mp4'))]
    captions_data = []

    for video_file in sorted(video_files):
        print(f"Processing video: {video_file}")
        input_video = os.path.join(path_videos, video_file)
        captions = video_captioning(input_video, frame_rate=1, model=blip_model, processor=blip_processor)  # list
        
        # Step 1: NLU - Parse initial user input
        caption = model_query.query_model(
            system_prompt=PROMPT_PATH,
            input_file=str(captions)
        )    
        captions_data.append({"filename": video_file, "caption": caption})

        print(f"\n-----------------------------------Response from llama ({video_file})-----------------------------------\n")
        print(caption)
        print("\n-----------------------------------------------------------------------------------------\n")
    
    # Ensure the output directory exists
    os.makedirs(os.path.join(os.getcwd(), "output"), exist_ok=True)
    csv_file = os.path.join(os.getcwd(), "output/video_captions.csv")

    with open(csv_file, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["filename", "caption"])
        writer.writeheader()
        writer.writerows(captions_data)