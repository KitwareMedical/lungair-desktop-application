# ==========================================================================
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#          https://www.apache.org/licenses/LICENSE-2.0.txt
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ==========================================================================

import monai.deploy.core as mdc
import monai.transforms as mt
import numpy as np
import os
import PIL
import torch


@mdc.input("img_path", mdc.DataPath, mdc.IOType.DISK)
@mdc.output("img", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.output("model_to_img_matrix", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.env(pip_packages=["monai", "numpy", "pillow"])
class LoadPILOperator(mdc.Operator):
    """
    Load image from the given input (mdc.DataPath) and set numpy array to the output
    (mdc.Image).
    """

    @property
    def image_size(self):
        return 256

    def compute(
        self,
        op_input: mdc.InputContext,
        op_output: mdc.OutputContext,
        context: mdc.ExecutionContext,
    ):
        input_path = op_input.get().path
        if input_path.is_dir():
            input_path = next(input_path.glob("*.*"))  # take the first file

        image = PIL.Image.open(input_path)
        image_arr = np.asarray(image)
        if len(image_arr.shape) != 2:
            raise ValueError("image must be a 2D array")
        output_image = mdc.Image(image_arr)
        op_output.set(output_image, "img")

        model_to_img_matrix = np.diag(np.array(image_arr.shape) / self.image_size)
        op_output.set(mdc.Image(model_to_img_matrix), "model_to_img_matrix")


@mdc.input("img", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.output("img_input", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.env(pip_packages=["monai"])
class PreprocessOperator(mdc.Operator):
    """
    Apply pre-processing of image, from numpy array input to numpy array output.
    """

    @property
    def image_size(self):
        return 256

    @property
    def preprocess(self):
        # Note that we removed the last: step mt.ToTensor()
        cast_to_type = mt.CastToType(dtype=np.float32)
        add_channel = mt.AddChannel()
        resize = mt.Resize(
            spatial_size=(self.image_size, self.image_size),
            mode="bilinear",
            align_corners=False,
        )

        return mt.Compose([cast_to_type, add_channel, resize])

    def compute(
        self,
        op_input: mdc.InputContext,
        op_output: mdc.OutputContext,
        context: mdc.ExecutionContext,
    ):
        img_input = op_input.get().asnumpy()
        img_preprocessed = self.preprocess(img_input)
        img_output = mdc.Image(img_preprocessed)
        op_output.set(img_output)


@mdc.input("img_input", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.output("seg_mask", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.env(pip_packages=["monai"])
class SegmentationOperator(mdc.Operator):
    """
    Segment image, from numpy array input to numpy array output.
    """

    def compute(
        self,
        op_input: mdc.InputContext,
        op_output: mdc.OutputContext,
        context: mdc.ExecutionContext,
    ):
        img_input = op_input.get().asnumpy()  # shape=(1, 256, 256), dtype=float32
        if len(img_input.shape) != 3 or img_input.shape[0] != 1:
            raise ValueError("img_input must be a 2D array")
        img_tensor = mt.ToTensor()(img_input)

        # Note that the model seems to be gpu based, so device=="cpu" may fail.
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        img_on_device = img_tensor.to(device)

        model = context.models.get()  # get a TorchScriptModel object
        tmp = model.eval()  # Needed?
        with torch.no_grad():
            seg_net_output = model(img_on_device.unsqueeze(0))[0]

        # assumption at the moment is that we have 2-channel image out (i.e. purely
        # binary segmentation was done)
        assert seg_net_output.shape[0] == 2

        _, max_indices = seg_net_output.max(dim=0)
        seg_mask = (max_indices == 1).type(torch.uint8)

        op_output.set(mdc.Image(seg_mask.cpu().numpy()), "seg_mask")


@mdc.input("seg_mask", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.output("seg_processed", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.env(pip_packages=["monai"])
class PostprocessOperator(mdc.Operator):
    """
    Apply post-processing of image, from numpy array input to numpy array output.
    """

    @property
    def postprocess(self):
        # Instead use SegmentationPostProcessing once it works
        return mt.Compose([])

    def compute(
        self,
        op_input: mdc.InputContext,
        op_output: mdc.OutputContext,
        context: mdc.ExecutionContext,
    ):
        if False:
            # Use SegmentationPostProcessing once it works
            img_input = op_input.get("seg_mask").asnumpy()
            img_postprocessed = self.postprocess(img_input)
            img_output = mdc.Image(img_postprocessed)
            op_output.set(img_output, "seg_processed")
        else:
            op_output.set(op_input.get("seg_mask"), "seg_processed")


@mdc.input("seg_processed", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.input("model_to_img_matrix", mdc.Image, mdc.IOType.IN_MEMORY)
@mdc.output("output_directory", mdc.DataPath, mdc.IOType.DISK)
@mdc.env(pip_packages=["pillow"])
class SavePILOperator(mdc.Operator):
    """
    Save image to the given output (mdc.DataPath) from numpy array input (mdc.Image).
    """

    def compute(
        self,
        op_input: mdc.InputContext,
        op_output: mdc.OutputContext,
        context: mdc.ExecutionContext,
    ):
        output_directory = op_output.get("output_directory").path
        os.makedirs(output_directory, exist_ok=True)
        img_input = op_input.get("seg_processed").asnumpy()
        img_pil = PIL.Image.fromarray(img_input)
        output_path = os.path.join(output_directory, "mask.png")
        img_pil.save(output_path)

        model_to_img_matrx = op_input.get("model_to_img_matrix").asnumpy()
        output_path = os.path.join(output_directory, "model_to_img_matrix")
        np.save(output_path, model_to_img_matrx)


@mdc.resource(cpu=1, gpu=1, memory="1Gi")
class App(mdc.Application):
    """
    mdc.Application class for the MedNIST classifier.
    """

    def compose(self):
        load_pil_op = LoadPILOperator()
        preprocess_op = PreprocessOperator()
        segmentation_op = SegmentationOperator()
        postprocess_op = PostprocessOperator()
        save_pil_op = SavePILOperator()

        self.add_flow(load_pil_op, preprocess_op, {"img": "img"})
        self.add_flow(preprocess_op, segmentation_op, {"img_input": "img_input"})
        self.add_flow(segmentation_op, postprocess_op, {"seg_mask": "seg_mask"})
        self.add_flow(postprocess_op, save_pil_op, {"seg_processed": "seg_processed"})

        self.add_flow(
            load_pil_op, save_pil_op, {"model_to_img_matrix": "model_to_img_matrix"}
        )


if __name__ == "__main__":
    App(do_run=True)
