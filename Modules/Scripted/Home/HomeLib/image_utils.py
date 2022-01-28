import numpy as np
import vtk, slicer
from vtk.util.numpy_support import get_vtk_array_type, get_numpy_array_type


# trial and error to get this right :)
IJK_TO_RAS_DIRECTIONS = [[1,0,0], [0,-1,0], [0,0,-1]]



def create_image_data_from_numpy_array(array, oriented : bool, copy = True):
  """Create a vtk image data object from a numpy array.

  Args:
    array: a contiguous 2D numpy array of scalars to turn into a single-sliced 3D vtkImageData
    oriented (bool): whether to return a vtkOrientedImageData instead of a vtkImageData
    copy (bool): whether to copy the underlying data.
      Keep this on unless you are sure the numpy array is going to remain a valid resource.

  Returns: vtkImageData or vtkOrientedImageData
  """

  # See the following for hints on how this works:
  # https://github.com/Kitware/VTK/blob/master/Wrapping/Python/vtkmodules/util/numpy_support.py

  # Get type, e.g. vtk.VTK_FLOAT
  vtk_type = get_vtk_array_type(array.dtype)

  # Ensure array was contiguous
  assert(array.flags.c_contiguous)

  # Create a vtkDataArray of the correct size
  vtk_array = vtk.vtkDataArray.CreateDataArray(vtk_type)
  vtk_array.SetNumberOfComponents(1)
  vtk_array.SetNumberOfTuples(array.size)

  # I'm not certain that th following assert is needed, but if it ever fails then look here for hints:
  # https://github.com/Kitware/VTK/blob/0d344f312f143e7266ae10266f01470fb941ec96/Wrapping/Python/vtkmodules/util/numpy_support.py#L168
  # arr_dtype = vtk.util.numpy_support.get_numpy_array_type(vtk_type) # TODO Why no vtk.util?
  arr_dtype = get_numpy_array_type(vtk_type)
  assert(np.issubdtype(array.dtype, arr_dtype) or array.dtype == np.dtype(arr_dtype))

  # Set underlying data pointer of the vtkDataArray to point to the underlying data of the numpy array
  array_flat = np.ravel(array)
  vtk_array.SetVoidArray(array_flat, len(array_flat), 1)

  # Deep copy the vtkDataArray so that it doesn't rely on the numpy resource to stay alive
  if copy:
    copy = vtk_array.NewInstance()
    copy.DeepCopy(vtk_array)
    vtk_array = copy

  # Create a vtkImageData and set our vtkDataArray to be its point data scalars
  if oriented:
    imageData = slicer.vtkOrientedImageData()
  else:
    imageData = vtk.vtkImageData()
  imageData.SetDimensions([1] + list(array.shape))
  imageData.GetPointData().SetScalars(vtk_array)

  return imageData


def create_volume_node_from_numpy_array(array, node_name : str):
  """Create a volume node and add it to the scene.

  Args:
    array: a contiguous 2D numpy array of scalars to turn into a single-slice volume node
    node_name: string

  Returns: the added vtkMRMLScalarVolumeNode
  """

  imageData = create_image_data_from_numpy_array(array, oriented = False)

  # Create and add a volume node to the scene, setting our vtkImageData to be its underlying image data
  volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", node_name)
  volumeNode.SetOrigin([0.,0.,0.])
  volumeNode.SetSpacing([1.,1.,1.])
  volumeNode.SetIJKToRASDirections(IJK_TO_RAS_DIRECTIONS)
  volumeNode.SetAndObserveImageData(imageData)
  volumeNode.CreateDefaultDisplayNodes()
  volumeNode.CreateDefaultStorageNode() # TODO including this causes memory leak, reported on exit. why?

  return volumeNode


def create_segmentation_node_from_numpy_array(array, class_names : dict, node_name : str, vol_node):
  """Create a segmentation node and add it to the scene.
  Args:
    array: a contiguous 2D numpy array consisting of discrete class labels
    class_names (dict): a mapping from class labels (values in array) to name strings
      name strings will be assigned to each segment
    node_name (string): name of the segmentation node that will be created
    vol_node: volume node that this segmentation should be associated to

  Returns: the added vtkMRMLSegmentationNode
  """
  segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", node_name)
  segNode.SetReferenceImageGeometryParameterFromVolumeNode(vol_node)
  segNode.CreateDefaultDisplayNodes()
  for class_label in class_names.keys():
    binary_labelmap_array = (array==class_label).astype('int8')
    orientedImageData = create_image_data_from_numpy_array(binary_labelmap_array, oriented = True)
    orientedImageData.SetDirections(IJK_TO_RAS_DIRECTIONS)
    segNode.AddSegmentFromBinaryLabelmapRepresentation(orientedImageData, class_names[class_label])
  return segNode
