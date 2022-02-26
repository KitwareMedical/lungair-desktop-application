import slicer, qt, importlib, functools

def check_and_install_package(module_names, pip_install_name, pre_install_hook = None):
  """
  Check if given module can be imported, and if not then prompt user to possibly attempt an install.

  Args:
    module_names: a list of strings for the modules for which import needs to succeed
    pip_install_name: the name of the package to install using pip in order to make the import succeed
      (or whatever text should follow "pip install" in the installation command)
    pre_install_hook: an optional callable that will be called before installation, in the event that installation is going to take place
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
      if pre_install_hook is not None:
        pre_install_hook()
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


# A pre-install step for monai, where we use light-the-torch to install torch more carefully:
# with light-the-torch, the computation backend is auto-detected from the available hardware preferring CUDA over CPU.
def monai_pre_install():
  slicer.util.pip_install('light-the-torch')
  import light_the_torch
  wheel_urls = light_the_torch.find_links(['monai'])
  if not wheel_urls:
    raise RuntimeError("light-the-torch has could not find suitable PyTorch wheel URLs to install the torch dependencies of MONAI.")
  for wheel_url in wheel_urls:
    print("Downloading and installing the following wheel URL obtained via light-the-torch:", wheel_url)
    slicer.util.pip_install(wheel_url)

check_and_install_itk = functools.partial(check_and_install_package, ["itk"], "itk")
check_and_install_pandas = functools.partial(check_and_install_package, ["pandas"], "pandas")
check_and_install_matplotlib = functools.partial(check_and_install_package, ["matplotlib"], "matplotlib")
check_and_install_monai = functools.partial(check_and_install_package, ["monai", "skimage", "tqdm"], "monai[skimage,tqdm]", monai_pre_install)
