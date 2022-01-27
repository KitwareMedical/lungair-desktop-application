# This is currently configured to work with models produced in exploration6.ipynb
# in https://github.com/ebrahimebrahim/lung-seg-exploration
# This wrapper class will handle loading a model and running inference

import monai
from typing import Mapping, Hashable, List
import numpy as np
import torch
from .segmentation_post_processing import SegmentationPostProcessing

monai.utils.misc.set_determinism(seed=9274)

# ----- objects needed to define transform_valid (TODO: move to common lib, dealing with pickling issues somehow) -------

def rgb_to_grayscale(x):
    """Given a numpy array with shape (H,W,C), return "grayscale" one of shape (H,W);
    behaves as no-op if given array with shape already being (H,W)"""
    if len(x.shape)==2: return x
    elif len(x.shape)==3: return x.mean(axis=2)
    else: raise Exception("rgb_to_grayscale: unexpected number of axes in array")

# -----------------------------------------------------------------------------------------------------------------------

class SegmentationModel:
  def __init__(self, load_path):
    """
    This class provides a way to interface with a lung segmentation model trained in MONAI.
    It loads the model on construction, and it handles loading and transforming
    images and running inference.
    """

    model_dict = torch.load(load_path, map_location=torch.device('cpu'))

    self.seg_net = model_dict['model']
    self.learning_rate = model_dict['learning_rate']
    self.training_losses = model_dict['training_losses']
    self.validation_losses = model_dict['validation_losses']
    self.epoch_number = model_dict['epoch_number']
    self.best_validation_loss = model_dict['best_validation_loss']
    self.best_validation_epoch = model_dict['best_validation_epoch']
    self.image_size = model_dict['image_size']

    # TODO: Currently we hardcode the transform because unpickling needs to be done in the same environment pickling is done in.
    # Find a better solution so that you can ensure the environment doesn't change and you can load the same transform.
    self.transform_valid = monai.transforms.Compose([
      monai.transforms.LoadImageD(keys = ['img']), # A few shenzhen images get mysteriously value-inverted with readers other than itkreader
      monai.transforms.LambdaD(keys=['img'], func = rgb_to_grayscale), # A few of the shenzhen imgs are randomly RGB encoded rather than grayscale colormap
      monai.transforms.TransposeD(keys = ['img', 'mo_seg_left', 'mo_seg_right', 'sh_seg'], indices = (1,0), allow_missing_keys=True),
      monai.transforms.AddChannelD(keys = ['img']),
      monai.transforms.ResizeD(
          keys = ['img', 'seg'],
          spatial_size=(self.image_size,self.image_size),
          mode = ['bilinear', 'nearest'],
          allow_missing_keys=True,
          align_corners=[False, None]
      ),
      monai.transforms.ToTensorD(keys = ['img', 'seg'], allow_missing_keys=True),
    ])

    self.seg_post_process = SegmentationPostProcessing()

  def load_img(self, filepath):
    """Run the transform that comes with the model, using it to load an image from file. Probably returns tensor with channel dimension."""
    img = self.transform_valid({'img':filepath})['img']
    return img

  def run_inference(self, img):
    """
    Execute segmentation model on an image, given as a tensor of shape (channels, height, width).
    The segmentation model includes the network and the post-processing.
    Returns segmentation, of shape (num_segments, height, width).
    """
    self.seg_net.eval()
    seg_pred = self.seg_net(img.unsqueeze(0))[0]

    # assumption at the moment is that we 2-channel image out (i.e. purely binary segmentation was done)
    assert(seg_pred.shape[0]==2)
    _, max_indices = seg_pred.max(dim=0)
    seg_pred_mask = (max_indices==1).type(torch.uint8)
    return seg_pred_mask # TODO returning early because post processing causes crash. why crash?

    seg_pred_processed = self.seg_post_process(seg_pred_mask)

    return seg_pred_processed