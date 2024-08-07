import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Union

import numpy as np
from loguru import logger

try:
    from structure_tools import save_json, load_json
except ImportError:
    from .structure_tools import save_json, load_json


def make_images_from_video(
    filename: Path,
    outputdir: Path,
    n_frames=None,
    scale=1,
    filemask: str = "{outputdir}/frame_{frame_id:0>6}.png",
    width: Optional[int] = None,
    height: Optional[int] = None,
    make_square: bool = False,
    create_meta_json: bool = True,
) -> Path:
    import cv2

    outputdir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(filename))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    totalframecount = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if width:
        scale = None
    if height:
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

    if create_meta_json:
        metadata = {
            "filename_full": str(filename),
            "fps": fps,
            "frame_count": totalframecount,
        }
        json_file = outputdir / "meta.json"
        save_json(metadata, json_file)


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
    s = [
        "ffmpeg",
        "-i",
        avi_file_path,
        "-ac",
        "2",
        "-y",
        "-b:v",
        "2000k",
        "-c:a",
        "aac",
        "-c:v",
        "libx264",
        "-b:a",
        "160k",
        "-vprofile",
        "high",
        "-bf",
        "0",
        "-strict",
        "experimental",
        "-f",
        "mp4",
        output_name,
    ]
    subprocess.call(s)
    return True


def crop_square(frame: np.ndarray) -> np.ndarray:

    mn = np.min(frame.shape[:2])
    sh0 = frame.shape[0]
    sh1 = frame.shape[1]
    if sh0 > sh1:
        st0 = int((sh0 / 2) - (sh1 / 2))
        st1 = 0
    else:
        st0 = 0
        st1 = int((sh1 / 2) - (sh0 / 2))

    frame = frame[st0 : st0 + mn, st1 : st1 + mn]

    return frame
