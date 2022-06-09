# Some basic setup

# import some common libraries
import logging

import cv2
import mmcv.utils
logger = mmcv.utils.get_logger(name=__file__, log_level=logging.DEBUG)

import matplotlib.pyplot as plt
import numpy as np
# Check Pytorch installation
import torch, torchvision
print(torch.__version__, torch.cuda.is_available())

# Check MMDetection installation
import mmdet
logger.debug(f'mmdet.version={mmdet.__version__}')

# Check mmcv installation
from mmcv.ops import get_compiling_cuda_version, get_compiler_version
logger.debug(get_compiling_cuda_version())
logger.debug(get_compiler_version())
from pprint import pprint, pformat
from mmcv import Config
from mmdet.apis import set_random_seed
from mmdet.datasets import build_dataset
from mmdet.apis import train_detector, init_detector, inference_detector, show_result_pyplot
import os.path as osp
from typing import Optional

from pathlib import Path
mmdetection_path = Path(mmdet.__file__).parent.parent

import mmcv
from mmcv.runner import load_checkpoint

from mmdet.models import build_detector

from pathlib import Path
import os
scratchdir = Path(os.getenv('SCRATCHDIR', "."))
logname = Path(os.getenv('LOGNAME', "."))
# from loguru import logger

local_input_data_dir = Path(scratchdir) / 'data/orig/'
local_output_data_dir = Path(scratchdir) / 'data/processed/'


def prepare_cfg(
        local_input_data_dir:Path,
        local_output_data_dir:Path,
        checkpoint_pth:Optional[Path]=None,
        work_dir:Optional[Path]=None,
        skip_data=False
):
    if checkpoint_pth == None:
        checkpoint_pth = scratchdir / 'checkpoints/faster_rcnn_r50_caffe_fpn_mstrain_3x_coco_20210526_095054-1f77628b.pth'
    checkpoint_pth = str(checkpoint_pth)

    work_dir = str(work_dir) if work_dir else str(local_output_data_dir / 'tutorial_exps')

    logger.debug(f"outputdir={local_output_data_dir}")
    logger.debug(f"input_data_dir={local_input_data_dir}")
    logger.debug(f"input_data_dir exists={local_input_data_dir.exists()}")
    logger.debug(f'input_data_dir glob={str(list(local_input_data_dir.glob("**/*")))}')



    # # Choose to use a config and initialize the detector
    # config = mmdetection_path / 'configs/faster_rcnn/faster_rcnn_r50_caffe_fpn_mstrain_3x_coco.py'
    # logger.debug(f"config.exists={config.exists()}")
    # # Setup a checkpoint file to load
    # checkpoint_pth = scratchdir / 'checkpoints/faster_rcnn_r50_caffe_fpn_mstrain_3x_coco_20210526_095054-1f77628b.pth'
    # logger.debug(f"checkpoint_pth.exists={checkpoint_pth.exists()}")
    #
    # # Set the device to be used for evaluation
    # device='cuda:0'
    #
    # # Load the config
    # config = mmcv.Config.fromfile(config)
    # # Set pretrained to be None since we do not need pretrained model here
    # config.model.pretrained = None
    #
    # # Initialize the detector
    # model = build_detector(config.model)
    #
    # # Load checkpoint
    # checkpoint = load_checkpoint(model, str(checkpoint_pth), map_location=device)
    #
    # # Set the classes of models for inference
    # model.CLASSES = checkpoint['meta']['CLASSES']
    #
    # # We need to set the model's cfg for inference
    # model.cfg = config
    #
    # # Convert the model to GPU
    # model.to(device)
    # # Convert the model into evaluation mode
    # model.eval()
    #
    # # Use the detector to do inference
    # img = mmdetection_path / 'demo/demo.jpg'
    # result = inference_detector(model, img)
    # model.show_result(img, result, out_file=local_output_data_dir / 'demo_output.jpg')# save image with result


    # My dataset training
    cfg = Config.fromfile(mmdetection_path / 'configs/faster_rcnn/faster_rcnn_r50_caffe_fpn_mstrain_1x_coco.py')

    cfg.dataset_type = 'CocoDataset'
    cfg.data_root = str(local_input_data_dir)
    cfg.classes = ('incision',)
    if not skip_data:
        # Modify dataset type and path

        cfg.data.test.type = 'CocoDataset'
        cfg.data.test.data_root = str(local_input_data_dir)
        cfg.data.test.ann_file = 'annotations/instances_default.json'
        cfg.data.test.img_prefix = 'images/'
        cfg.data.test.classes = cfg.classes

        cfg.data.train.type = 'CocoDataset'
        cfg.data.train.data_root = str(local_input_data_dir)
        cfg.data.train.ann_file = 'annotations/instances_default.json'
        cfg.data.train.img_prefix = 'images/'
        cfg.data.train.classes = cfg.classes

        cfg.data.val.type = 'CocoDataset'
        cfg.data.val.data_root = str(local_input_data_dir)
        cfg.data.val.ann_file = 'annotations/instances_default.json'
        cfg.data.val.img_prefix = 'images/'
        cfg.data.val.classes = cfg.classes

    # modify num classes of the model in box head
    cfg.model.roi_head.bbox_head.num_classes = 1
    # If we need to finetune a model based on a pre-trained detector, we need to
    # use load_from to set the path of checkpoints.
    cfg.load_from = checkpoint_pth

    # Set up working dir to save files and logs.
    cfg.work_dir = work_dir

    # The original learning rate (LR) is set for 8-GPU training.
    # We divide it by 8 since we only use one GPU.
    cfg.optimizer.lr = 0.02 / 8
    cfg.lr_config.warmup = None
    cfg.log_config.interval = 10

    # Change the evaluation metric since we use customized dataset.
    # cfg.evaluation.metric = 'mAP'
    # We can set the evaluation interval to reduce the evaluation times
    cfg.evaluation.interval = 12
    # We can set the checkpoint saving interval to reduce the storage cost
    cfg.checkpoint_config.interval = 12

    # Set seed thus the results are more reproducible
    cfg.seed = 0
    set_random_seed(0, deterministic=False)
    cfg.gpu_ids = range(1)

    # We can also use tensorboard to log the training process
    cfg.log_config.hooks = [
        dict(type='TextLoggerHook'),
        dict(type='TensorboardLoggerHook')]


    # We can initialize the logger for training and have a look
    # at the final config used for training
    # print(f'Config:\n{cfg.pretty_text}') # does not work for paths beginning '/' because of bug in lib2to3

    logger.debug(f"cfg=\n{pformat(cfg)}")


    return cfg


def train(cfg):
    # Build dataset
    datasets = [build_dataset(cfg.data.train)]

    logger.debug(f"classes={datasets[0].CLASSES}")


    # Build the detector
    model = build_detector(cfg.model)
    # Add an attribute for visualization convenience
    model.CLASSES = datasets[0].CLASSES


    # Create work_dir
    mmcv.mkdir_or_exist(osp.abspath(cfg.work_dir))

    train_detector(model, datasets, cfg, distributed=False, validate=True)
    return model

def run_incision_detection(img, local_output_data_dir:Path):
    # img = mmcv.imread(str(img_fn))
    checkpoint_path = Path(__file__).parent / "resources/incision_detection_models/220326_234659_mmdet.pth"
    logger.debug(f"checkpoint_path.exists={checkpoint_path.exists()}")
    logger.debug(f"img={img}")
    # logger.debug(f"img_fn={img_fn}")

    # img_fn = Path(img_fn)
    local_output_data_dir = Path(local_output_data_dir)

    # My dataset training
    cfg = Config.fromfile(mmdetection_path / 'configs/faster_rcnn/faster_rcnn_r50_caffe_fpn_mstrain_1x_coco.py')

    cfg.dataset_type = 'CocoDataset'
    # cfg.data_root = str(local_input_data_dir)
    cfg.classes = ('incision',)
    # modify num classes of the model in box head
    cfg.model.roi_head.bbox_head.num_classes = 1

    model = init_detector(cfg, str(checkpoint_path),
                          # device='cuda:0'
                          )
    # logger.debug(f"cfg=\n{pformat(cfg)}")
    result = inference_detector(model, img)
    model.show_result(img, result, out_file=local_output_data_dir / f'incision_full.jpg')  # save image with result

    # get cropped incision
    class_id = 0
    # obj_in_class_id = 0
    bboxes = result[class_id]
    logger.debug(f"number of detected incisions = {len(bboxes)}")
    imgs = []
    for i, bbox in enumerate(bboxes):

        imcr = img[int(bbox[1]):int(bbox[3]), int(bbox[0]):int(bbox[2])]

        cv2.imwrite(str(local_output_data_dir / f'incision_crop_{i}.jpg'), imcr)
        imgs.append(imcr)
        # plt.imshow(imcr[:, :, ::-1])
    # predict_image_with_cfg(cfg, model, img_fn, local_output_data_dir)
    return imgs

def predict_image_with_cfg(cfg, model, img_fn, local_output_data_dir):
    # img_fn = local_input_data_dir / '/images/10.jpg'
    img = mmcv.imread(img_fn)

    model.cfg = cfg
    result = inference_detector(model, img)
    # show_result_pyplot(model, img, result)
    model.show_result(img, result,
                      out_file=local_output_data_dir / f'output_{img_fn.stem}.jpg')  # save image with result
    return result


def predict_images(cfg, model, local_input_data_dir:Path, local_output_data_dir):

    filelist = []
    if local_input_data_dir.is_dir():
        filelist =  list(local_input_data_dir.glob("*.jpg"))
        filelist.extend(list(local_input_data_dir.glob("*.png")))
    else:
        filelist = [local_input_data_dir]

    results = []
    for img_fn in filelist:
        result = predict_image_with_cfg(cfg, model, img_fn, local_output_data_dir)
        results.append(result)

    # # print all files in input dir recursively to check everything
    logger.debug(str(list(Path(local_output_data_dir).glob("**/*"))))
    return results

if __name__ == "__main__":
    cfg = prepare_cfg(local_input_data_dir, local_output_data_dir)
    predict_images(local_input_data_dir/"images")





