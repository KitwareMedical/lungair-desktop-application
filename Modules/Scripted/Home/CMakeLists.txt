#-----------------------------------------------------------------------------
set(MODULE_NAME Home)
set(MODULE_LIB HomeLib)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  ${MODULE_LIB}/dependency_installer.py
  ${MODULE_LIB}/image_utils.py
  ${MODULE_LIB}/segmentation_model.py
  ${MODULE_LIB}/segmentation_post_processing.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Icons/Gears.png
  Resources/UI/Settings.ui
  Resources/Home.qss
  Resources/PyTorchModels/LungSegmentation/model0018.pth
  )

slicerFunctionAddPythonQtResources(MODULE_PYTHON_QRC_RESOURCES
  Resources/HomeResources.qrc
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}  ${MODULE_PYTHON_QRC_RESOURCES}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()
