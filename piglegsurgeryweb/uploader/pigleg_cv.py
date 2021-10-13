from pathlib import Path
import cv2
import json
from loguru import logger


def run_media_processing(filename: Path, outputdir: Path) -> dict:
    """
    Based on filename suffix the processing
    :param filename:
    :param outputdir:
    :return:
    """
    isvideo = True
    if isvideo:
        return run_video_processing(filename, outputdir)
    else:
        return run_image_processing(filename, outputdir)


def run_video_processing(filename: Path, outputdir: Path) -> dict:
    # TODO here will be tracking
    outputdir = Path(outputdir)
    filename = Path(str(filename))
    logger.debug("Video processing initiated...")
    logger.debug(f"File '{filename.stem}' exists={filename.exists()}")
    outputdir.mkdir(parents=True, exist_ok=True)

    # TODO here should be video processing with detectron2 (J. Vyskocil + Z. Krnoul)
    tmp_dir_with_images:Path = _make_images_from_video(filename)

    # TODO here should be processing of the outptut of detectron2 (Z. Krnoul)

    # TODO here should be handpose processing (J. Kanis)

    return {
        "Needle Holder Tip Track Length [m]": 123.5,
        "Needle Holder Tip Avg Velocity [ms^1]": 123.5,
    }


def run_image_processing(filename: Path, outputdir: Path) -> dict:
    # TODO here will be angle measurement
    return {
        "Stitch Angle 1 [°]": 0.75,
        "Stitch Angle 2 [°]": 0.75,
    }


def _make_images_from_video(filename: Path) -> Path:
    tmp_dir = Path("tmp_video_processing") / filename.stem
    tmp_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(filename))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    frame_id = 0
    while cap.isOpened():
        ret, frame = cap.read()

        frame_id += 1
        if not ret:
            break
        else:
            file_name = "{}/frame_{:0>6}.png".format(tmp_dir, frame_id)
            cv2.imwrite(file_name, frame)
            logger.trace(file_name)
    cap.release()

    metadata = {"filename": str(filename), "fps": fps}
    json_file = tmp_dir / "meta.json"
    with open(json_file, "w") as f:
        json.dump(metadata, f)

    return tmp_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process media file")
    parser.add_argument("filename", type=str)
    parser.add_argument("outputdir", type=str)
    args = parser.parse_args()
    run_media_processing(Path(args.filename), Path(args.outputdir))
