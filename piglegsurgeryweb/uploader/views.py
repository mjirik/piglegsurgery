from django.shortcuts import render, get_object_or_404, redirect
from django.views import generic
from django.contrib.auth.decorators import login_required
from pathlib import Path

from loguru import logger
# Create your views here.

from django.http import HttpResponse
from .models import UploadedFile, _hash
from .forms import UploadedFileForm
from .models_tools import randomString
from .tasks import email_media_recived
# from .models_tools import get_hash_from_output_dir, get_outputdir_from_hash

def index(request):
    return HttpResponse("Hello, world. You're at the polls index. HAHA")


def thanks(request):
    context = {
        'headline': "Thank You",
        'text': "Thank you for uploading media file. We will let you know when the processing will be finished."
    }
    return render(request, "uploader/thanks.html", context)

def reset_hashes(request):
    files = UploadedFile.objects.all()
    for file in files:
        file.hash = _hash()
        file.save()
    return redirect("/uploader/thanks/")

def resend_report_email(request, filename_id):
    serverfile = get_object_or_404(UploadedFile, pk=filename_id)
    from django_q.tasks import async_task
    async_task(
        "uploader.tasks.email_report",
        serverfile,
        request.build_absolute_uri("/"),
    )
    return redirect("/uploader/thanks/")


# @login_required(login_url='/admin/')
def show_report_list(request):
    files = UploadedFile.objects.all().order_by('-uploaded_at')
    context = {
        "uploadedfiles": files
    }
    return render(request, "uploader/report_list.html", context)



def web_report(request, filename_hash:str):
    # fn = get_outputdir_from_hash(hash)
    serverfile = get_object_or_404(UploadedFile, hash=filename_hash)
    fn = Path(serverfile.zip_file.path)
    logger.debug(fn)
    logger.debug(fn.exists())
    if not fn.exists():
        return render(request, 'uploader/thanks.html', {"headline": "File not exists", "text": "Requested file is probably under processing now."})
    logger.debug(serverfile.zip_file.url)
    image_list = serverfile.bitmapimage_set.all()
    context = {
        'serverfile': serverfile,
        'mediafile': Path(serverfile.mediafile.name).name,
        'image_list': image_list
    }
    return render(request,'uploader/web_report.html', context)

def run(request, filename_id):
    serverfile = get_object_or_404(UploadedFile, pk=filename_id)

    from django_q.tasks import async_task
    async_task(
        "uploader.tasks.run_processing",
        serverfile,
        request.build_absolute_uri("/"),
        hook="uploader.tasks.email_report",
    )
    context = {
        'headline': "Processing started",
        'text': f"Processing file {serverfile.mediafile}. The output will be stored in {serverfile.outputdir}."
    }
    return render(request, "uploader/thanks.html", context)
    # return redirect("/uploader/upload/")

class DetailView(generic.DetailView):
    model = UploadedFile
    template_name = "uploader/model_form_upload.html"


def model_form_upload(request):
    if request.method == "POST":
        form = UploadedFileForm(
            request.POST,
            request.FILES,
            # owner=request.user
        )
        if form.is_valid():
            from django_q.tasks import async_task

            # logger.debug(f"imagefile.name={dir(form)}")
            # name = form.cleaned_data['imagefile']
            # if name is None or name == '':
            #     return render(request, 'uploader/model_form_upload.html', {
            #         'form': form,
            #         "headline": "Upload",
            #         "button": "Upload",
            #         "error_text": "Image File is mandatory"
            #     })

            serverfile = form.save()
            async_task("uploader.tasks.email_media_recived", serverfile)

            # email_media_recived(serverfile)
            # print(f"user id={request.user.id}")
            # serverfile.owner = request.user
            # serverfile.save()
            async_task(
                "uploader.tasks.run_processing",
                serverfile,
                request.build_absolute_uri("/"),
                hook="uploader.tasks.email_report",
            )
            return redirect("/uploader/thanks/")
    else:
        form = UploadedFileForm()
    return render(
        request,
        "uploader/model_form_upload.html",
        {"form": form, "headline": "Upload", "button": "Upload"},
    )
