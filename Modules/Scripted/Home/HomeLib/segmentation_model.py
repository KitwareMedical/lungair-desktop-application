# This is currently configured to work with models produced in exploration6.ipynb
# in https://github.com/ebrahimebrahim/lung-seg-exploration
# This wrapper class will handle loading a model and running inference

import monai
import numpy as np
import os
import re
import torch
from .segmentation_post_processing import SegmentationPostProcessing


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

    # Transforms a given image to the input format expected by the segmentation network
    self.transform = monai.transforms.Compose([
      monai.transforms.CastToType(dtype=np.float32), # TODO dtype should have been included in the model_dict
      monai.transforms.AddChannel(),
      monai.transforms.Resize(
        spatial_size=(self.image_size,self.image_size),
        mode = 'bilinear',
        align_corners=False
      ),
      monai.transforms.ToTensor()
    ])

    self.seg_post_process = SegmentationPostProcessing()

    # set dropout and batch normalization layers to evaluation mode before running
    # inference
    tmp = self.seg_net.eval()

    # If we haven't already, write out a TorchScript version of the model, for use in
    # MONAI Deploy.  For save_path, remove trailing .pth if present; append .zip
    save_path = re.sub("\.pth$", "", load_path) + ".zip"
    self.write_torchscript(self.seg_net, save_path, overwrite=False)

  def write_torchscript(self, seg_net, save_path, overwrite):
    if overwrite or not os.path.exists(save_path):
      torch.jit.script(seg_net).save(save_path)

  def run_inference(self, img):
    """
    Execute segmentation model on a chest xray, given as an array of shape (height, width).

    The image axes are assumed to be in "matrix" order, with the origin in the upper left of the image:
    - The 0 axis should go along the height of the radiograph, towards patient-inferior
    - The 1 axis should go along the width of the radiograph, towards patient-left/image-right

    The segmentation model should include post-processing but this is SKIPPED for now; TODO.
    Currently it's just a segmentation network.

    Returns (seg_mask, model_to_img_matrix), where:
      seg_mask is a torch tensor of shape (height, width), a binary label mask indicating the lung field
      model_to_img_matrix is a 2D numpy array representing the linear transform from the coordinate space of the segmentation model
        output to the original coordinate space of the given array img.
    """
    if len(img.shape) != 2:
      raise ValueError("img must be a 2D array")

    self.seg_net.eval()
    img_input = self.transform(img)
    seg_net_output = self.seg_net(img_input.unsqueeze(0))[0]

    # assumption at the moment is that we have 2-channel image out (i.e. purely binary segmentation was done)
    assert(seg_net_output.shape[0]==2)

    _, max_indices = seg_net_output.max(dim=0)
    seg_mask = (max_indices==1).type(torch.uint8)

    model_to_img_matrix = np.diag(np.array(img.shape)/self.image_size)

    return seg_mask, model_to_img_matrix # TODO returning early because post processing causes crash due to ITK python issues

    seg_processed = self.seg_post_process(seg_mask)

    return seg_processed, model_to_img_matrix
