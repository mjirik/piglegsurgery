import glob
import json
import os
import os.path as op
import shutil
import subprocess
import time
import traceback

# from .pigleg_cv import run_media_processing
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Tuple

import django.utils
import gspread
import loguru
import numpy as np
import pandas as pd
import requests
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template import defaultfilters
from django.utils.html import strip_tags
from django_q.models import Schedule
from django_q.tasks import async_task, queue_size, schedule
from loguru import logger
from oauth2client.service_account import ServiceAccountCredentials

from .data_tools import (
    flatten_dict,
    google_spreadsheet_append,
    remove_empty_lists,
    remove_iterables_from_dict,
)
from .media_tools import convert_avi_to_mp4, make_images_from_video, rescale
from .models import BitmapImage, UploadedFile, Owner
from .visualization_tools import crop_square


def _run_media_processing_rest_api(
    input_file: Path,
    outputdir: Path,
    is_microsurgery: bool,
    n_stitches: int,
    hostname="127.0.0.1",
    port=5000,
):

    # query = {"filename": "/webapps/piglegsurgery/tests/pigleg_test.mp4", "outputdir": "/webapps/piglegsurgery/tests/outputdir"}
    logger.debug("Creating request for processing")
    logger.debug(f"hostname={hostname}, port={port}")
    query = {
        "filename": str(input_file),
        "outputdir": str(outputdir),
        "is_microsurgery": is_microsurgery,
        "n_stitches": n_stitches,
    }
    url = f"http://{hostname}:{port}/run"
    try:
        response = requests.post(url, params=query)
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.debug(f"REST API processing not finished. Connection refused. url={url}")
        return
    logger.debug("Checking if processing is finished...")

    hash = response.json()
    is_finished = False
    tm = 0
    time_to_sleep = 4
    while not is_finished:
        time_to_sleep = time_to_sleep * 2 if time_to_sleep < 64 else 64
        time_step = 4
        tm += time_to_sleep
        for i in range(int(time_to_sleep / time_step)):
            time.sleep(time_step)
        response = requests.get(
            f"http://{hostname}:{port}/is_finished/{hash}",
            # params=query
        )
        is_finished = response.json()
        logger.debug(
            f".    is_finished={is_finished}  input_file={input_file.name}  time[s]={tm} queue_size={queue_size()}"
        )

    if type(is_finished) == str:
        logger.warning(
            f"REST API processing failed. input_file={input_file.name}  time[s]={tm}"
        )
    else:
        logger.debug(f"REST API processing finished.")


def run_processing(serverfile: UploadedFile, absolute_uri, hostname, port):
    outputdir = Path(serverfile.outputdir)

    # delete outputdir but keep tracks.json
    if outputdir.exists() and outputdir.is_dir():
        tracks_json_path = outputdir / "tracks.json"
        tracks_json_tmp_path = outputdir.parent / "tracks.json.tmp"
        tracks_json_tmp_path.unlink(missing_ok=True)
        if tracks_json_path.exists():
            shutil.move(tracks_json_path, tracks_json_tmp_path)
        shutil.rmtree(outputdir, ignore_errors=True)
        if tracks_json_tmp_path.exists():
            outputdir.mkdir(parents=True, exist_ok=True)
            shutil.move(tracks_json_tmp_path, tracks_json_path)
    else:
        outputdir.mkdir(parents=True, exist_ok=True)
    log_format = loguru._defaults.LOGURU_FORMAT
    logger_id = logger.add(
        str(Path(serverfile.outputdir) / "webapp_log.txt"),
        format=log_format,
        level="DEBUG",
        rotation="1 week",
        backtrace=True,
        diagnose=True,
    )
    logger.debug(f"Image processing of '{serverfile.mediafile}' initiated")
    make_preview(serverfile)
    if serverfile.zip_file and Path(serverfile.zip_file.path).exists():
        serverfile.zip_file.delete()
    input_file = Path(serverfile.mediafile.path)
    logger.debug(f"input_file={input_file}")
    outputdir = Path(serverfile.outputdir)
    logger.debug(f"outputdir={outputdir}")

    _run_media_processing_rest_api(
        input_file,
        outputdir,
        serverfile.is_microsurgery,
        int(serverfile.stitch_count),
        hostname,
        port,
    )

    # (outputdir / "empty.txt").touch(exist_ok=True)

    if input_file.suffix in (".mp4", ".avi", ".mov", ".webm"):
        make_images_from_video(input_file, outputdir=outputdir, n_frames=1)

    # for video_pth in outputdir.glob("*.avi"):
    #     input_video_file = video_pth
    #     output_video_file = video_pth.with_suffix(".mp4")
    #     logger.debug(f"input_video_file={input_video_file}")
    #     logger.debug(f"outout_video_file={output_video_file}")
    #     if output_video_file.exists():
    #         output_video_file.unlink()
    #     _convert_avi_to_mp4(str(input_video_file), str(output_video_file))
    add_generated_images(serverfile)
    make_zip(serverfile)

    add_status_to_uploaded_file(serverfile)

    serverfile.finished_at = django.utils.timezone.now()
    serverfile.save()
    _add_row_to_spreadsheet(serverfile, absolute_uri)
    html_path = make_graph_for_owner(serverfile.owner)
    logger.debug("Processing finished")
    logger.remove(logger_id)
    
def make_graph_for_owner(owner:Owner):
    # owner = get_object_or_404(Owner, hash=owner_hash)
    order_by = request.GET.get("order_by", "-uploaded_at")
    files = UploadedFile.objects.filter(owner=owner).order_by(order_by)
    return make_graph(files, owner)

    

def get_graph_path(owner: Optional[Owner] = None):
    if owner:
        html_path = Path(settings.MEDIA_ROOT) / "generated" / owner.hash / "graph.html"
    else:
        html_path = Path(settings.MEDIA_ROOT) / "generated/graph.html"
    return html_path


def make_graph(
    uploaded_file_set: UploadedFile.objects.all(), owner: Optional[Owner] = None,
):
    import pandas as pd
    import plotly.express as px
    from django.utils import timezone

    html_path = _get_graph_path(owner)
    html_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []

    for i, uploaded_file in enumerate(uploaded_file_set):

        results_path = Path(uploaded_file.outputdir) / "results.json"
        # read results.json
        if results_path.exists():
            with open(results_path) as f:
                loaded_results = json.load(f)
            # fix typo
            if "Stichtes linearity score" in loaded_results:
                loaded_results["Stitches linearity score"] = loaded_results.pop("Stichtes linearity score")
            loaded_results["Uploaded at"] = uploaded_file.uploaded_at
            loaded_results["i"] = i
            rows.append(loaded_results)

    df = pd.DataFrame(rows)


    if "Stitches linearity score" in df.keys():
        df["Stitches linearity score [%]"] = df["Stitches linearity score"] * 100

    if "Stitches parallelism score" in df.keys():
        df["Stitches parallelism score [%]"] = df["Stitches parallelism score"] * 100

    y = [
        "Needle holder visibility [%]",
        "Needle holder area presence [%]",
        "Forceps visibility [%]",
        "Forceps area presence [%]",
        "Stitches linearity score [%]",
        "Stitches parallelism score [%]",
    ]

    y = [element for element in y if element in df.keys()]
    if len(y) == 0:
        return None
    # x = list(df.keys())
    #
    # x = [el for el in x if el != 'Uploaded at']

    x = "Uploaded at"
    import plotly.express as px

    fig = px.scatter(
        df,
        x=x,
        y=y,
        # marginal_x="box",
        # marginal_y="box"
    )
    fig.write_html(html_path, full_html=False)
    return html_path
    
    

def add_row_to_spreadsheet_and_update_zip(serverfile: UploadedFile, absolute_uri):
    logger.debug("Updating spreadsheet...")
    _add_row_to_spreadsheet(serverfile, absolute_uri)
    # logger.debug("Spreadsheet updated")
    # if serverfile.zip_file and Path(serverfile.zip_file.path).exists():
    #     serverfile.zip_file.delete()
    # make_zip(serverfile)
    logger.debug("Zip updated")

def add_status_to_uploaded_file(serverfile:UploadedFile):
    """
    Find status in piglegcv log file. Status is the last line of the file.
    If line contain "Work finished", everything is OK. If line contain error,
    the processing failed.
    """
    piglegcv_log_path = Path(serverfile.outputdir) / "piglegcv_log.txt"
    is_ok = False
    if not piglegcv_log_path.exists():
        is_ok = False
        status = "Log file does not exist."
    else:
        with open(piglegcv_log_path, "r") as fr:
            lines = fr.readlines()
            if len(lines) == 0:
                is_ok = False
                status = "Log file is empty."
                return is_ok, status
            last_line = lines[-1]
            if "Work finished" in last_line:
                is_ok = True
                status = "Work finished."
            else:
                is_ok = False
                status = last_line
    serverfile.processing_ok = is_ok
    serverfile.processing_message = status
    serverfile.save()


def _add_row_to_spreadsheet(serverfile, absolute_uri):

    creds_file = Path(settings.CREDS_JSON_FILE)  # 'piglegsurgery-1987db83b363.json'
    if not creds_file.exists():
        logger.error(f"Credetials file does not exist. Expected path: {creds_file}")
        return
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)

    novy = {}

    filename = Path(serverfile.outputdir) / "meta.json"
    if os.path.isfile(filename):
        with open(filename, "r") as fr:
            data = json.load(fr)
            novy.update(data)

    # filename = Path(serverfile.outputdir) / "evaluation.json"
    filename = Path(serverfile.outputdir) / "results.json"
    if os.path.isfile(filename):
        with open(filename, "r") as fr:
            data = json.load(fr)
            novy.update(data)

    novy.update(
        {
            "email": serverfile.email,
            "filename_full": str(Path(serverfile.mediafile.name)),
            # return str(Path(self.mediafile.name).name)
            "filename": str(Path(serverfile.mediafile.name).name),
            # "uploaded_at": None if serverfile.uploaded_at is None else serverfile.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            # "finished_at": None if serverfile.finished_at is None else serverfile.finished_at.strftime('%Y-%m-%d %H:%M:%S'),
            "uploaded_at": None
            if serverfile.uploaded_at is None
            else defaultfilters.date(serverfile.uploaded_at, "Y-m-d H:i"),
            "finished_at": None
            if serverfile.finished_at is None
            else defaultfilters.date(serverfile.finished_at, "Y-m-d H:i"),
            "filename_full": serverfile.mediafile.name,
            "report_url": f"{absolute_uri}/uploader/web_report/{serverfile.hash}",
            "processing_ok": serverfile.processing_ok,
            "processing_message": serverfile.processing_message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )

    annotation = serverfile.mediafileannotation_set.first()
    # meta = {
    # }
    # data_tools.save_json(meta, Path(serverfile.outputdir) / "meta.json", update=True)

    if annotation:
        novy.update(
            {
                "annotation":{
                    'annotation': {
                        "annotation": str(annotation.annotation),
                        "stars": int(annotation.stars) if annotation.stars is not None else -1,
                        "annotator": str(annotation.annotator) if annotation.annotator is not None else "",
                        "updated_at": str(annotation.updated_at),
                    }

                }
            }
        )

    pop_from_dict(novy, "incision_bboxes")
    pop_from_dict(novy, "filename_full")
    novy = remove_empty_lists(flatten_dict(novy))
    pop_from_dict(novy, "qr_data_box")

    # novy = remove_iterables_from_dict(novy)
    logger.debug(f"novy={novy}")
    df_novy = pd.DataFrame(novy, index=[0])

    google_spreadsheet_append(title="Pigleg Surgery Stats", creds=creds, data=df_novy)


def pop_from_dict(d, key):
    if key in d:
        d.pop(key)


def make_preview(
    serverfile: UploadedFile, force: bool = False, height=100, make_square: bool = True
) -> Path:
    if serverfile.mediafile:
        input_file = Path(serverfile.mediafile.path)
        # if not input_file.exists():
        #     return
        filename = input_file.parent / "preview.jpg"
        filename_rel = filename.relative_to(settings.MEDIA_ROOT)
        # logger.debug(f"  {input_file=}")
        # logger.debug(f"    {filename=}")
        # logger.debug(f"{filename_rel=}")
        if (not filename.exists()) or force:
            if input_file.suffix.lower() in (".mp4", ".avi", ".mov", ".webm"):
                fn = serverfile.mediafile
                make_images_from_video(
                    input_file,
                    outputdir=input_file.parent,
                    n_frames=1,
                    # filemask="{outputdir}/preview.jpg",
                    filemask=str(filename),
                    # scale=0.125,
                    height=height,
                    make_square=make_square,
                )
            elif input_file.suffix.lower() in (
                ".jpg",
                ".jpeg",
                ".tiff",
                ".tif",
                ".png",
            ):
                import cv2

                # print(input_file)
                frame = cv2.imread(str(input_file))
                scale = height / frame.shape[0]
                frame = rescale(frame, scale)
                if make_square:
                    frame = crop_square(frame)
                cv2.imwrite(str(filename), frame)
            else:
                logger.warning(
                    f"Preview generation skipped. Unknown file type. filename={str(input_file.name)}"
                )
                return

            serverfile.preview.name = str(filename_rel)
            serverfile.save()


def email_report_from_task(task):

    logger.debug("getting parameters from task for email")
    serverfile: UploadedFile = task.args[0]
    # absolute uri is http://127.0.0.1:8000/. We have to remove last '/' because the url already contains it.
    absolute_uri = task.args[1][:-1]
    # logger.debug(dir(task))
    email_report(serverfile, absolute_uri)


def email_report(serverfile: UploadedFile, absolute_uri: str):
    logger.debug("Sending email report...")
    html_message = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
        '<html xmlns="http://www.w3.org/1999/xhtml">\n'
        "<head> \n"
        '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />'
        "<title>Order received</title>"
        '<meta name="viewport" content="width=device-width, initial-scale=1.0"/>'
        "</head>"
        f"<body>"
        f"<p>Finished.</p><p>Email: {serverfile.email}</p><p>Filename: {str(Path(serverfile.mediafile).name)}</p>"
        f"<p></p>"
        f'<p> <a href="{absolute_uri}/uploader/web_report/{serverfile.hash}">Check report here</a> .</p>\n'
        f"<p></p>"
        f"<p></p>"
        f'<p> <a href="{absolute_uri}/uploader/owners_reports/{serverfile.owner.hash}">See all your reports here</a> .</p>\n'
        f"<p></p>"
        f'<p> <a href="{absolute_uri}/uploader/go_to_video_for_annotation/{serverfile.email}">You can also do a review</a> .</p>\n'
        f"<p></p>"
        f"<p>Best regards</p>\n"
        f"<p>Miroslav Jirik</p>\n"
        f"<p></p>"
        "<p>Faculty of Applied Sciences</p\n"
        "<p>University of West Bohemia</p>\n"
        "<p>Pilsen, Czech Republic</p>\n"
        "<p>mjirik@kky.zcu.cz</p>\n"
        f"</body></html>"
    )

    # f'<p> <a href="{absolute_uri}{serverfile.zip_file.url}">Download report here</a> .</p>\n'

    # f'http://127.0.0.1:8000/{request.buld_absolute_uri(serverfile.zip_file.url)}' \
    # logger.debug(f"email_text={html_message}")
    subject = "Pig Leg Surgery Analyser: Report"
    from_email = "mjirik@kky.zcu.cz"
    # to_email = "mjirik@gapps.zcu.cz"
    to_email = serverfile.email

    # async_task('django.core.mail.send_mail',
    # message = EmailMessage(subject, html_message, from_email, [to_email])
    # message.content_subtype = 'html'  # this is required because there is no plain text email message
    # message.send()
    send_mail(
        subject,
        html_message,
        from_email,
        [to_email],
        fail_silently=False,
        html_message=html_message,
    )
    logger.debug("Email sent.")
    # send_mail(
    #     "[Pig Leg Surgery]",
    #     html_message,
    #     "mjirik@kky.zcu.cz",
    #     ["miroslav.jirik@gmail.com"],
    #     fail_silently=False,
    # )


def email_media_recived(serverfile: UploadedFile):
    # async_task('django.core.mail.send_mail',
    send_mail(
        "Pig Leg Surgery Analyser: Media file recived",
        "Thank you for uploading a file. \n"
        + "Now we are in an early stage of the project when we plan to collect the data."
        + " The outputs of the analysis will be introduced in few weeks. "
        + "We will let you know when the processing will be finished. \n\n"
        + "Best regards,\n"
        "Miroslav Jirik, Ph.D.\n\n"
        "Faculty of Applied Sciences\n"
        "University of West Bohemia\n"
        "Pilsen, Czech Republic",
        "mjirik@kky.zcu.cz",
        [serverfile.email],
        fail_silently=False,
    )


def run_processing2(serverfile: UploadedFile):
    log_format = loguru._defaults.LOGURU_FORMAT
    logger_id = logger.add(
        str(Path(serverfile.outputdir) / "log.txt"),
        format=log_format,
        level="DEBUG",
        rotation="1 week",
        backtrace=True,
        diagnose=True,
    )
    # delete_generated_images(
    #     serverfile
    # )  # remove images from database and the output directory
    # mainapp = scaffan.algorithm.Scaffan()
    # mainapp.set_input_file(serverfile.imagefile.path)
    # mainapp.set_output_dir(serverfile.outputdir)
    # fn, _, _ = models.get_common_spreadsheet_file(serverfile.owner)
    # mainapp.set_common_spreadsheet_file(str(fn).replace("\\", "/"))
    # settings.SECRET_KEY
    logger.debug("Scaffan processing run")
    # if len(centers_mm) > 0:
    #     mainapp.set_parameter("Input;Lobulus Selection Method", "Manual")
    # else:
    #     mainapp.set_parameter("Input;Lobulus Selection Method", "Auto")
    # mainapp.run_lobuluses(seeds_mm=centers_mm)
    # serverfile.score = _clamp(
    #     mainapp.report.df["SNI area prediction"].mean() * 0.5, 0.0, 1.0
    # )
    # serverfile.score_skeleton_length = mainapp.report.df["Skeleton length"].mean()
    # serverfile.score_branch_number = mainapp.report.df["Branch number"].mean()
    # serverfile.score_dead_ends_number = mainapp.report.df["Dead ends number"].mean()
    # serverfile.score_area = mainapp.report.df["Area"].mean()

    # add_generated_images(serverfile)  # add generated images to database
    #
    # serverfile.processed_in_version = scaffan.__version__
    # serverfile.process_started = False
    # serverfile.last_error_message = ""
    # if serverfile.zip_file and Path(serverfile.zip_file.path).exists():
    #     serverfile.zip_file.delete()
    #
    # views.make_zip(serverfile)
    # serverfile.save()
    # logger.remove(logger_id)


def get_zip_fn(serverfile: UploadedFile):
    logger.trace(f"serverfile.imagefile={serverfile.mediafile.name}")
    if not serverfile.mediafile.name:
        logger.debug(f"No file uploaded for {serverfile.mediafile}")
        return None
        # file is not uploaded

    nm = str(Path(serverfile.mediafile.path).name)
    # prepare output zip file path
    pth_zip = serverfile.outputdir + nm + ".zip"
    return pth_zip


def add_generated_images(serverfile: UploadedFile):
    # serverfile.bitmap_image_set.all().delete()
    od = Path(serverfile.outputdir)
    logger.debug(od)
    lst = sorted(glob.glob(str(od / "*.jpg")))
    lst.extend(sorted(glob.glob(str(od / "*.JPG"))))
    lst.extend(glob.glob(str(od / "*.png")))
    # lst.extend(glob.glob(str(od / "slice_label.png")))
    # lst.extend(sorted(glob.glob(str(od / "*.png"))))
    lst.extend(sorted(glob.glob(str(od / "*.PNG"))))
    # lst.extend(glob.glob(str(od / "sinusoidal_tissue_local_centers.png")))
    # lst.extend(sorted(glob.glob(str(od / "lobulus_[0-9]*.png"))))
    logger.debug(lst)
    # remove all older references and objects
    serverfile.bitmapimage_set.all().delete()

    for fn in lst:
        # skip the files with __ in the beginning of the name
        if Path(fn).name.startswith("__"):
            continue
        pth_rel = op.relpath(fn, settings.MEDIA_ROOT)
        bi = BitmapImage(server_datafile=serverfile, bitmap_image=pth_rel)
        bi.save()


def make_zip(serverfile: UploadedFile):
    pth_zip = get_zip_fn(serverfile)
    if pth_zip:
        import shutil

        # remove last letters.because of .zip is added by make_archive
        shutil.make_archive(pth_zip[:-4], "zip", serverfile.outputdir)

        serverfile.processed = True
        pth_rel = op.relpath(pth_zip, settings.MEDIA_ROOT)
        serverfile.zip_file = pth_rel
        serverfile.save()
