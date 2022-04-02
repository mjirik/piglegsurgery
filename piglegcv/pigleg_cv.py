from pathlib import Path
import cv2
import json
import loguru
from loguru import logger
from typing import Optional
import shutil
import traceback
import time
try:
    from .run_tracker_lite import main_tracker
    from .run_mmpose import main_mmpose
    from .run_qr import main_qr
    from .run_report import main_report
    from .run_perpendicular import main_perpendicular, get_frame_to_process
    from .incision_detection_mmdet import predict_image
except ImportError as e:
    logger.debug(e)
    from run_tracker_lite import main_tracker
    from run_mmpose import main_mmpose
    from run_qr import main_qr
    from run_report import main_report
    from run_perpendicular import main_perpendicular, get_frame_to_process
    from incision_detection_mmdet import predict_image



def do_computer_vision(filename, outputdir):
    log_format = loguru._defaults.LOGURU_FORMAT
    logger_id = logger.add(
        str(Path(outputdir) / "piglegcv_log.txt"),
        format=log_format,
        level="DEBUG",
        rotation="1 week",
        backtrace=True,
        diagnose=True,
    )
    logger.debug(f"CV processing started on {filename}, outputdir={outputdir}")

    try:
        if Path(filename).suffix in (".png", ".PNG", ".jpg", ".JPG", ".jpeg", ".JPEG"):
            run_image_processing(filename, outputdir)
        else:
            run_video_processing(filename, outputdir)

        logger.debug("Work finished")
    except Exception as e:
        logger.error(traceback.format_exc())
    logger.remove(logger_id)


def run_video_processing(filename: Path, outputdir: Path) -> dict:
    logger.debug("Running video processing...")
    s = time.time()
    main_tracker("./.cache/tracker_model \"{}\" --output_dir {}".format(filename, outputdir))
    # run_media_processing(Path(filename), Path(outputdir))
    logger.debug(f"Detectron finished in {time.time() - s}s.")

    #
    # s = time.time()
    # main_mmpose(filename, outputdir)
    # logger.debug(f"MMpose finished in {time.time() - s}s.")

    main_qr(filename, outputdir)
    logger.debug("QR finished.")

    main_report(filename, outputdir)
    logger.debug("Report finished.")

    # if extention in images_types:

    run_image_processing(filename, outputdir)
    # main_perpendicular(filename, outputdir)
    # logger.debug("Perpendicular finished.")
    logger.debug("Video processing finished")
    pass

def run_image_processing(filename: Path, outputdir: Path) -> dict:
    logger.debug("Running image processing...")
    main_perpendicular(filename, outputdir)
    logger.debug("Perpendicular finished.")
    predict_image(filename, outputdir)
    logger.debug("Incision detection finished")

# def run_media_processing(filename: Path, outputdir: Path) -> dict:
#     """
#     Not used
#     Based on filename suffix the processing
#     :param filename:
#     :param outputdir:
#     :return:
#     """
#     isvideo = True
#     if isvideo:
#         return run_video_processing(filename, outputdir)
#     else:
#         return run_image_processing(filename, outputdir)
#
#
# def run_video_processing(filename: Path, outputdir: Path) -> dict:
#     """
#     Not used
#     :param filename:
#     :param outputdir:
#     :return:
#     """
#     # TODO here will be tracking
#     outputdir = Path(outputdir)
#     filename = Path(str(filename))
#     logger.debug("Video processing initiated...")
#     logger.debug(f"File '{filename.name}' exists={filename.exists()}")
#     outputdir.mkdir(parents=True, exist_ok=True)
#
#     # TODO here should be video processing with detectron2 (J. Vyskočil + Z. Krňoul)
#     tmp_dir_with_images = Path("tmp_video_processing") / filename.name
#     _make_images_from_video(filename, tmp_dir_with_images)
#
#     # Copy middle image to output dir
#     png_files = list(tmp_dir_with_images.glob("*.png"))
#     middle_img = Path(sorted(png_files)[int(len(png_files) / 2)])
#     shutil.copy(str(middle_img), str(outputdir))
#
#     # TODO here should be processing of the outptut of detectron2 (Z. Krňoul)
#
#     # TODO here should be handpose processing (J. Kanis)
#
#     return {
#         "Needle Holder Tip Track Length [m]": 123.5,
#         "Needle Holder Tip Avg Velocity [ms^1]": 123.5,
#     }
#
#
# def run_image_processing(filename: Path, outputdir: Path) -> dict:
#     """
#     Not used
#     :param filename:
#     :param outputdir:
#     :return:
#     """
#     # TODO here will be angle measurement
#     return {
#         "Stitch Angle 1 [°]": 0.75,
#         "Stitch Angle 2 [°]": 0.75,
#     }
#

def _make_images_from_video(filename: Path, outputdir: Path) -> Path:
    outputdir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(filename))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    frame_id = 0
    while cap.isOpened():
        ret, frame = cap.read()

        frame_id += 1
        if not ret:
            break
        else:
            file_name = "{}/frame_{:0>6}.png".format(outputdir, frame_id)
            cv2.imwrite(file_name, frame)
            logger.trace(file_name)
    cap.release()

    metadata = {"filename": str(filename), "fps": fps}
    json_file = outputdir / "meta.json"
    with open(json_file, "w") as f:
        json.dump(metadata, f)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process media file")
    parser.add_argument("filename", type=str)
    parser.add_argument("outputdir", type=str)
    args = parser.parse_args()
    do_computer_vision(Path(args.filename), Path(args.outputdir))
