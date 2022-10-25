from genericpath import exists
import os
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
from slicer.util import VTKObservationMixin
from HomeLib import dependency_installer
from HomeLib.image_utils import *
from HomeLib.plots import *
import HomeLib.xray as xray
from HomeLib.constants import *

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
        try:
            from HomeLib.segmentation_model import SegmentationModel
        except Exception as e:
            # We cannot use slicer.util.errorDisplay here because there is no main window (it will only log an error and not raise a popup).
            qt.QMessageBox.critical(slicer.util.mainWindow(), "Error importing segmentation model",
                                    "Error importing segmentation model. If python dependencies are not installed, install them and restart the application. \nDetails: "+str(e)
                                    )
            return False

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
        backendComboBox = qt.QComboBox()
        backendComboBox.addItems([
            SegmentationModel.ModelSource.LOCAL_WEIGHTS.value,
            SegmentationModel.ModelSource.LOCAL_DEPLOY.value,
            SegmentationModel.ModelSource.DOCKER_DEPLOY.value,
        ])
        def backendChanged(index):
            self.backendToUse = SegmentationModel.ModelSource(backendComboBox.currentText)
        backendComboBox.currentIndexChanged.connect(backendChanged)
        backendLayout = qt.QHBoxLayout()
        backendLayout.addWidget(backendComboBox)
        self.backendToUse = SegmentationModel.ModelSource(backendComboBox.currentText)
        advancedLayout.addRow("Backend model:", backendLayout)
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
            backend_to_use = self.backendToUse,
        )

        # Apply style
        self.applyApplicationStyle()

        # Make additional UI modifications after the main window is shown
        slicer.util.mainWindow().initialWindowShown.connect(self.onApplicationStartupCompleted)

    def onClose(self, unusedOne, unusedTwo):
        pass

    def cleanup(self):
        pass

    def onApplicationStartupCompleted(self):
        # Set initial size of the split view
        half_height = slicer.util.mainWindow().centralWidget().size.height()//2
        centralWidgetLayoutFrame = slicer.util.mainWindow().centralWidget().findChild(qt.QFrame, "CentralWidgetLayoutFrame")
        splitter = centralWidgetLayoutFrame.findChild(qt.QSplitter)
        # For the splitter movement to work, we need to first let other events finish processing, hence the timer with timeout of 0
        qt.QTimer.singleShot(0, lambda : splitter.handle(1).moveSplitter(half_height))

    def onLoadPatientClicked(self):
        self.logic.loadXraysFromDirectory(self.xrayDirectoryPathLineEdit.currentPath)
        self.xrayListWidget.clear()
        for xray in self.logic.xray_collection.values():
            self.xrayListWidget.addItem(xray.name)

        self.logic.loadEICUFromDirectory(self.csvDirectoryPathLineEdit.currentPath, self.resourcePath("Schema/eICU"))

    def onXrayListWidgetDoubleClicked(self, item):
        self.logic.selectXrayByName(item.text())

    def onClinicalParametersListWidgetDoubleClicked(self, item):
        print("item double click placeholder 2:", item)

    def onFeatureComboBoxTextChanged(self, text):
        print("text change placeholder:", text)

    def onSegmentSelectedClicked(self):
        self.logic.segmentSelected(self.backendToUse)


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


# TODO: move this to an appropriate place
def tableNodeFromDataFrame(df, editable = False):
    """Given a pandas dataframe, return a vtkMRMLTableNode with a copy of the data as strings.
    This is not performant; use on small dataframes only."""
    tableNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode")
    for col in df.columns:

        # Populate array
        array = vtk.vtkStringArray()
        for val in df[col]:
            array.InsertNextValue(str(val))

        # The array name should end up as the first value in the column
        array.SetName(str(col))
        tableNode.AddColumn(array)

    tableNode.SetLocked(not editable)
    return tableNode



class ClinicalParametersTabWidget(qt.QTabWidget): # TODO move this class to an appropriate place
    def __init__(self):
        super().__init__()

        self.patient_table_view = slicer.qMRMLTableView()
        self.patient_table_view.setMRMLScene(slicer.mrmlScene)
        self.addTab(self.patient_table_view, "Patient data")
        self.patient_table_node = None # vtkMRMLTableNode

        self.fio2_line_plot = SlicerPlotData("fio2Line")
        self.addTab(self.fio2_line_plot.plot_view, "FiO2 plot")
        self.fio2_bar_plot = SlicerPlotData("fio2Bar")
        self.addTab(self.fio2_bar_plot.plot_view, "FiO2 times")

    def set_table_node(self, table_node):
        """Set the patient table view to show the given vtkMRMLTableNode."""
        self.patient_table_view.setMRMLTableNode(table_node)
        self.patient_table_view.setFirstRowLocked(True) # Put the column names in the top header, rather than A,B,...

    def set_patient_df(self, patient_df):
        """Populate the patient table view with the contents of the given dataframe"""
        if self.patient_table_node is not None:
            slicer.mrmlScene.RemoveNode(self.patient_table_node)
        self.patient_table_node = tableNodeFromDataFrame(patient_df, editable=False)
        self.patient_table_node.SetName("ClinicalParamatersTabWidget_PatientTableNode")
        self.set_table_node(self.patient_table_node)

    def set_fio2_line_plot(self, fio2_data):
        """
        Populate the fio2 line plot with the data from the given numpy array.

        Args:
          fio2_data: A numpy array of shape (N,2), where
            the first column is time in min and
            the second column is FiO2 %
        """

        self.fio2_line_plot.set_plot_data(
            data = fio2_data,
            x_axis_label = "time since unit admission (min)",
            y_axis_label = "FiO2 (%)",
            title = "FiO2",
        )

    def set_fio2_bar_plot(self, bins, total_times):
        """
        Populate the fio2 bar plot with the given data

        Args:
          bins: a list of pairs representing the start and end of FiO2 % bins, to go with total_times
          total_times: array with the total time, in minutes, spent in each bin from bins
        """
        self.fio2_bar_plot.set_plot_data(
            data = np.array([np.array(bins).mean(axis=1) , total_times]).transpose(),
            x_axis_label = "FiO2 range (%)",
            y_axis_label = "Total time (min)",
            title = "FiO2 times",
            legend_label="Time (min)",
            plot_type = "scatterbar",
            labels = [f"{start} to {end}" for start, end in bins]
        )

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

    def setup(self, layout_file_path, model_path, backend_to_use):

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
            sliceWidget = layoutManager.sliceWidget(sliceViewName)

            # See http://apidocs.slicer.org/master/classqMRMLViewControllerBar.html
            # for some of the available accessors to the widgets in top bar
            sliceController = sliceWidget.sliceController()

            sliceController.sliceOffsetSlider().hide()
            sliceController.pinButton().hide()

            barWidget = sliceWidget.sliceController().barWidget()
            barWidget.setStyleSheet(f"background-color: #{BAR_WIDGET_COLOR}; color: #FFFFFF;")
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
                logging.warn(f"Warning: Found an unexpected qMRMLPlotWidget named \"{plotWidget.name}\"; there may be UI setup issues.")

            # we use plotview widgets as placeholders that we can replace with our own custom "view",
            # so we don't actually care about the plot view
            plotWidget.plotView().hide()

            barWidget = plotWidget.plotController().barWidget()
            barWidget.setStyleSheet(f"background-color: #{BAR_WIDGET_COLOR}; color: #FFFFFF;")

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

        self.clinical_parameters_tabWidget = ClinicalParametersTabWidget()
        self.risk_analysis_tabWidget = qt.QTabWidget() # TODO make this, eventually
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

        self.xray_collection = xray.XrayCollection()

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
        self.seg_model = dict(model_path=model_path, model=SegmentationModel(model_path, backend_to_use))

        # ------------------------
        # Check for eicu dependencies
        # ------------------------
        try:
            from HomeLib.eicu import Eicu
        except Exception as e:
            qt.QMessageBox.critical(slicer.util.mainWindow(), "Error importing eICU interface class",
                                    "Error importing eICU interface class. If python dependencies are not installed, install them and restart the application. \nDetails: "+str(e)
                                    )
            return False

        # ------------------------
        # Adjust python console colors
        # ------------------------

        slicer.util.mainWindow().pythonConsole().setStyleSheet(f"background-color: #FFFFFF")


        return True

    def loadXraysFromDirectory(self, dir_path : str):
        self.xray_collection.clear()
        for item_name in os.listdir(dir_path):
            item_path = os.path.join(dir_path,item_name)
            loaded_xrays = xray.load_xrays(item_path, self.seg_model)
            if len(loaded_xrays)==0:
                raise RuntimeError("Failed to load xray(s) from path", item_path)
            self.xray_collection.extend(loaded_xrays)
            self.xray_collection.select(loaded_xrays[0].name)

    def selectXrayByName(self, name : str):
        self.xray_collection.select(name)

    def segmentSelected(self, backend_to_use):
        self.xray_collection.segment_selected(backend_to_use)

    def loadEICUFromDirectory(self, dir_path : str, schema_dir : str):
        """ As a placeholder to get some EHR data to play with, we use the eICU dataset.
        See https://eicu-crd.mit.edu/about/eicu/
        It's not NICU-focused or even pediatric-focused, but it's something to work with for now.

        Args:
          dir_path : path to the directory that contains eICU tables as csv.gz files.
          schema_dir : path to the directory that contains table schema text files; see EICU class documentation for details.
        """
        import pandas as pd
        if not hasattr(self,"eicu") or not self.eicu:
            from HomeLib.eicu import Eicu
            self.eicu = Eicu(dir_path, schema_dir)
        self.unitstay_id = self.eicu.get_random_unitstay()
        print(f"We will pretend that this patient is {self.eicu.get_patient_id_from_unitstay(self.unitstay_id)} from the eICU dataset,"
              + f" with unit stay ID {self.unitstay_id}.")

        fio2_data, average_fio2, bins, total_times = self.eicu.process_fio2_data_for_unitstay(self.unitstay_id)

        patient_df = self.eicu.get_patient_from_unitstay(self.unitstay_id).to_frame().reset_index()
        patient_df.columns = ["Parameter", "Value"]
        patient_df = pd.concat([patient_df, pd.DataFrame([{"Parameter":"Average FiO2", "Value":average_fio2}])])

        self.clinical_parameters_tabWidget.set_patient_df(patient_df)
        self.clinical_parameters_tabWidget.set_fio2_line_plot(fio2_data.to_numpy())
        self.clinical_parameters_tabWidget.set_fio2_bar_plot(bins, total_times)

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
