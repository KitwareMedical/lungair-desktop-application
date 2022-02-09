import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from HomeLib import dependency_installer
from HomeLib.image_utils import *

class Home(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Home"
    self.parent.categories = [""]
    self.parent.dependencies = []
    self.parent.contributors = ["Ebrahim Ebrahim (Kitware Inc.), Andinet Enquobahrie (Kitware Inc.)"]
    self.parent.helpText = """This is the Home module for LungAIR"""
    self.parent.helpText += self.getModuleDocumentationLink()
    self.parent.acknowledgementText = """(TODO: put NIH grant number here)""" # replace with organization, grant and thanks.

  def getModuleDocumentationLink(self):
    url = "https://github.com/KitwareMedical/lungair-desktop-application" # Just link to repo for now
    return f'<p>For more information see the <a href="{url}">code repository</a>.</p>'


class HomeWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)


  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # (Previously we were loading widget from .ui file; keep this commented out here temporarily)
    # self.uiWidget = slicer.util.loadUI(self.resourcePath('UI/Home.ui'))
    # self.layout.addWidget(self.uiWidget)
    # self.ui = slicer.util.childWidgetVariables(self.uiWidget)

    vboxLayout = self.layout

    patientBrowserCollapsible = ctk.ctkCollapsibleButton()
    patientBrowserCollapsible.text = "Patient Browser"
    vboxLayout.addWidget(patientBrowserCollapsible)
    patientBrowserLayout = qt.QVBoxLayout(patientBrowserCollapsible)

    explanation =  "In lieu of an EHR-linked patient browser,\n"
    explanation += "we include for now a directory selector.\n"
    explanation += "Images and DICOM files in in the directory\n"
    explanation += "are considered to be chest xrays, while csv\n"
    explanation += "files are considered to contain clinical data."
    patientBrowserLayout.addWidget(qt.QLabel(explanation))
    directoryPathLineEdit = ctk.ctkPathLineEdit()
    directoryPathLineEdit.filters = ctk.ctkPathLineEdit.Dirs
    directoryPathLineEdit.currentPath = "/home/ebrahim/Desktop/test_patient2" # temporary measure to speed up testing
    patientBrowserLayout.addWidget(directoryPathLineEdit)

    loadPatientButton = qt.QPushButton("Load Patient")
    patientBrowserLayout.addWidget(loadPatientButton)
    loadPatientButton.clicked.connect(self.onLoadPatientClicked)

    dataBrowserCollapsible = ctk.ctkCollapsibleButton()
    dataBrowserCollapsible.text = "Data Browser"
    vboxLayout.addWidget(dataBrowserCollapsible)
    dataBrowserLayout = qt.QVBoxLayout(dataBrowserCollapsible)

    dataBrowserLayout.addWidget(qt.QLabel("X-rays (by image)"))
    xrayListWidget = qt.QListWidget()
    xrayListWidget.itemDoubleClicked.connect(self.onXrayListWidgetDoubleClicked)
    dataBrowserLayout.addWidget(xrayListWidget)

    dataBrowserLayout.addWidget(qt.QLabel("Clinical Parameters (by day)"))
    clinicalParametersListWidget = qt.QListWidget()
    clinicalParametersListWidget.itemDoubleClicked.connect(self.onClinicalParametersListWidgetDoubleClicked)
    dataBrowserLayout.addWidget(clinicalParametersListWidget)

    advancedCollapsible = ctk.ctkCollapsibleButton()
    advancedCollapsible.text = "Advanced"
    vboxLayout.addWidget(advancedCollapsible)
    advancedLayout = qt.QFormLayout(advancedCollapsible)
    advancedCollapsible.collapsed = True

    featureComboBox = qt.QComboBox()
    featureComboBox.currentTextChanged.connect(self.onFeatureComboBoxTextChanged)
    advancedLayout.addRow("Feature extraction\nstep to display", featureComboBox)
    monaiInstallButton = qt.QPushButton("Check for MONAI install")
    monaiInstallButton.clicked.connect(dependency_installer.check_and_install_monai)
    advancedLayout.addRow(monaiInstallButton)
    itkInstallButton = qt.QPushButton("Check for ITK-python install")
    itkInstallButton.clicked.connect(dependency_installer.check_and_install_itk)
    advancedLayout.addRow(itkInstallButton)
    segmentSelectedButton = qt.QPushButton("Segment selected xray")
    segmentSelectedButton.clicked.connect(self.onSegmentSelectedClicked)
    advancedLayout.addRow(segmentSelectedButton)

    self.patientBrowserCollapsible = patientBrowserCollapsible
    self.dataBrowserCollapsible = dataBrowserCollapsible
    self.advancedCollapsible = advancedCollapsible
    self.directoryPathLineEdit = directoryPathLineEdit
    self.xrayListWidget = xrayListWidget


    # Add custom toolbar with a settings button and then hide various Slicer UI elements
    self.modifyWindowUI()

    # Create logic class
    self.logic = HomeLogic()

    # set up logic
    self.logic.setup(
      layout_file_path = self.resourcePath("lungair_layout.xml"),
      model_path = self.resourcePath("PyTorchModels/LungSegmentation/model0018.pth"),
    )

    #Apply style
    self.applyApplicationStyle()


  def onClose(self, unusedOne, unusedTwo):
    pass

  def cleanup(self):
    pass

  def onLoadPatientClicked(self):
    self.logic.loadPatientFromDirectory(self.directoryPathLineEdit.currentPath)
    self.xrayListWidget.clear()
    for xray in self.logic.xrays:
      self.xrayListWidget.addItem(xray.name)

  def onXrayListWidgetDoubleClicked(self, item):
    self.logic.selectXrayByName(item.text())

  def onClinicalParametersListWidgetDoubleClicked(self, item):
    print("item double click placeholder 2:", item)

  def onFeatureComboBoxTextChanged(self, text):
    print("text change placeholder:", text)

  def onSegmentSelectedClicked(self):
    self.logic.segmentSelected()


  def hideSlicerUI(self):
    slicer.util.setDataProbeVisible(False)
    slicer.util.setMenuBarsVisible(False)
    slicer.util.setModuleHelpSectionVisible(False)
    slicer.util.setModulePanelTitleVisible(False)
    slicer.util.setPythonConsoleVisible(False)
    slicer.util.setToolbarsVisible(True)
    mainToolBar = slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar')
    keepToolbars = [
      # slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar'),
      # slicer.util.findChild(slicer.util.mainWindow(), 'ViewToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'CustomToolBar'),
      ]
    slicer.util.setToolbarsVisible(False, keepToolbars)

  def showSlicerUI(self):
    slicer.util.setDataProbeVisible(True)
    slicer.util.setMenuBarsVisible(True)
    slicer.util.setModuleHelpSectionVisible(True)
    slicer.util.setModulePanelTitleVisible(True)
    slicer.util.setPythonConsoleVisible(True)
    slicer.util.setToolbarsVisible(True)



  def modifyWindowUI(self):
    slicer.util.setModuleHelpSectionVisible(False)

    mainToolBar = slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar')

    self.CustomToolBar = qt.QToolBar("CustomToolBar")
    self.CustomToolBar.name = "CustomToolBar"
    slicer.util.mainWindow().insertToolBar(mainToolBar, self.CustomToolBar)

#     central = slicer.util.findChild(slicer.util.mainWindow(), name='CentralWidget')
#     central.setStyleSheet("background-color: #464449")

    gearIcon = qt.QIcon(self.resourcePath('Icons/Gears.png'))
    self.settingsAction = self.CustomToolBar.addAction(gearIcon, "")

    self.settingsDialog = slicer.util.loadUI(self.resourcePath('UI/Settings.ui'))
    self.settingsUI = slicer.util.childWidgetVariables(self.settingsDialog)

    self.settingsUI.CustomUICheckBox.toggled.connect(self.toggleUI)
    self.settingsUI.CustomStyleCheckBox.toggled.connect(self.toggleStyle)

    self.settingsAction.triggered.connect(self.raiseSettings)
    self.hideSlicerUI()


  def toggleStyle(self,visible):
    if visible:
      self.applyApplicationStyle()
    else:
      slicer.app.styleSheet = ''

  def toggleUI(self, visible):
    if visible:
      self.hideSlicerUI()
    else:
      self.showSlicerUI()

  def raiseSettings(self, unused):
    self.settingsDialog.exec()

  def applyApplicationStyle(self):
    # Style
    self.applyStyle([slicer.app], 'Home.qss')


  def applyStyle(self, widgets, styleSheetName):
    stylesheetfile = self.resourcePath(styleSheetName)
    with open(stylesheetfile,"r") as fh:
      style = fh.read()
      for widget in widgets:
        widget.styleSheet = style


def create_axial_to_coronal_transform_node():
  axial_to_coronal_np_matrix = np.array([
    [1., 0.,  0., 0.],
    [0., 0., -1., 0.],
    [0., 1.,  0., 0.],
    [0., 0.,  0., 1.]
  ])
  axial_to_coronal_vtk_matrix = slicer.util.vtkMatrixFromArray(axial_to_coronal_np_matrix)
  axial_to_coronal_transform_node = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
  axial_to_coronal_transform_node.SetName("axial slice to coronal slice")
  axial_to_coronal_transform_node.SetAndObserveMatrixTransformToParent(axial_to_coronal_vtk_matrix)
  return axial_to_coronal_transform_node

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

    self.img_tensor = self.seg_model.load_img(path)

    img_np = self.img_tensor[0].numpy() # The [0] contracts the single channel dimension, yielding a 2D scalar array for the image
    self.volume_node = create_volume_node_from_numpy_array(img_np, "LungAIR CXR: "+self.name)

    # TODONOW make this be the actual volume node. right now this is just for while I work on the current commit.
    self.volume_node2 = slicer.util.loadVolume(path, {"singleFile":True, "name":"LungAIR CXR TEST: "+self.name})

    # Only one of these transform nodes is needed; it is shared among all Xray instances
    if self.__class__.axial_to_coronal_transform_node is None:
      self.__class__.axial_to_coronal_transform_node = create_axial_to_coronal_transform_node()

    self.volume_node2.SetAndObserveTransformNodeID(self.__class__.axial_to_coronal_transform_node.GetID())

    # Harden so that we can rely on vtkMRMLVolumeNode::GetIJKToRASDirections to get orientation information
    self.volume_node2.HardenTransform()

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
    self.seg_mask_tensor = self.seg_model.run_inference(self.img_tensor) # a tensor of shape (H,W) representing a binary image that gives the lung fields
    self.seg_node = create_segmentation_node_from_numpy_array(
      self.seg_mask_tensor.numpy(),
      {1:"lung field"}, # TODO replace by left and right lung setup once you fix post processing, and update doc above
      "LungAIR Seg: "+self.name,
      self.volume_node
    )

  def get_numpy_array(self):
    """
    Get a 2D numpy array representation of the xray image.
    The dimensions follow the standard image-style (rows,columns) format:
    - the 0 dimension points towards the bottom of the image, towards patient inferior
    - the 1 dimension points towards the right of the image, towards the patient left
    """

    volume_node = self.volume_node2 # TODO: replace by self.volume_node when ready to swap that back in

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

    # We will attempt to find which axes of the numpy array correspond to certain patient-coordinate-directions
    array_axis_left = None
    array_axis_inferior = None
    left_dir = np.array([-1.,0.,0.])
    inferior_dir = np.array([0.,0.,-1.])

    # Tolerance for floating point comparisons
    epsilon = 0.00001

    # Here array_axis is an one of the axes of the numpy array and direction_vector is its direction in RAS coordinates
    for array_axis, direction_vector in enumerate((k_dir, j_dir, i_dir)):
      if ((direction_vector-left_dir)<epsilon).all():
        array_axis_left = array_axis
      elif ((direction_vector-inferior_dir)<epsilon).all():
        array_axis_inferior = array_axis
    if array_axis_left is None or array_axis_inferior is None:
      raise RuntimeError(f"Volume node {volume_node.GetName()} does not seem to be aligned along the expected axes; "+
        "unable to provide a numpy array because we cannot determine the standard axis order.")

    assert(all(array_axis in range(3) for array_axis in (array_axis_left, array_axis_inferior)))
    assert(array_axis_left != array_axis_inferior)
    other_axes = [array_axis for array_axis in range(3) if array_axis not in (array_axis_left, array_axis_inferior)]
    assert(len(other_axes)==1)
    array_axis_other = other_axes[0]

    if array.shape[array_axis_other]!=1:
      raise RuntimeError(f"Volume node {volume_node.GetName()} seems to have more than one slice in a direction besides RIGHT or SUPERIOR; "+
        "unable to provide a 2D numpy array for this.")

    return np.transpose(array, axes = (array_axis_other, array_axis_inferior, array_axis_left))[0]





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


class HomeLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def exitApplication(self,status=slicer.util.EXIT_SUCCESS, message=None):
    """Exit application.
    If ``status`` is ``slicer.util.EXIT_SUCCESS``, ``message`` is logged using ``logging.info(message)``
    otherwise it is logged using ``logging.error(message)``.
    """
    def _exitApplication():
      if message:
        if status == slicer.util.EXIT_SUCCESS:
          logging.info(message)
        else:
          logging.error(message)
      slicer.util.mainWindow().hide()
      slicer.util.exit(slicer.util.EXIT_FAILURE)
    qt.QTimer.singleShot(0, _exitApplication)

  def setup(self, layout_file_path, model_path):

    # --------------
    # Set up layout
    # --------------

    with open(layout_file_path,"r") as fh:
      layout_text = fh.read()

    # built-in layout IDs are all below 100, so we can choose any large random number for this one
    layoutID=501

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(layoutID, layout_text)

    # set the layout to be the current one
    layoutManager.setLayout(layoutID)

    # tweak any slice view nodes that were added in the layout
    for sliceViewName in layoutManager.sliceViewNames():
      mrmlSliceWidget = layoutManager.sliceWidget(sliceViewName)
      mrmlSliceWidget.sliceController().sliceOffsetSlider().hide() # Hide the offset slider

    # ------------------------
    # Set up xray display manager
    # ------------------------

    self.xray_display_manager = XrayDisplayManager()

    # ------------------------
    # Set up segmentation model
    # ------------------------

    self.seg_model = None
    try:
      from HomeLib.segmentation_model import SegmentationModel
    except Exception as e:
      qt.QMessageBox.critical(slicer.util.mainWindow(), "Error importing segmentation model",
        "Error importing segmentation model. Are python dependencies installed?\nDetails: "+str(e)
      )
      return False
    self.seg_model = SegmentationModel(model_path)
    return True


  def loadPatientFromDirectory(self, dir_path : str):
    self.xrays = []
    for item_name in os.listdir(dir_path):
      item_path = os.path.join(dir_path,item_name)
      if os.path.isfile(item_path):
        if item_name[-4:] != ".png":
          continue
        xray = Xray(item_path, self.seg_model)
        self.xrays.append(xray)
        self.selectXray(xray)

  def selectXray(self, xray : Xray):

    # Hide segmentation on previously selected xray, if there was one. Show segmentation of newly selected xray, if there is one.
    if hasattr(self, "selected_xray"):
      self.xray_display_manager.set_xray_segmentation_visibility(self.selected_xray, False)
    self.selected_xray = xray
    self.xray_display_manager.set_xray_segmentation_visibility(self.selected_xray, True)
    self.xray_display_manager.show_xray(self.selected_xray)

  def selectXrayByName(self, name : str):
    for xray in self.xrays: # TODO replace self.xrays by map so you don't search
      if xray.name == name:
        self.selectXray(xray)

  def segmentSelected(self):
    self.selected_xray.add_segmentation()

    # Make all segmentations invisible except the selected one
    for xray in self.xrays:
      self.xray_display_manager.set_xray_segmentation_visibility(xray, False)
    self.xray_display_manager.set_xray_segmentation_visibility(self.selected_xray, True)





class HomeTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_Home1()

  def test_Home1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #

    logic = HomeLogic()
    self.delayDisplay('Test passed!')


#
# Class for avoiding python error that is caused by the method SegmentEditor::setup
# http://issues.slicer.org/view.php?id=3871
#
class HomeFileWriter(object):
  def __init__(self, parent):
    pass
