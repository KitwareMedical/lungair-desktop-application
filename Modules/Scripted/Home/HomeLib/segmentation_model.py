# This is currently configured to work with models produced in exploration6.ipynb
# in https://github.com/ebrahimebrahim/lung-seg-exploration
# This wrapper class will handle loading a model and running inference

import enum
import monai
import numpy as np
import os
import PIL
import re
import shutil
import slicer
import tempfile
import torch
from .segmentation_post_processing import SegmentationPostProcessing


class SegmentationModel:
    class NoValue(enum.Enum):
        def __repr__(self):
            return f'<{self.__class__.__name__}.{self.name}>'

    class ModelSource(NoValue):
        LOCAL_WEIGHTS = 'Locally saved model weights, without MONAI Deploy'
        LOCAL_DEPLOY = 'MONAI Deploy with locally saved model weights'
        DOCKER_DEPLOY = 'MONAI Deploy with docker image'

    def __init__(self, load_pth_path, backend_to_use):
        """
        This class provides a way to interface with a lung segmentation model trained in MONAI.
        It loads the model on construction, and it handles loading and transforming
        images and running inference.
        """
        self.model_source = backend_to_use

        self.load_pth_path = load_pth_path
        # For save_zip_path, remove trailing .pth if present; append .zip
        self.save_zip_path = re.sub(r"\.pth$", "", self.load_pth_path) + ".zip"

        if self.model_source == self.ModelSource.LOCAL_WEIGHTS:
            model_dict = torch.load(self.load_pth_path, map_location=torch.device('cpu'))

            self.seg_net = model_dict['model']
            self.learning_rate = model_dict['learning_rate']
            self.training_losses = model_dict['training_losses']
            self.validation_losses = model_dict['validation_losses']
            self.epoch_number = model_dict['epoch_number']
            self.best_validation_loss = model_dict['best_validation_loss']
            self.best_validation_epoch = model_dict['best_validation_epoch']
            self.image_size = model_dict['image_size']

            # Transforms a given image to the input format expected by the segmentation network
            self.transform = monai.transforms.Compose([
                monai.transforms.CastToType(dtype=np.float32),  # TODO dtype should have been included in the model_dict
                monai.transforms.AddChannel(),
                monai.transforms.Resize(
                    spatial_size=(self.image_size, self.image_size),
                    mode='bilinear',
                    align_corners=False
                ),
                monai.transforms.ToTensor()
            ])

            self.seg_post_process = SegmentationPostProcessing()

        if self.model_source in (self.ModelSource.LOCAL_DEPLOY, self.ModelSource.DOCKER_DEPLOY) and not os.path.exists(self.save_zip_path):
            # Write out a TorchScript version of the model, for use in MONAI Deploy.
            model_dict = torch.load(self.load_pth_path, map_location=torch.device('cpu'))
            seg_net = model_dict['model']
            # set dropout and batch normalization layers to evaluation mode before running
            # inference
            seg_net.eval()
            torch.jit.script(seg_net).save(self.save_zip_path)

    def run_inference(self, img):
        """
        Execute segmentation model on a chest xray, given as an array of shape (height, width).

        The image axes are assumed to be in "matrix" order, with the origin in the upper left of the image:
        - The 0 axis should go along the height of the radiograph, towards patient-inferior
        - The 1 axis should go along the width of the radiograph, towards patient-left/image-right

        The segmentation model should include post-processing but this is SKIPPED for now; TODO.
        Currently it's just a segmentation network.

        Returns (seg_mask, model_to_img_matrix), where:
          seg_mask is a torch tensor of shape (height, width), a binary label mask indicating the lung field
          model_to_img_matrix is a 2D numpy array representing the linear transform from the coordinate space of the segmentation model
            output to the original coordinate space of the given array img.
        """
        if len(img.shape) != 2:
            raise ValueError("img must be a 2D array")

        if self.model_source == self.ModelSource.LOCAL_WEIGHTS:
            self.seg_net.eval()
            img_input = self.transform(img)
            seg_net_output = self.seg_net(img_input.unsqueeze(0))[0]

            # assumption at the moment is that we have 2-channel image out (i.e. purely binary segmentation was done)
            assert(seg_net_output.shape[0] == 2)

            _, max_indices = seg_net_output.max(dim=0)
            seg_mask = (max_indices == 1).type(torch.uint8)

            model_to_img_matrix = np.diag(np.array(img.shape) / self.image_size)

            # TODO skipping post processing because post processing causes crash due to ITK
            # python issues seg_processed = self.seg_post_process(seg_mask)
            seg_processed = seg_mask

        if self.model_source in (self.ModelSource.LOCAL_DEPLOY, self.ModelSource.DOCKER_DEPLOY):
            # Communicate with monai deploy via files.  Locations are:
            input_dir_path = tempfile.mkdtemp()
            output_dir_path = tempfile.mkdtemp()
            input_file_path = os.path.join(input_dir_path, "input.png")
            output_mask_path = os.path.join(output_dir_path, "mask.png")
            output_model_to_img_matrix_path = os.path.join(output_dir_path, "model_to_img_matrix.npy")

            # Write input file
            img_pil = PIL.Image.fromarray(img)
            img_pil = img_pil.convert("L")
            img_pil.save(input_file_path)

            # Run monai-deploy
            monai_deploy_path = shutil.which("monai-deploy")
            if self.model_source == self.ModelSource.LOCAL_DEPLOY:
                deploy_app_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "deploy_app.py")
                process_image_command = [monai_deploy_path,
                                         "exec", deploy_app_path,
                                         "-m", self.save_zip_path,
                                         "-i", input_dir_path,
                                         "-o", output_dir_path]
            if self.model_source == self.ModelSource.DOCKER_DEPLOY:
                # TODO: Unfortunately, this docker image appears to require CUDA>=11.3.
                docker_image = "ghcr.io/kitwaremedical/lungair-desktop-application/lung_air_model_deploy:latest"
                # Note: to *create* the docker image, use
                # f"{monai_deploy_path} package {deploy_app_path} --tag {docker_image} --model {self.save_zip_path}"
                # f"echo {CR_PAT} | docker login -u {User} --password-stdin ghcr.io"
                # f"docker push {docker_image}"
                process_image_command = [monai_deploy_path,
                                         "run", docker_image,
                                         input_dir_path, output_dir_path]
            proc = slicer.util.launchConsoleProcess(process_image_command, useStartupEnvironment=False)
            slicer.util.logProcessOutput(proc)

            # Read output files
            seg_processed = torch.from_numpy(np.asarray(PIL.Image.open(output_mask_path)))
            model_to_img_matrix = np.load(output_model_to_img_matrix_path)

            # Clean up files that were used for communication
            shutil.rmtree(output_dir_path)
            shutil.rmtree(input_dir_path)

        return seg_processed, model_to_img_matrix
