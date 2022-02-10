# This is currently configured to work with models produced in exploration6.ipynb
# in https://github.com/ebrahimebrahim/lung-seg-exploration
# This wrapper class will handle loading a model and running inference

import monai
import numpy as np
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

  def run_inference(self, img):
    """
    Execute segmentation model on a chest xray, given as an array of shape (height, width).

    The image axes are assumed to be in "matrix" order, with the origin in the upper left of the image:
    - The 0 axis should go along the height of the radiograph, towards patient-inferior
    - The 1 axis should go along the width of the radiograph, towards patient-left/image-right

    The segmentation model includes the network and the post-processing. (But post-processing is SKIPPED for now; TODO.)
    Returns segmentation, of shape (num_segments, height, width).
    """
    self.seg_net.eval()
    img_input = self.transform(img)
    seg_pred = self.seg_net(img_input.unsqueeze(0))[0]

    # assumption at the moment is that we have 2-channel image out (i.e. purely binary segmentation was done)
    assert(seg_pred.shape[0]==2)

    _, max_indices = seg_pred.max(dim=0)
    seg_pred_mask = (max_indices==1).type(torch.uint8)
    return seg_pred_mask # TODO returning early because post processing causes crash due to ITK python issues

    seg_pred_processed = self.seg_post_process(seg_pred_mask)

    return seg_pred_processed
