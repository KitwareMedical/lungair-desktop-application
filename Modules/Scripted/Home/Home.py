import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from HomeLib import dependency_installer
from HomeLib.image_utils import *
from HomeLib.xray import *

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
