from email.mime import image
import logging
import os
import numpy as np
import slicer
import vtk
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
        [1., 0., 0., 0.],
        [0., 0., -1., 0.],
        [0., 1., 0., 0.],
        [0., 0., 0., 1.]
    ])
    return create_linear_transform_node_from_matrix(axial_to_coronal_np_matrix, "axial slice to coronal slice")

def create_coronal_plane_transform_node_from_2x2(matrix, node_name):
    """Given a 2D linear transform as a 2x2 matrix, create a transform node that carries out the transform within each coronal slice
    The vtkMRMLTransformNode is added to the scene and returned."""

    # The [2,0] is a the "S,R" coordinates in "R,A,S". The np.ix_([2,0],[2,0]) allows us to select the S,R submatrix.
    affine_transform = np.identity(4)
    affine_transform[np.ix_([2, 0], [2, 0])] = matrix
    return create_linear_transform_node_from_matrix(affine_transform, node_name)

def load_dicom_dir(dicomDataDir, pluginName, validate_dict=None, validate_mode=None, quiet=True):
    """Load from a DICOM directory and return a list of the loaded nodes.

    Args:
      pluginName: the DICOMPlugin to use; to see the available DICOMPlugins look at slicer.modules.dicomPlugins.keys().
      validate_dict: if specified then this should be a dict mapping dicom tags to lists of allowed values
      validate_mode: only matters if validate_dict is specified; can be any of the following:
        "skip": skip items that don't pass validation
        "error": raise an exception if an item is encountered that does not pass validation
      quiet: whether to not dump information about the series IDs and files that were found
    """

    if validate_dict is not None and validate_mode is None:
        raise ValueError("Please specify a validate_mode.")
    if validate_mode is not None and validate_dict is None:
        raise ValueError("Please specify a validate_dict.")

    loadedNodes = []
    @vtk.calldata_type(vtk.VTK_OBJECT)
    def onNodeAdded(caller, event, calldata):
        node = calldata
        if not isinstance(node, slicer.vtkMRMLStorageNode) and not isinstance(node, slicer.vtkMRMLDisplayNode):
            loadedNodes.append(node)
    sceneObserverTag = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent, onNodeAdded)

    plugin = slicer.modules.dicomPlugins[pluginName]()
    from DICOMLib import DICOMUtils
    with DICOMUtils.TemporaryDICOMDatabase() as db:
        DICOMUtils.importDicom(dicomDataDir, db)
        patientUIDs = db.patients()
        for patientUID in patientUIDs:
            patientUIDstr = str(patientUID)
            studies = db.studiesForPatient(patientUIDstr)
            series = [db.seriesForStudy(study) for study in studies]
            seriesUIDs = [uid for uidList in series for uid in uidList]
            fileLists = []
            for seriesUID in seriesUIDs:
                series_file_list = db.filesForSeries(seriesUID)
                if validate_mode is None:
                    series_file_list_filtered = series_file_list
                elif validate_mode == "skip" or validate_mode == "error":
                    series_file_list_filtered = []
                    for file_path in series_file_list:
                        dicom_values = {dicom_tag: db.fileValue(file_path, dicom_tag) for dicom_tag, allowed_vals in validate_dict.items()}
                        validation_passed = all(dicom_values[dicom_tag] in validate_dict[dicom_tag] for dicom_tag in validate_dict.keys())
                        if validation_passed:
                            series_file_list_filtered.append(file_path)
                        else:
                            if validate_mode == "error":
                                raise Exception(
                                    f"DICOM file {file_path} has failed validation due to the following: " + ", ".join(
                                        f"{tag} is {dicom_values[tag]}" for tag in validate_dict.keys()
                                        if dicom_values[tag] not in validate_dict[tag]
                                    )
                                )
                            elif not quiet:
                                print(f"Skipping {file_path} because it failed validation.")
                else:
                    raise ValueError("Invalid validate_mode.")
                if len(series_file_list_filtered) > 0:
                    fileLists.append(series_file_list)
            loadables = plugin.examineForImport(fileLists)
            for loadable in loadables:
                plugin.load(loadable)

            if not quiet:
                print("Patient with UID", patientUIDstr)
                print("  Studies:", studies)
                print("  Series:", series)
                print("  fileLists:", fileLists)

    slicer.mrmlScene.RemoveObserver(sceneObserverTag)
    return loadedNodes

# The DICOM validation function that we will use for NICU chest x-rays
validate_nicu_cxr = {
    "0018,5101": ["AP", "PA"],  # view position
    "0008,0060": ["RG", "DX", "CR"],  # modality
    "0018,0015": ["CHEST"],  # body part examined
}

def load_xrays(path: str, seg_model, image_format=None):
    """
    Load xrays from a given path, returning a list of Xray objects.
    This handles the creation of the needed MRML nodes and their alignment to the coordinate system.

    Args:
        path: path to the xray image
        image_format: xray image format; "png" or "dicom". Default behavior is to decide based on path extension
        seg_model: an instance of the SegmentationModel to use
    """
    if image_format is None:
        if path[-4:] == ".png":
            image_format = "png"
        else:
            image_format = "dicom"

    name = os.path.basename(path)
    if image_format == "png":
        volume_node = slicer.util.loadVolume(path, {"singleFile": True, "name": "LungAIR CXR: " + name})
        return [Xray(name, volume_node, seg_model)]
    elif image_format == "dicom":
        loaded_nodes = load_dicom_dir(path, "DICOMScalarVolumePlugin", validate_dict=validate_nicu_cxr, validate_mode="skip")
        loaded_xrays = []
        for i, node in enumerate(loaded_nodes):
            if node.GetClassName() != "vtkMRMLScalarVolumeNode":
                logging.warning("Somehow load_dicom_dir added an unexpected node type; see node ID " + node.GetID())
            else:
                loaded_xrays.append(Xray(name + f"_{i}", node, seg_model))
        return loaded_xrays
    else:
        raise ValueError("Unrecognized image_format.")



class Xray:
    """
    Represents one patient xray, including image arrays and references to any associated MRML nodes.
    Handles creation of associated MRML nodes.
    """

    axial_to_coronal_transform_node = None

    def __init__(self, name: str, volume_node, seg_model):
        """
        Args:
          name: name to be used in names of other associated objects (e.g. segmentation node)
          seg_model: an instance of the SegmentationModel to use
          volume_node: a vtkMRMLVolumeNode containing the xray image data. It should be a 1-volume slice.
            The single slice is expected to be an axial slice, as often happens when 2D images are loaded as volume nodes.
            A transform will be used to rotate it so that it becomes a coronal slice.
        """
        self.name = name
        self.seg_model = seg_model
        self.volume_node = volume_node

        # Only one of these transform nodes is needed; it is shared among all Xray instances
        if self.__class__.axial_to_coronal_transform_node is None:
            self.__class__.axial_to_coronal_transform_node = create_axial_to_coronal_transform_node()

        self.volume_node.SetAndObserveTransformNodeID(self.__class__.axial_to_coronal_transform_node.GetID())

        # Harden so that we can rely on vtkMRMLVolumeNode::GetIJKToRASDirections to get orientation information
        self.volume_node.HardenTransform()

        self.seg_node = None
        self.model_to_ras_transform_node = None

    def has_seg(self) -> bool:
        """Whether there is an associated segmentation node"""
        return self.seg_node is not None

    def delete_nodes(self):
        """Delete this xray's associated nodes. This leaves the object in an invalid state and it should no longer be used."""
        slicer.mrmlScene.RemoveNode(self.volume_node)
        slicer.mrmlScene.RemoveNode(self.seg_node)  # Passing None to RemoveNode should do nothing
        slicer.mrmlScene.RemoveNode(self.model_to_ras_transform_node)
        self.seg_node = None
        self.volume_node = None
        self.model_to_ras_transform_node = None

    def add_segmentation(self, backend_to_use: str):
        """
        Run segmentation model for this xray if it hasn't already been done.
        Creates an associated slicer segmentation node.
        """
        if self.has_seg():
            return

        # If the seg_model is the wrong type, replace it
        if self.seg_model['model'].model_source != backend_to_use:
            from HomeLib.segmentation_model import SegmentationModel
            self.seg_model['model'] = SegmentationModel(self.seg_model['model_path'], backend_to_use)
        # Use the seg_model
        self.seg_mask_tensor, model_to_image_matrix = self.seg_model['model'].run_inference(self.get_numpy_array())

        self.seg_node = create_segmentation_node_from_numpy_array(
            self.seg_mask_tensor.numpy(),
            {1: "lung field"},  # TODO replace by left and right lung setup once you fix post processing, and update doc above
            "LungAIR Seg: " + self.name,
            self.volume_node
        )

        # Now there are a few spatial coordinate systems we need to worry about; we number them to make this easier to discuss:
        # 1)  segmentation model 2D coordinates-- the spatial ij coordinates of the segmentation model's input and output images.
        # 2)  segmentation model 3D coordinates: the ijk coordinates coming from embedding (1) into the coronal plane
        # 2') RAS directions version of (2): intermediate coordinate system obtained by starting with (2) and then
        #     sending unit vectors in the coordinate directions to (unit) RAS direction vectors.
        # 3)  original volume node ijk coordinates: the spatial ijk coordinates on the underlying vtkImageData of the volume node
        # 3') RAS directions version of (3): intermediate coordinate system obtained by starting with (3) and then
        #     sending unit vectors in the coordinate directions to (unit) RAS direction vectors.
        # 4)  RAS coordinate system, the system slicer is ultimately using

        # The seg_node in a sense "starts" its life the coordinate system (2').
        # This is because segments are represented as vtkOrientedImageData, with their orientation realizing the (2)->(2') transform.

        # Coordinate transformation (2') to (3'), for now. It will change below.
        self.model_to_ras_transform_node = create_coronal_plane_transform_node_from_2x2(model_to_image_matrix, "LungAIR model to image transform: " + self.name)

        # Coordinate transformation (3) to (4)
        ijkToRas = vtk.vtkMatrix4x4()
        self.volume_node.GetIJKToRASMatrix(ijkToRas)

        # Coordinate transformation (3') to (3)
        ijkToRasDirInverse = vtk.vtkMatrix4x4()
        self.volume_node.GetIJKToRASDirectionMatrix(ijkToRasDirInverse)  # (3) to (3')
        ijkToRasDirInverse.Invert()  # now (3') to (3)

        # Coordinate transformation (3') to (4)
        ijkToRasWithoutDir = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(ijkToRas, ijkToRasDirInverse, ijkToRasWithoutDir)

        # Change model_to_ras_transform_node to be a (2') to (4) transform
        self.model_to_ras_transform_node.ApplyTransformMatrix(ijkToRasWithoutDir)

        # This (2') to (4) transform is just what we need to get the seg_node into RAS coordinates
        self.seg_node.SetAndObserveTransformNodeID(self.model_to_ras_transform_node.GetID())

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
            logging.warning(f"The underlying vtkImageData of volume node {volume_node.GetName()} appears to have a nontrivial direction matrix. " +
                            "Slicer might not provide accurate RAS directions in this situation, " +
                            "so there may be issues with producing a correctly oriented 2D array.")

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
                raise RuntimeError(f"The underlying vtkImageData of volume node {volume_node.GetName()} has {num_scalar_components} scalar components. " +
                                   "We do not know how to interpret this; expected 1 or 3 components.")

            # Convert to grayscale
            array = array.mean(axis=3, dtype=dtype)

        elif len(array.shape) != 3:
            raise RuntimeError(f"Getting an array from volume node {volume_node.GetName()} resulted in the shape {list(array.shape)}, " +
                               "which has an unexpected number of axes. Expected 3 or 4 axes.")

        # Attempt to find which axes of the numpy array correspond to certain patient-coordinate-directions
        array_axis_left = None
        array_axis_inferior = None
        left_dir = np.array([-1., 0., 0.])
        inferior_dir = np.array([0., 0., -1.])

        epsilon = 0.00001  # Tolerance for floating point comparisons

        # Here array_axis is one of the axes of the numpy array and direction_vector is its direction in RAS coordinates
        for array_axis, direction_vector in enumerate((k_dir, j_dir, i_dir)):
            if ((direction_vector - left_dir) < epsilon).all():
                array_axis_left = array_axis
            elif ((direction_vector - inferior_dir) < epsilon).all():
                array_axis_inferior = array_axis
        if array_axis_left is None or array_axis_inferior is None:
            raise RuntimeError(f"Volume node {volume_node.GetName()} does not seem to be aligned along the expected axes; " +
                               "unable to provide a numpy array because we cannot determine the standard axis order.")

        # Verify that the left and inferior axes are distinct and that the dimension along the remaining third axis is 1
        assert(all(array_axis in range(3) for array_axis in (array_axis_left, array_axis_inferior)))
        assert(array_axis_left != array_axis_inferior)
        other_axes = [array_axis for array_axis in range(3) if array_axis not in (array_axis_left, array_axis_inferior)]
        assert(len(other_axes) == 1)
        array_axis_other = other_axes[0]

        if array.shape[array_axis_other] != 1:
            raise RuntimeError(f"Volume node {volume_node.GetName()} seems to have more than one slice in a direction besides RIGHT or SUPERIOR; " +
                               "unable to provide a 2D numpy array for this.")

        array_2D_oriented = np.transpose(array, axes=(array_axis_other, array_axis_inferior, array_axis_left))[0]
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


    def show_xray(self, xray: Xray):
        """Show the given Xray image in the xray display views"""
        self.xray_composite_node.SetBackgroundVolumeID(xray.volume_node.GetID())
        self.xray_features_composite_node.SetBackgroundVolumeID(xray.volume_node.GetID())
        slicer.util.resetSliceViews()  # reset views to show full image

    def set_xray_segmentation_visibility(self, xray: Xray, visibility: bool):
        """Show the segmentation of the given in the xray image in the xray features view"""
        if xray.has_seg():

            # The list of view node IDs on a display node is initially empty, which makes the node visible in all views.
            # Adding a view node ID as we do here makes it so that the node is only visible in the added view.
            # (this only needs to be done once for the segmentation node, not every time visibility is changed; but for now this is the best place to do it)
            xray.seg_node.GetDisplayNode().AddViewNodeID(self.xray_features_view_node.GetID())

            xray.seg_node.GetDisplayNode().SetVisibility(visibility)


def shItem_has_volume_node_descendant(item_id):
    """Return whether the item with the given subject hierarchy item ID has any volume nodes under its subtree"""
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    children = vtk.vtkIdList()
    shNode.GetItemChildren(item_id, children, True)  # last parameter is "recursive = False"
    for i in range(children.GetNumberOfIds()):
        node = shNode.GetItemDataNode(children.GetId(i))
        if node is not None and node.IsTypeOf("vtkMRMLVolumeNode"):
            return True
    return False

def prune_unused_subjects():
    """Delete any unused top-level subjects from the subject hierarchy.
    Here "unused" means subjects that contain no volume nodes under them."""
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    top_level_children = vtk.vtkIdList()
    shNode.GetItemChildren(shNode.GetSceneItemID(), top_level_children, False)  # last parameter is "recursive = False"
    for i in range(top_level_children.GetNumberOfIds()):
        top_level_child = top_level_children.GetId(i)
        if shNode.GetItemLevel(top_level_child) == "Patient" and not shItem_has_volume_node_descendant(top_level_child):
            shNode.RemoveItem(top_level_child)

class XrayCollection(dict):
    """A mapping from xray names to xray objects, with some useful xray-specific functionality."""
    def __init__(self):
        super().__init__()
        self.xray_display_manager = XrayDisplayManager()
        self.selected_name = None  # This can be None or it can be the key of the currently selected xray

    def clear(self):
        """Empty out the xray collection, cleaning up associated resources used in the scene."""
        self.selected_name = None
        for xray in self.values():
            xray.delete_nodes()

        # The last set of xrays that was loaded may have added subjects to the subject hierarchy that are no longer needed
        # This is not an elegant approach, because it deletes unused subjects indiscriminantly, without regard to whether they were
        # added in relation to this particular xray collection. IF we later use the subject-study system elsewhere in the LungAIR application,
        # then we would have to change this approach.
        prune_unused_subjects()

        super().clear()

    def extend(self, xrays):
        """Append the given list of xrays to this collection; raises exception if a duplicate xray name is encountered."""
        for xray in xrays:
            if xray.name in self.keys():
                raise Exception("Duplicate xray name has been encountered; names should be unique.")
            self.update({xray.name: xray})

    def selected_xray(self) -> Xray:
        return self[self.selected_name]

    def select(self, name: str):
        """Select the xray of the given name, carrying out visibility changes in the scene as needed."""
        if self.selected_name is not None:
            self.xray_display_manager.set_xray_segmentation_visibility(self.selected_xray(), False)
        self.selected_name = name
        self.xray_display_manager.set_xray_segmentation_visibility(self.selected_xray(), True)
        self.xray_display_manager.show_xray(self.selected_xray())

    def segment_selected(self, backend_to_use: str):
        """Add a segmentation for the selected xray and make it the visible segmentation."""
        self.selected_xray().add_segmentation(backend_to_use)

        # Make all segmentations invisible except the selected one
        for xray in self.values():
            self.xray_display_manager.set_xray_segmentation_visibility(xray, False)
        self.xray_display_manager.set_xray_segmentation_visibility(self.selected_xray(), True)
