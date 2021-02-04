/*
 * This file is part of guanaco-ctf.
 * Copyright 2021 Diamond Light Source
 * Copyright 2021 Rosalind Franklin Institute
 *
 * Author: James Parkhurst
 *
 * guanaco-ctf is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * guanaco-ctf is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with guanaco-ctf. If not, see <http:// www.gnu.org/licenses/>.
 */
#include <pybind11/pybind11.h>
#include <pybind11/numpy.h>
#include <guanaco/guanaco.h>

namespace py = pybind11;

namespace guanaco {
  
  /**
   * Allow conversion from string to enum
   */
  template <typename T>
  py::enum_<T> enum_wrapper(const py::handle& scope, const char* name) {
    py::enum_<T> obj(scope, name);
    obj.def("__init__", [](T& v, const std::string& str) {
      py::object obj = py::cast(v);
      py::dict entries = obj.get_type().attr("__entries");
      for (auto item : entries) {
        if (str == item.first.cast<std::string>()) {
          v = item.second.cast<py::tuple>()[0].cast<T>();
          return;
        }
      }
      std::string tname = typeid(T).name();
      py::detail::clean_type_id(tname);
      throw py::value_error("\"" + std::string(str)
                        + "\" is not a valid value for enum type " + tname);
    });

    // Allow implicit conversions from string and int to enum
    py::implicitly_convertible<py::str, T>();
    py::implicitly_convertible<int, T>();
    return obj;
  }

  /**
   * A short wrapper function to call the reconstruction code
   */
  template <typename T>
  void reconstruct(const py::array_t<T> &sinogram,
                   py::array_t<T> &reconstruction,
                   const py::array_t<T> &angles,
                   const py::array_t<T> &defocus,
                   float centre = 0,
                   float pixel_size = 1,
                   eDevice device = e_host,
                   int gpu_index = -1) {

    // Check the input
    GUANACO_ASSERT(sinogram.ndim() == 2 || sinogram.ndim() == 3);
    GUANACO_ASSERT(reconstruction.ndim() == 2);
    GUANACO_ASSERT(angles.ndim() == 1);

    // Check the sinogram dimensions
    if (sinogram.ndim() == 2) {
      GUANACO_ASSERT(sinogram.shape()[0] == angles.size());
      GUANACO_ASSERT(sinogram.shape()[1] == reconstruction.shape()[0]);
      GUANACO_ASSERT(sinogram.shape()[1] == reconstruction.shape()[1]);
    } else {
      GUANACO_ASSERT(sinogram.shape()[0] == defocus.size());
      GUANACO_ASSERT(sinogram.shape()[1] == angles.size());
      GUANACO_ASSERT(sinogram.shape()[2] == reconstruction.shape()[0]);
      GUANACO_ASSERT(sinogram.shape()[2] == reconstruction.shape()[1]);
    }

    // Initialise the configuration
    auto args = [&] {
      auto c = Config();
      c.device = device;
      c.gpu_index = gpu_index;
      c.num_pixels = sinogram.shape()[sinogram.ndim()-1];
      c.num_angles = angles.size();
      c.num_defocus = defocus.size();
      c.grid_width = reconstruction.shape()[1];
      c.grid_height = reconstruction.shape()[0];
      c.pixel_size = pixel_size;
      c.centre = centre;
      c.angles.assign(angles.data(), angles.data() + angles.size());
      c.defocus.assign(defocus.data(), defocus.data() + defocus.size());
      return c;
    }();

    // Create the reconstructor object
    auto rec = make_reconstructor(args);

    // Perform the reconstruction
    rec(sinogram.data(), reconstruction.mutable_data());
  }

}

PYBIND11_MODULE(guanaco_ext, m) {
  
  // Export the device enum
  guanaco::enum_wrapper<guanaco::eDevice>(m, "eDevice")
    .value("cpu", guanaco::e_host)
    .value("gpu", guanaco::e_device)
    .export_values();

  // Export the reconstruction function
  m.def("recon",
        &guanaco::reconstruct<float>,
        py::arg("sinogram"),
        py::arg("reconstruction"),
        py::arg("angles"),
        py::arg("defocus"),
        py::arg("centre"),
        py::arg("pixel_size") = 1.0,
        py::arg("device") = guanaco::e_host,
        py::arg("gpu_index") = -1);
}
