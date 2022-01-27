import slicer, qt

def check_and_install_monai(self):
  """
  Check if monai is installed, and if not then prompt user to possibly attempt an install.
  Returns whether monai is present at the end.
  """
  try:
    import monai, skimage, tqdm
    slicer.util.messageBox("MONAI found! Version: " + str(monai.__version__))
    return True
  except ModuleNotFoundError:
    wantInstall = qt.QMessageBox.question(slicer.util.mainWindow(), "Missing Dependency", "MONAI or a related dependency was not found. Install it?")
    if wantInstall == qt.QMessageBox.Yes:
      slicer.util.pip_install("monai[skimage,tqdm]")
      try:
        import monai, skimage, tqdm
        slicer.util.messageBox("Finished installing MONAI.")
        return True
      except ModuleNotFoundError as e:
        qt.QMessageBox.critical(slicer.util.mainWindow(), "MONAI Install Error", "Unable to install MONAI. Check the console for details.")
        print(e)
        return False

def check_and_install_itk(self):
  """
  Check if itk is installed, and if not then prompt user to possibly attempt an install.
  Returns whether itk is present at the end.
  """
  try:
    import itk
    slicer.util.messageBox("ITK found! Version: " + str(itk.__version__))
    return True
  except ModuleNotFoundError:
    wantInstall = qt.QMessageBox.question(slicer.util.mainWindow(), "Missing Dependency", "ITK or a related dependency was not found. Install it?")
    if wantInstall == qt.QMessageBox.Yes:
      slicer.util.pip_install("itk")
      try:
        import itk
        slicer.util.messageBox("Finished installing ITK.")
        return True
      except ModuleNotFoundError as e:
        qt.QMessageBox.critical(slicer.util.mainWindow(), "ITK Install Error", "Unable to install ITK. Check the console for details.")
        print(e)
        return False