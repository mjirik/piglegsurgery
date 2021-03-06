from pathlib import Path
from typing import Optional
import cv2
from loguru import logger
import json
import subprocess
from .visualization_tools import crop_square



def make_images_from_video(filename: Path, outputdir: Path, n_frames=None,
                           scale=1,
                           filemask:str="{outputdir}/frame_{frame_id:0>6}.png",
                           width:Optional[int]=None,
                           height:Optional[int]=None,
                           make_square:bool=False
                           ) -> Path:
    import cv2
    outputdir.mkdir(parents=True, exist_ok=True)


    cap = cv2.VideoCapture(str(filename))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    if width:
        scale = None

    frame_id = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if frame is None:
            logger.warning(f"Reading frame {frame_id} in {str(filename)} failed.")
            break
        if scale is None and width is not None:
            scale = width / frame.shape[1]
        if scale is None and height is not None:
            scale = height / frame.shape[0]

        frame_id += 1
        if frame_id > n_frames:
            break
        if not ret:
            break
        else:
            file_name = filemask.format(outputdir=outputdir, frame_id=frame_id)
            frame = rescale(frame, scale)
            if make_square:
                frame = crop_square(frame)
            cv2.imwrite(file_name, frame)
            logger.trace(file_name)
    cap.release()

    metadata = {"filename_full": str(filename), "fps": fps}
    json_file = outputdir / "meta.json"
    with open(json_file, "w") as f:
        json.dump(metadata, f)

def rescale(frame, scale):
    import cv2
    if scale != 1:
        width = int(frame.shape[1] * scale)
        height = int(frame.shape[0] * scale)
        dim = (width, height)
        # resize image
        frame = cv2.resize(frame, dim, interpolation=cv2.INTER_AREA)
    return frame


def convert_avi_to_mp4(avi_file_path, output_name):
    s = ["ffmpeg", '-i', avi_file_path, '-ac', '2', "-y", "-b:v", "2000k", "-c:a", "aac", "-c:v", "libx264", "-b:a", "160k",
         "-vprofile", "high", "-bf", "0", "-strict", "experimental", "-f", "mp4", output_name]
    subprocess.call(s)
    return True
