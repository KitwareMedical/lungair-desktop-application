import slicer, qt, importlib, functools

def check_and_install_package(module_names, pip_install_name):
  """
  Check if given module can be imported, and if not then prompt user to possibly attempt an install.

  Args:
    module_names: a list of strings for the modules for which import needs to succeed
    pip_install_name: the name of the package to install using pip in order to make the import succeed
      (or whatever text should follow "pip install" in the installation command)
  Returns whether the import can succeed at the end.
  """
  try:
    modules = []
    for module_name in module_names:
      modules.append(importlib.import_module(module_name))
    version_text = '\n'.join([f'  {module_name} version: {module.__version__}' for module, module_name in zip(modules, module_names)])
    slicer.util.infoDisplay("Modules found!\n" + version_text, "Modules Found")
    return True
  except ModuleNotFoundError as e1:
    wantInstall = slicer.util.confirmYesNoDisplay(f"Package was not found. Install it?\nDetails of missing import: {e1}", "Missing Dependency")
    if wantInstall:
      slicer.util.pip_install(pip_install_name)
      try:
        for module_name in module_names:
          importlib.import_module(module_name)
        slicer.util.infoDisplay("Finished installing.", "Install Success")
        return True
      except ModuleNotFoundError as e2:
        slicer.util.errorDisplay("Unable to install package. Check the console for details.", "Install Error")
        print(e2)
        return False

check_and_install_monai = functools.partial(check_and_install_package, ["monai", "skimage", "tqdm"], "monai[skimage,tqdm]")
check_and_install_itk = functools.partial(check_and_install_package, ["itk"], "itk")
check_and_install_pandas = functools.partial(check_and_install_package, ["pandas"], "pandas")
check_and_install_matplotlib = functools.partial(check_and_install_package, ["matplotlib"], "matplotlib")