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
      except ModuleNotFoundError:
        qt.QMessageBox.critical(slicer.util.mainWindow(), "MONAI Install Error", "Unable to install MONAI. Check the console for details.")
        return False