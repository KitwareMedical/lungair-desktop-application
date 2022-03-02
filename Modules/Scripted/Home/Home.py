from genericpath import exists
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
    patientBrowserLayout = qt.QFormLayout(patientBrowserCollapsible)

    explanation =  "In lieu of an EHR-linked patient browser,\n"
    explanation += "we include for now a directory selector.\n"
    explanation += "Images and DICOM files in in the directory\n"
    explanation += "are considered to be chest xrays, while csv\n"
    explanation += "files are considered to contain clinical data."
    patientBrowserLayout.addRow(qt.QLabel(explanation))
    xrayDirectoryPathLineEdit = ctk.ctkPathLineEdit()
    xrayDirectoryPathLineEdit.filters = ctk.ctkPathLineEdit.Dirs
    xrayDirectoryPathLineEdit.currentPath = "/home/ebrahim/Desktop/test_patient2" # temporary measure to speed up testing
    csvDirectoryPathLineEdit = ctk.ctkPathLineEdit()
    csvDirectoryPathLineEdit.filters = ctk.ctkPathLineEdit.Dirs
    csvDirectoryPathLineEdit.currentPath = "/home/ebrahim/data/eICU/eICU-Original-Data" # temporary measure to speed up testing
    patientBrowserLayout.addRow("XRay Image Directory", xrayDirectoryPathLineEdit)
    patientBrowserLayout.addRow("eICU Data Directory", csvDirectoryPathLineEdit)

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
    def add_install_button(package_name:str, install_function:str):
      installButton = qt.QPushButton(f"Check for {package_name} install")
      installButton.clicked.connect(lambda unused_arg : install_function())
      advancedLayout.addRow(installButton)
    add_install_button("MONAI", dependency_installer.check_and_install_monai)
    add_install_button("ITK-python", dependency_installer.check_and_install_itk)
    add_install_button("pandas", dependency_installer.check_and_install_pandas)
    add_install_button("matplotlib", dependency_installer.check_and_install_matplotlib)
    segmentSelectedButton = qt.QPushButton("Segment selected xray")
    segmentSelectedButton.clicked.connect(self.onSegmentSelectedClicked)
    advancedLayout.addRow(segmentSelectedButton)

    self.patientBrowserCollapsible = patientBrowserCollapsible
    self.dataBrowserCollapsible = dataBrowserCollapsible
    self.advancedCollapsible = advancedCollapsible
    self.xrayDirectoryPathLineEdit = xrayDirectoryPathLineEdit
    self.csvDirectoryPathLineEdit = csvDirectoryPathLineEdit
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
    self.logic.loadXraysFromDirectory(self.xrayDirectoryPathLineEdit.currentPath)
    self.xrayListWidget.clear()
    for xray in self.logic.xrays:
      self.xrayListWidget.addItem(xray.name)

    self.logic.loadEICUFromDirectory(self.csvDirectoryPathLineEdit.currentPath, self.resourcePath("Schema/eICU"))

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

    # central = slicer.util.findChild(slicer.util.mainWindow(), name='CentralWidget')
    # central.setStyleSheet("background-color: #B9BAA3")

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

    bar_widget_color = "656DA4"

    # tweak any slice view nodes that were added in the layout
    for sliceViewName in layoutManager.sliceViewNames():
      sliceWidget = layoutManager.sliceWidget(sliceViewName)

      # See http://apidocs.slicer.org/master/classqMRMLViewControllerBar.html
      # for some of the available accessors to the widgets in top bar
      sliceController = sliceWidget.sliceController()

      sliceController.sliceOffsetSlider().hide()
      sliceController.pinButton().hide()

      barWidget = sliceWidget.sliceController().barWidget()
      barWidget.setStyleSheet(f"background-color: #{bar_widget_color}; color: #FFFFFF;")
      resetViewButton = [child for child in barWidget.children() if child.name=="FitToWindowToolButton"][0]
      resetViewButton.toolTip = "<p>Reset X-Ray view to fill the viewer.</p>"

    self.clinical_parameters_widget = None
    self.risk_analysis_widget = None
    for i in range(layoutManager.plotViewCount):
      plotWidget = layoutManager.plotWidget(i)
      if plotWidget.name == 'qMRMLPlotWidgetClinicalParameters':
        self.clinical_parameters_widget = plotWidget
      elif plotWidget.name == 'qMRMLPlotWidgetRiskAnalysis':
        self.risk_analysis_widget = plotWidget
      else:
        logging.warn("Warning: Found an unexpected qMRMLPlotWidget; there may be UI setup issues.")

      # we use plotview widgets as placeholders that we can replace with our own custom "view",
      # so we don't actually care about the plot view
      plotWidget.plotView().hide()

      barWidget = plotWidget.plotController().barWidget()
      barWidget.setStyleSheet(f"background-color: #{bar_widget_color}; color: #FFFFFF;")

      # This removes the stretch that was added at
      # https://github.com/Slicer/Slicer/blob/d3b8e33a8a2f5a4cb73a0060e34513eb8573c12b/Libs/MRML/Widgets/qMRMLPlotViewControllerWidget.cxx#L110
      # which is necessary to get the bar widgets to have a consistent appearance
      barWidget.layout().takeAt(barWidget.layout().count()-1)

      for widget in barWidget.children():
        if not widget.isWidgetType():
          continue
        if widget.name not in ["MaximizeViewButton", "ViewLabel"]:
          widget.hide()

    if self.clinical_parameters_widget is None:
      raise RuntimeError("Unable to find Clinical Parameters widget; UI setup has failed.")
    if self.risk_analysis_widget is None:
      raise RuntimeError("Unable to find Risk Analysis widget; UI setup has failed.")

    self.clinical_parameters_tabWidget = qt.QTabWidget()
    self.risk_analysis_tabWidget = qt.QTabWidget()
    self.clinical_parameters_widget.layout().addWidget(self.clinical_parameters_tabWidget)
    self.risk_analysis_widget.layout().addWidget(self.risk_analysis_tabWidget)


    # ------------------------
    # Set up workspace directory
    # ------------------------

    self.workspace_dir = os.path.join(slicer.util.settingsValue("DefaultScenePath", None), "LungAIR-Application-Workspace")
    os.makedirs(self.workspace_dir, exist_ok=True)

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
      # We cannot use slicer.util.errorDisplay here because there is no main window (it will only log an error and not raise a popup).
      qt.QMessageBox.critical(slicer.util.mainWindow(), "Error importing segmentation model",
        "Error importing segmentation model. If python dependencies are not installed, install them and restart the application. \nDetails: "+str(e)
      )
      return False
    self.seg_model = SegmentationModel(model_path)

    # ------------------------
    # Check for eicu dependencies
    # ------------------------
    try:
      from HomeLib.eicu import Eicu
      import matplotlib
    except Exception as e:
      qt.QMessageBox.critical(slicer.util.mainWindow(), "Error importing eICU interface class",
        "Error importing eICU interface class. If python dependencies are not installed, install them and restart the application. \nDetails: "+str(e)
      )
      return False

    # ------------------------
    # Adjust python console colors
    # ------------------------

    for child in slicer.util.mainWindow().children():
      if child.name == "PythonConsoleDockWidget":
        child.setStyleSheet(f"background-color: #FFFFFF")


    return True

  def loadXraysFromDirectory(self, dir_path : str):
    self.xrays = []
    for item_name in os.listdir(dir_path):
      item_path = os.path.join(dir_path,item_name)
      loaded_xrays = load_xrays(item_path, self.seg_model)
      if len(loaded_xrays)==0:
        raise RuntimeError("Failed to load xray(s) from path", item_path)
      self.xrays.extend(loaded_xrays)
      self.selectXray(loaded_xrays[0])

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

  def loadEICUFromDirectory(self, dir_path : str, schema_dir : str):
    """ As a placeholder to get some EHR data to play with, we use the eICU dataset.
    See https://eicu-crd.mit.edu/about/eicu/
    It's not NICU-focused or even pediatric-focused, but it's something to work with for now.

    Args:
      dir_path : path to the directory that contains eICU tables as csv.gz files.
      schema_dir : path to the directory that contains table schema text files; see EICU class documentation for details.
    """
    if not hasattr(self,"eicu") or not self.eicu:
      from HomeLib.eicu import Eicu
      self.eicu = Eicu(dir_path, schema_dir)
    self.unitstay_id = self.eicu.get_random_unitstay()
    print(f"We will pretend that this patient is {self.eicu.get_patient_id_from_unitstay(self.unitstay_id)} from the eICU dataset,"
      + f" with unit stay ID {self.unitstay_id}.")

    fio2_data, average_fio2, figure = self.eicu.process_fio2_data_for_unitstay(self.unitstay_id)

    # TODO: this is a temporary experimental measure. we should not add this tab again and again each time a patient is loaded.
    patient_data_widget = qt.QWidget()
    patient_data_widget.setLayout(qt.QVBoxLayout())
    patient_data_dump = qt.QLabel(str(self.eicu.get_patient_from_unitstay(self.unitstay_id)))
    patient_data_widget.layout().addWidget(patient_data_dump)
    patient_data_widget.layout().addWidget(qt.QLabel(f"Average FiO2 for this patient: {average_fio2}"))
    scrollArea = qt.QScrollArea()
    scrollArea.setWidget(patient_data_widget)
    self.clinical_parameters_tabWidget.addTab(scrollArea, "Patient data")

    import matplotlib
    matplotlib.use('agg')
    plot_path = os.path.join(self.workspace_dir, "plot.png")
    figure.savefig(plot_path)
    print("Saved FiO2 plot to", plot_path)
    pixmap = qt.QPixmap(plot_path)
    plotQLabel = qt.QLabel()
    plotQLabel.setPixmap(pixmap)

    # TODO: this is a temporary experimental measure. we should not add this tab again and again each time a patient is loaded.
    scrollArea = qt.QScrollArea()
    scrollArea.setWidget(plotQLabel)
    self.clinical_parameters_tabWidget.addTab(scrollArea, "FiO2 plot")






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
