import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from HomeLib import monai_installer

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
    monaiInstallButton.clicked.connect(monai_installer.check_and_install_monai)
    advancedLayout.addRow(monaiInstallButton)

    self.patientBrowserCollapsible = patientBrowserCollapsible
    self.dataBrowserCollapsible = dataBrowserCollapsible
    self.advancedCollapsible = advancedCollapsible
    self.directoryPathLineEdit = directoryPathLineEdit


    # Add custom toolbar with a settings button and then hide various Slicer UI elements
    self.modifyWindowUI()

    # Create logic class
    self.logic = HomeLogic()

    # set up defaults for viewers (this was carried over from SlicerCAT; not sure how much of it is needed)
    self.logic.setup3DView()
    self.logic.setupSliceViewers()

    # set up layout
    self.logic.setupLayout(self.resourcePath("lungair_layout.xml"))

    #Apply style
    self.applyApplicationStyle()


  def onClose(self, unusedOne, unusedTwo):
    pass

  def cleanup(self):
    pass

  def onLoadPatientClicked(self):
    self.logic.loadPatientFromDirectory(self.directoryPathLineEdit.currentPath)

  def onXrayListWidgetDoubleClicked(self, item):
    print("item double click placeholder 1:", item)

  def onClinicalParametersListWidgetDoubleClicked(self, item):
    print("item double click placeholder 2:", item)

  def onFeatureComboBoxTextChanged(self, text):
    print("text change placeholder:", text)


  def hideSlicerUI(self):
    slicer.util.setDataProbeVisible(False)
    slicer.util.setMenuBarsVisible(False, ignore=['MainToolBar', 'ViewToolBar'])
    slicer.util.setModuleHelpSectionVisible(False)
    slicer.util.setModulePanelTitleVisible(False)
    slicer.util.setPythonConsoleVisible(False)
    slicer.util.setToolbarsVisible(True)
    mainToolBar = slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar')
    keepToolbars = [
      slicer.util.findChild(slicer.util.mainWindow(), 'MainToolBar'),
      slicer.util.findChild(slicer.util.mainWindow(), 'ViewToolBar'),
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

  #settings for 3D view
  def setup3DView(self):
    layoutManager = slicer.app.layoutManager()
    # layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    # controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
    # controller.setBlackBackground()
    # controller.set3DAxisVisible(False)
    # controller.set3DAxisLabelVisible(False)
    # controller.setOrientationMarkerType(3)  #Axis marker
    # controller.setStyleSheet("background-color: #000000")

  def setupSliceViewers(self):
    for name in slicer.app.layoutManager().sliceViewNames():
        sliceWidget = slicer.app.layoutManager().sliceWidget(name)
        self.setupSliceViewer(sliceWidget)

    # Set linked slice views  in all existing slice composite nodes and in the default node
    sliceCompositeNodes = slicer.util.getNodesByClass('vtkMRMLSliceCompositeNode')
    defaultSliceCompositeNode = slicer.mrmlScene.GetDefaultNodeByClass('vtkMRMLSliceCompositeNode')
    if not defaultSliceCompositeNode:
      defaultSliceCompositeNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLSliceCompositeNode')
      defaultSliceCompositeNode.UnRegister(None)  # CreateNodeByClass is factory method, need to unregister the result to prevent memory leaks
      slicer.mrmlScene.AddDefaultNode(defaultSliceCompositeNode)
    sliceCompositeNodes.append(defaultSliceCompositeNode)
    for sliceCompositeNode in sliceCompositeNodes:
      sliceCompositeNode.SetLinkedControl(True)

  #Settings for slice views
  def setupSliceViewer(self, sliceWidget):
    controller = sliceWidget.sliceController()
    # controller.setOrientationMarkerType(3)  #Axis marker
    # controller.setRulerType(1)  #Thin ruler
    # controller.setRulerColor(0) #White ruler
    # controller.setStyleSheet("background-color: #000000")
    # controller.sliceViewLabel = ''

  def setupLayout(self, layout_file_path):

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

  def loadPatientFromDirectory(self, dir_path):
    for item_name in os.listdir(dir_path):
      item_path = os.path.join(dir_path,item_name)
      if os.path.isfile(item_path):
        print("PLACEHOLDER: would now add into logic:", item_name)





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
