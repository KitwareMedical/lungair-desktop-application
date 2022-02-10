import logging
import os
import numpy as np
import slicer
from .image_utils import create_segmentation_node_from_numpy_array

def create_linear_transform_node_from_matrix(matrix, node_name):
  """Given a 3D affine transform as a 4x4 matrix, create a vtkMRMLTransformNode in the scene return it."""
  vtk_matrix = slicer.util.vtkMatrixFromArray(matrix)
  transform_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
  transform_node.SetName(node_name)
  transform_node.SetAndObserveMatrixTransformToParent(vtk_matrix)
  return transform_node

def create_axial_to_coronal_transform_node():
  axial_to_coronal_np_matrix = np.array([
    [1., 0.,  0., 0.],
    [0., 0., -1., 0.],
    [0., 1.,  0., 0.],
    [0., 0.,  0., 1.]
  ])
  return create_linear_transform_node_from_matrix(axial_to_coronal_np_matrix, "axial slice to coronal slice")

def create_coronal_plane_transform_node_from_2x2(matrix, node_name):
  """Given a 2D linear transform as a 2x2 matrix, create a transform node that carries out the transform within each coronal slice
  The vtkMRMLTransformNode is added to the scene and returned."""

  # The [2,0] is a the "S,R" coordinates in "R,A,S". The np.ix_([2,0],[2,0]) allows us to select the S,R submatrix.
  affine_transform = np.identity(4)
  affine_transform[np.ix_([2,0],[2,0])] = matrix
  return create_linear_transform_node_from_matrix(affine_transform, node_name)


class Xray:
  """
  Represents one patient xray, including image arrays and references to any associated MRML nodes.
  Handles creation of associated MRML nodes.
  """

  axial_to_coronal_transform_node = None

  def __init__(self, path:str, seg_model):
    """
    Args:
      path: path to the xray file
      seg_model: an instance of the SegmentationModel to use
    """
    self.name = os.path.basename(path)
    self.path = path
    self.seg_model = seg_model

    self.volume_node = slicer.util.loadVolume(path, {"singleFile":True, "name":"LungAIR CXR: "+self.name})

    # Only one of these transform nodes is needed; it is shared among all Xray instances
    if self.__class__.axial_to_coronal_transform_node is None:
      self.__class__.axial_to_coronal_transform_node = create_axial_to_coronal_transform_node()

    self.volume_node.SetAndObserveTransformNodeID(self.__class__.axial_to_coronal_transform_node.GetID())

    # Harden so that we can rely on vtkMRMLVolumeNode::GetIJKToRASDirections to get orientation information
    self.volume_node.HardenTransform()

    self.seg_node = None

  def has_seg(self) -> bool:
    """Whether there is an associated segmentation node"""
    return self.seg_node is not None

  def add_segmentation(self):
    """
    Run segmentation model for this xray if it hasn't already been done.
    Creates an associated slicer segmentation node.
    """
    if self.has_seg():
      return

    self.seg_mask_tensor, model_to_image_matrix = self.seg_model.run_inference(self.get_numpy_array())

    self.seg_node = create_segmentation_node_from_numpy_array(
      self.seg_mask_tensor.numpy(),
      {1:"lung field"}, # TODO replace by left and right lung setup once you fix post processing, and update doc above
      "LungAIR Seg: "+self.name,
      self.volume_node
    )

    self.model_to_image_transform_node = create_coronal_plane_transform_node_from_2x2(model_to_image_matrix, "LungAIR model to image transform: "+self.name)
    self.seg_node.SetAndObserveTransformNodeID(self.model_to_image_transform_node.GetID())

  def get_numpy_array(self, dtype=np.float32):
    """
    Get a 2D numpy array representation of the xray image.
    The dimensions follow the standard image-style (rows,columns) format:
    - the 0 dimension points towards the bottom of the image, towards patient inferior
    - the 1 dimension points towards the right of the image, towards the patient left
    """

    volume_node = self.volume_node

    # Verify that there is no unhardened transform, so we can trust vtkMRMLVolumeNode::GetIJKToRASDirections
    if volume_node.GetParentTransformNode() is not None:
      raise RuntimeError(f"Volume node {volume_node.GetName()} has an associated transform. Harden the transform before trying to get a numpy array.")

    # Verify that the underlying vtk image data has directions matrix equal to the identity.
    # (I'm pretty sure the vtkMRMLVolumeNode::Get<*>ToRASDirection functions don't care about the vtkImageData directions matrix)
    if not volume_node.GetImageData().GetDirectionMatrix().IsIdentity():
      logging.warning(f"The underlying vtkImageData of volume node {volume_node.GetName()} appears to have a nontrivial direction matrix. "+
        "Slicer might not provide accurate RAS directions in this situation, so there may be issues with producing a correctly oriented 2D array.")

    # The vtkMRMLVolumeNode::Get<*>ToRASDirection functions take an output parameter
    k_dir = np.zeros(3)
    j_dir = np.zeros(3)
    i_dir = np.zeros(3)
    volume_node.GetKToRASDirection(k_dir)
    volume_node.GetJToRASDirection(j_dir)
    volume_node.GetIToRASDirection(i_dir)

    # The 0,1,2 axes of this numpy array correspond to slicer K,J,I directions respectively.
    # (See https://discourse.slicer.org/t/why-are-dimensions-transposed-in-arrayfromvolume/21873)
    array = slicer.util.arrayFromVolume(volume_node)
    assert(len(array.shape) >= 3)

    # There could also be an additional axis for image color channels; we deal with that possibility here
    if len(array.shape) == 4:
      num_scalar_components = volume_node.GetImageData().GetNumberOfScalarComponents()

      # If the array has an extra axis then I assume it is due to multiple components in the scalar array of the underlying vtkImageData
      assert(num_scalar_components > 1)
      assert(num_scalar_components == array.shape[3])

      # If the number of components is 3 then it's probably just color channels-- but if not then further investigation is definitely needed.
      if num_scalar_components != 3:
        raise RuntimeError(f"The underlying vtkImageData of volume node {volume_node.GetName()} has {num_scalar_components} scalar components. "+
          "We do not know how to interpret this; expected 1 or 3 components.")

      # Convert to grayscale
      array = array.mean(axis=3, dtype=dtype)

    elif len(array.shape) != 3:
      raise RuntimeError(f"Getting an array from volume node {volume_node.GetName()} resulted in the shape {list(array.shape)}, "+
        "which has an unexpected number of axes. Expected 3 or 4 axes.")

    # Attempt to find which axes of the numpy array correspond to certain patient-coordinate-directions
    array_axis_left = None
    array_axis_inferior = None
    left_dir = np.array([-1.,0.,0.])
    inferior_dir = np.array([0.,0.,-1.])

    epsilon = 0.00001 # Tolerance for floating point comparisons

    # Here array_axis is an one of the axes of the numpy array and direction_vector is its direction in RAS coordinates
    for array_axis, direction_vector in enumerate((k_dir, j_dir, i_dir)):
      if ((direction_vector-left_dir)<epsilon).all():
        array_axis_left = array_axis
      elif ((direction_vector-inferior_dir)<epsilon).all():
        array_axis_inferior = array_axis
    if array_axis_left is None or array_axis_inferior is None:
      raise RuntimeError(f"Volume node {volume_node.GetName()} does not seem to be aligned along the expected axes; "+
        "unable to provide a numpy array because we cannot determine the standard axis order.")

    # Verify that there left and inferior axes are distinct and that the dimension along the remaining third axis is 1
    assert(all(array_axis in range(3) for array_axis in (array_axis_left, array_axis_inferior)))
    assert(array_axis_left != array_axis_inferior)
    other_axes = [array_axis for array_axis in range(3) if array_axis not in (array_axis_left, array_axis_inferior)]
    assert(len(other_axes)==1)
    array_axis_other = other_axes[0]

    if array.shape[array_axis_other]!=1:
      raise RuntimeError(f"Volume node {volume_node.GetName()} seems to have more than one slice in a direction besides RIGHT or SUPERIOR; "+
        "unable to provide a 2D numpy array for this.")

    array_2D_oriented = np.transpose(array, axes = (array_axis_other, array_axis_inferior, array_axis_left))[0]
    return array_2D_oriented.astype(dtype)





class XrayDisplayManager:
  """Handles showing and hiding various aspects of Xray objects, and manages the xray view nodes."""
  def __init__(self):
    layoutManager = slicer.app.layoutManager()

    # Get qMRMLSliceWidgets; the layout names are specified in the layout xml text
    self.xray_slice_widget = layoutManager.sliceWidget('xray')
    self.xray_features_slice_widget = layoutManager.sliceWidget('xrayFeatures')

    # Get qMRMLSliceViews
    self.xray_slice_view = self.xray_slice_widget.sliceView()
    self.xray_features_slice_view = self.xray_features_slice_widget.sliceView()

    # Get vtkMRMLSliceCompositeNodes. These are resposnible for putting together background,foreground,
    # and label layers to create the final slice view image.
    self.xray_composite_node = self.xray_slice_widget.mrmlSliceCompositeNode()
    self.xray_features_composite_node = self.xray_features_slice_widget.mrmlSliceCompositeNode()

    # Get vtkMRMLSliceNodes. These are often called "view nodes" in the Slicer documentation, so we use that name here.
    # (Not to be confused with vtkMRMLViewNodes, which are for 3D view rather than slice view.)
    self.xray_view_node = self.xray_slice_view.mrmlSliceNode()
    self.xray_features_view_node = self.xray_features_slice_view.mrmlSliceNode()


  def show_xray(self, xray:Xray):
    """Show the given Xray image in the xray display views"""
    self.xray_composite_node.SetBackgroundVolumeID(xray.volume_node.GetID())
    self.xray_features_composite_node.SetBackgroundVolumeID(xray.volume_node.GetID())
    slicer.util.resetSliceViews() # reset views to show full image

  def set_xray_segmentation_visibility(self, xray:Xray, visibility:bool):
    """Show the segmentation of the given in the xray image in the xray features view"""
    if xray.has_seg():

      # The list of view node IDs on a display node is initially empty, which makes the node visible in all views.
      # Adding a view node ID as we do here makes it so that the node is only visible in the added view.
      # (this only needs to be done once for the segmentation node, not every time visibility is changed; but for now this is the best place to do it)
      xray.seg_node.GetDisplayNode().AddViewNodeID(self.xray_features_view_node.GetID())

      xray.seg_node.GetDisplayNode().SetVisibility(visibility)