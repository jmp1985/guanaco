#
# This file is part of guanaco-ctf.
# Copyright 2021 Diamond Light Source
# Copyright 2021 Rosalind Franklin Institute
#
# Author: James Parkhurst
#
# guanaco-ctf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guanaco-ctf is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with guanaco-ctf. If not, see <http:// www.gnu.org/licenses/>.
#


import mrcfile
import numpy
import time
from math import pi
import guanaco.detail
import guanaco.detail.mp

__all__ = ["reconstruct_file", "reconstruct"]


def get_centre(shape, centre, sinogram_order=True):
    if not sinogram_order:
        shape = list(shape)
        shape[0], shape[-2] = shape[-2], shape[0]
    if centre is None:
        centre = numpy.ones(shape[0], dtype="float32") * (shape[-1] / 2.0)
    elif numpy.array(centre).size == 1:
        centre = numpy.ones(shape[0], dtype="float32") * centre
    return centre.astype(dtype="float32", copy=False)


def reconstruct(
    tomogram,
    angles,
    reconstruction=None,
    centre=None,
    pixel_size=1,
    min_defocus=0,
    max_defocus=0,
    sinogram_order=False,
    transform=None,
    device="cpu",
    ncore=None,
    nchunk=None,
    gpu_list=None,
):
    """
    The sinogram is expected to be provided with dimensions as follows:

    - Stack of projections:
        ( THETA, Y, X ) - sinogram_order = False

    - Stack of sinograms:
        ( Y, THETA, X ) - sinogram_order = True

    - Stack of defocus corrected projections
        ( THETA, DEFOCUS, Y, X ) - sinogram_order = False

    - Stack of defocus corrected sinograms
        ( Y, DEFOCUS, THETA, X ) - sinogram_order = True

    """

    def initialise_sinogram(tomogram, sinogram_order):
        assert len(tomogram.shape) in [3, 4]
        tomogram = tomogram.astype(dtype="float32", copy=False)
        if not sinogram_order:
            tomogram = numpy.swapaxes(tomogram, 0, -2)  # doesn't copy data
        return tomogram

    def initialise_reconstruction(reconstruction, sinogram):
        if reconstruction is None:
            shape = (sinogram.shape[0], sinogram.shape[-1], sinogram.shape[-1])
            reconstruction = numpy.zeros(shape, dtype="float32")
        else:
            assert reconstruction.shape[0] == sinogram.shape[0]
            assert reconstruction.shape[1] == sinogram.shape[-1]
            assert reconstruction.shape[2] == sinogram.shape[-1]
        return reconstruction.astype(dtype="float32", copy=False)

    # Initialize sinogram
    sinogram = initialise_sinogram(tomogram, sinogram_order)

    # Initialise reconstruction
    reconstruction = initialise_reconstruction(reconstruction, sinogram)

    # Generate args for the algorithm.
    centre = get_centre(sinogram.shape, centre)

    # Perform the reconstruction in multiple threads
    guanaco.detail.mp.reconstruction_dispatcher(
        sinogram,
        reconstruction,
        centre,
        angles,
        pixel_size=pixel_size,
        min_defocus=min_defocus,
        max_defocus=max_defocus,
        transform=transform,
        device=device,
        ncore=ncore,
        nchunk=nchunk,
        gpu_list=gpu_list,
    )

    # Return reconstruction
    return reconstruction


def reconstruct_file(
    input_filename,
    output_filename,
    corrected_filename="GUANACO_CORRECTED.dat",
    centre=None,
    energy=None,
    defocus=None,
    num_defocus=None,
    step_defocus=None,
    spherical_aberration=None,
    astigmatism=None,
    astigmatism_angle=None,
    phase_shift=None,
    device="cpu",
    ncore=None,
    transform=None,
    chunk_size=None,
):
    """
    Do the reconstruction

    """
    start_time = time.time()

    def read_projection_metadata(infile):

        # Read the voxel size
        voxel_size = infile.voxel_size
        print("Voxel size: ", infile.voxel_size)

        # Read the angles
        assert infile.data.shape[0] == infile.extended_header.shape[0]
        angles = numpy.zeros(infile.extended_header.shape[0], dtype=numpy.float32)
        for i in range(infile.extended_header.shape[0]):
            angles[i] = infile.extended_header[i]["Alpha tilt"] * pi / 180.0
            print("Image %d; angle %.4f" % (i + 1, angles[i]))

        # Return metadata
        return angles, voxel_size

    def open_reconstruction_file(output_filename, shape, voxel_size):

        # Open the file
        outfile = mrcfile.new_mmap(
            output_filename, overwrite=True, mrc_mode=2, shape=shape
        )

        # Set the voxel size
        outfile.voxel_size = voxel_size

        # Return the handle
        return outfile

    # Open the input file
    print("Reading %s" % input_filename)
    with mrcfile.mmap(input_filename) as infile:

        # Get the projection metadata
        angles, voxel_size = read_projection_metadata(infile)

        # Get the pixel size
        assert voxel_size["x"] == voxel_size["y"]
        pixel_size = 1.0  # FIXME voxel_size["x"]

        # Get the projection data
        projections = infile.data

        # Set the reconstruction shape
        output_shape = (
            projections.shape[1],
            projections.shape[2],
            projections.shape[2],
        )

        # Get the rotation centre
        centre = get_centre(projections.shape, centre, False)

        # Get the corrected projections.
        projections, min_defocus, max_defocus = guanaco.correct_projections(
            projections,
            centre,
            pixel_size,
            energy,
            defocus,
            num_defocus,
            step_defocus,
            spherical_aberration,
            astigmatism,
            astigmatism_angle,
            phase_shift,
            corrected_filename,
            device,
        )

        # Open the output file
        print("Writing reconstruction to %s" % output_filename)
        with open_reconstruction_file(
            output_filename, output_shape, voxel_size
        ) as outfile:

            # Get the reconstruction data
            reconstruction = outfile.data

            # Reconstruct
            reconstruct(
                projections,
                angles,
                reconstruction,
                centre=centre,
                pixel_size=pixel_size,
                min_defocus=min_defocus,
                max_defocus=max_defocus,
                sinogram_order=False,
                transform=transform,
                device=device,
                ncore=ncore,
            )

    print("Time: %.2f seconds" % (time.time() - start_time))
