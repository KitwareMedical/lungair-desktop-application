import sys
import itk
import numpy as np
import torch
from collections import OrderedDict
import matplotlib.pyplot as plt

class SegmentationPostProcessing():
  """
  Post-processing callable that remembers some intermediate steps.
  Given a binary lung segmentation (with labels 0=background and 1=lung) this will return a segmentation
  that picks out a left and a right lung (left=1, right=2), and that guarantees each lung to be a simply connected region
  (i.e. both connected and containing no holes).

  Note that "left" and "right" refer to the left and right sides of the _image_, not necessarily of the patient!
  To get patient left/right correctly, you would need to involve the PA/AP orientation information associated to the xray.
  """
  def __init__(self):
    self.intermediate_steps = OrderedDict()

  def log_intermediate_step(self, step_name, step_description, step_artifact):
    self.intermediate_steps[step_name] = {
      "description" : step_description,
      "artifact" : step_artifact,
    }

  def __call__(self, seg_tensor: torch.Tensor):
    """
    seg_tensor should be a pytorch tensor of shape (H,W), a binary image label map with; labels 0 and 1.
    Returns a processed version of seg_tensor, while logging some intermediate steps in case they need to be inspected.
    """

    # A dict mapping each step name to a corresponding step artifact
    # to log intermediate steps of computation
    self.intermediate_steps = OrderedDict()

    if (not len(seg_tensor.shape)==2):
      raise ValueError("Expected 2D image, i.e. tensor of shape (H,W).")

    # Convert tensor to ITK image
    seg_itk = itk.image_from_array(seg_tensor.numpy().astype(np.uint8))

    # Compute connected components from binary label map
    seg_connected = itk.ConnectedComponentImageFilter(seg_itk)

    # save copy to allow inspecting later
    self.log_intermediate_step(
      "connected_components", "Connected components of segmentation",
      itk.array_from_image(seg_connected)
    )

    # Construct a list of pairs (label, size) consisting of the label assigned to each connected
    # component followed by the size of that component. The label 0 is excluded because it
    # stands for background, and the itk connected components filter should preserve that label.
    label_size_pairs = [(l,(seg_connected==l).sum()) for l in np.unique(seg_connected) if l!=0]

    # sort by region size, descending
    label_size_pairs = sorted(label_size_pairs, key = lambda pair : pair[1], reverse=True)

    if len(label_size_pairs) < 2:
      raise Exception("Invalid segmentation mask; fewer than two components detected. (Expected left lung and right lung)")

    if (label_size_pairs[0][1]/label_size_pairs[1][1] > 2.):
      print("Something may be wrong: one lung segment (left or right) seems to be much larger than the other",file=sys.stderr)

    # the top two labels in terms of region size
    largest_two_labels = [pair[0].item() for pair in label_size_pairs[:2]]

    # Use ITK to compute shape attributes
    label_map = itk.LabelImageToShapeLabelMapFilter(seg_connected.astype(itk.UC))

    # Get the centroid of each of the largest two regions
    centroids = np.array([label_map.GetLabelObject(l).GetCentroid() for l in largest_two_labels])

    # This must be true because we raise exception when largest_two_labels is too short of a list,
    # and because the input image was a 2D image.
    # centroids[i,j] is the j^th coordinate of the i^th label
    assert(centroids.shape==(2,2))

    self.log_intermediate_step(
      "centroids", "Centroids of the two largest connected components of the segmentation",
      centroids
    )

    # Use centroid x coordinate to determine indices of largest_two_labels that correspond
    # to left and right lungs, and validate that the x coordinates are reasonable
    left_lung_index = centroids[:,0].argmin()
    right_lung_index = 0 if left_lung_index==1 else 1
    lung_indices = [left_lung_index, right_lung_index]
    x_total = seg_connected.shape[0]
    left_lung_x_proportion, right_lung_x_proportion = centroids[lung_indices,0] / x_total
    if not (left_lung_x_proportion > 0. and left_lung_x_proportion < 0.5 and
      right_lung_x_proportion > 0.5 and right_lung_x_proportion < 1.0):
      print("Something may be wrong: left and right lung segments ended up not reasonably positioned",file=sys.stderr)

    left_lung_label, right_lung_label = np.array(largest_two_labels)[lung_indices]

    # Construct lung mask with left and right labels
    lr_lung_seg = np.zeros_like(seg_itk)
    lr_lung_seg[seg_connected==left_lung_label] = 1
    lr_lung_seg[seg_connected==right_lung_label] = 2
    self.log_intermediate_step(
      "unfilled_lung_segmentation",
      "Lung segmentation after identifying left vs right lung, but before filling any holes",
      np.copy(lr_lung_seg)
    )

    # Fill holes in each label
    lr_lung_seg = itk.image_from_array(lr_lung_seg.astype(np.uint8))
    lr_lung_seg = itk.BinaryFillholeImageFilter(lr_lung_seg, ForegroundValue=1)
    lr_lung_seg = itk.BinaryFillholeImageFilter(lr_lung_seg, ForegroundValue=2)
    lr_lung_seg = itk.array_from_image(lr_lung_seg)
    self.log_intermediate_step(
      "filled_lung_segmentation",
      "Lung segmentation after identifying left vs right lung and filling any holes in them",
      np.copy(lr_lung_seg)
    )

    return lr_lung_seg

  def preview_intermediate_steps(self):

    def describe_and_plot(step_name): # prevents some code duplication
      print(self.intermediate_steps[step_name]['description'])
      plt.imshow(self.intermediate_steps[step_name]['artifact'])
      plt.show()

    describe_and_plot('connected_components')

    print(self.intermediate_steps['centroids']['description'])
    plt.imshow(self.intermediate_steps['connected_components']['artifact'])
    centroids = self.intermediate_steps['centroids']['artifact']
    plt.scatter(x = centroids[:,0], y = centroids[:,1])
    plt.show()

    describe_and_plot('unfilled_lung_segmentation')

    describe_and_plot('filled_lung_segmentation')