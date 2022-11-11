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

By default, the LungAir application runs the underlying MONAI Torch model with "Locally saved model weights, without MONAI deploy".  To instead use "MONAI Deploy with locally saved model weights" or "MONAI Deploy with docker image", select that option for the "Backend model" in the Advanced section in the lower left of the main screen.  If you have not yet created a docker image to use, you will need to do that first, with commands similar to:

```shell
# Useful directory and paths
cd lungair-desktop-application
DEPLOY_APP='Modules/Scripted/Home/HomeLib/deploy_app.py'
MODEL_PATH='Modules/Scripted/Home/Resources/PyTorchModels/LungSegmentation/model0018.pth'
DOCKER_BASE='nvcr.io/nvidia/pytorch:22.09-py3'
NEW_DOCKER='ghcr.io/kitwaremedical/lungair-desktop-application/lung_air_model_deploy:latest'

# Build a docker image to be deployed
monai-deploy package $DEPLOY_APP --model $MODEL_PATH -b $DOCKER_BASE --tag $NEW_DOCKER
```
Note that the currently specified $DOCKER_BASE was current as of September, 2022.  It may be wise to update this to a later date or to eliminate the "-b" option entirely and accept the default.

This docker image can also be used from the command line to run the model.  Place the image to analyzed in an otherwise empty input directory of your choosing.  The resulting output mask and scaling matrix will be placed in the output directory of your choosing.

```shell
# Run the model using the created docker image
monai-deploy run $NEW_DOCKER input_dir output_dir
```

Note that the model also can be run from the command line without using the docker image.
```shell
# Run the deployed application in the local environment
monai-deploy exec $DEPLOY_APP -m $MODEL_PATH -i input_dir -o output_dir
```

## Acknowledgments

This work was supported by the National Institutes of Health under Award Number R42HL145669. The content is solely the responsibility of the authors and does not necessarily represent the official views of the National Institutes of Health.

---

![LungAIR by Kitware, Inc.](Applications/LungAIRApp/Resources/Images/LogoFull.png?raw=true)
