# guanaco
> Python library for doing 3D CTF correction

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/jmp1985/guanaco.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/jmp1985/guanaco/context:python)
[![Total alerts](https://img.shields.io/lgtm/alerts/g/jmp1985/guanaco.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/jmp1985/guanaco/alerts/)

## Installation

To install from source, clone this repository and then do the following:

```sh
git submodule update --init --recursive
```

In order to build this package, the following dependencies are required:

- The CUDA toolkit
- FFTW

```sh
pip install -r requirements.txt
python setup.py install 
```

## Testing

To run the tests, clone this repository and the do the following:

```sh
python setup.py test
```

## Usage

To do a tomographic reconstruction with no CTF correction do something do the following

```sh
guanaco -i images.mrc -o rec.mrc -d gpu
```

To correct all images with the same single defocus something do the following

```sh
guanaco -i images.mrc -o rec.mrc -d gpu --df=20000 --Cs=2.7
```

To correct all images with the same defocus range something do the following

```sh
guanaco -i images.mrc -o rec.mrc -d gpu --df=20000 --Cs=2.7 --ndf=10
```

## Issues

Please use the [GitHub issue tracker](https://github.com/rosalindfranklininstitute/guanaco/issues) to submit bugs or request features.

## License

Copyright Diamond Light Source and Rosalind Franklin Institute, 2021

Distributed under the terms of the GPLv3 license, guanaco is free and open source software.

