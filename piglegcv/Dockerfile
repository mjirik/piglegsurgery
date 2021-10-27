FROM nvidia/cuda:11.1.1-cudnn8-devel

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update && apt-get install -y \
	python3-opencv ca-certificates python3-dev git wget sudo ninja-build
RUN ln -sv /usr/bin/python3 /usr/bin/python

# create a non-root user
ARG USER_ID=1000
RUN useradd -m --no-log-init --system  --uid ${USER_ID} appuser -g sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

USER appuser
WORKDIR /home/appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"
RUN wget https://bootstrap.pypa.io/get-pip.py && \
	python3 get-pip.py --user && \
	rm get-pip.py

# install dependencies	
# See https://pytorch.org/ for other options if you use a different version of CUDA
RUN pip install --user tensorboard cmake   # cmake from apt-get is too old
RUN pip install --user torch==1.9 torchvision==0.10 -f https://download.pytorch.org/whl/cu111/torch_stable.html

RUN pip install --user 'git+https://github.com/facebookresearch/fvcore'
# install detectron2
RUN git clone https://github.com/facebookresearch/detectron2 detectron2_repo
# set FORCE_CUDA because during `docker build` cuda is not accessible
ENV FORCE_CUDA="1"
# This will by default build detectron2 for all common cuda architectures and take a lot more time,
# because inside `docker build`, there is no way to tell which architecture will be used.
ARG TORCH_CUDA_ARCH_LIST="Kepler;Kepler+Tesla;Maxwell;Maxwell+Tegra;Pascal;Volta;Turing"
ENV TORCH_CUDA_ARCH_LIST="${TORCH_CUDA_ARCH_LIST}"

RUN pip install --user -e detectron2_repo

# SORT
# RUN git clone https://github.com/abewley/sort.git extern
ADD ./extern ./extern
RUN pip install --user filterpy==1.4.5 scikit-image==0.17.2 lap==0.4.0
RUN pip install --user flask loguru rq

#COPY ./run_tracker_lite.sh .
# RUN chmod +x ./run_tracker_lite.sh
# ADD ./01_firstTry_faster_rcnn_R_50_FPN_3x ./model

# Set a fixed model cache directory.
ENV FVCORE_CACHE="/tmp"
# WORKDIR /home/appuser/data

#ENTRYPOINT ["/home/appuser/run_tracker_lite.sh"]
USER root
RUN apt-get install -y redis ffmpeg

USER appuser

RUN mkdir logs

COPY ./run_tracker_lite.py .
COPY ./worker.py .
COPY ./app.py .
COPY ./pigleg_cv.py .
COPY ./run_services.sh .

#CMD ["./data/images"]
CMD cd /home/appuser/ && \
    ./run_services.sh && \
    tail -f /dev/null

#    sudo service redis-server start && \
#    /webapps/piglegsurgery/docker/bin/qcluster_start  & && \
#    /webapps/piglegsurgery/docker/bin/gunicorn_start & && \

# run detectron2 under user "appuser":
# wget http://images.cocodataset.org/val2017/000000439715.jpg -O input.jpg
# python3 demo/demo.py  \
	#--config-file configs/COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml \
	#--input input.jpg --output outputs/ \
	#--opts MODEL.WEIGHTS detectron2://COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x/137849600/model_final_f10217.pkl