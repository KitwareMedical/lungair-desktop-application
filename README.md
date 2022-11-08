# LungAIR by Kitware, Inc.

A customized version of Slicer for bringing AI-based BPD risk prediction into the NICU.

Created using [Slicer Custom App Template](https://github.com/KitwareMedical/SlicerCustomAppTemplate).

_This project is in active development and may change from version to version without notice._


## Building on Linux

The build process is similar to [that of Slicer](https://slicer.readthedocs.io/en/latest/developer_guide/build_instructions/linux.html#pre-requisites). Currently this application is only being tested for Linux, though it may work on other platforms if the appropriate Slicer build instructions are followed.

Once the needed dependencies are installed (including Qt) following the [Slicer build instructions](https://slicer.readthedocs.io/en/latest/developer_guide/build_instructions/linux.html#pre-requisites), the basic build process is as follows:
```sh
mkdir LungAIR-SuperBuild
cd LungAIR-SuperBuild
cmake -S ~/LungAIR/ -B . -DQt5_DIR:PATH=<QT INSTALL PATH>/gcc_64/lib/cmake/Qt5 -DCMAKE_BUILD_TYPE:STRING=Release
make -j <NUMBER OF PARALLEL JOBS>
```

Launch the application from the executable `LungAIR-SuperBuild/Slicer-build/LungAIR`.

## Using the MONAI Deploy docker image

_(to be written)_



## Acknowledgments

This work was supported by the National Institutes of Health under Award Number R42HL145669. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.

---

![LungAIR by Kitware, Inc.](Applications/LungAIRApp/Resources/Images/LogoFull.png?raw=true)

