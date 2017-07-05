#-
# Copyright (c) 2014 iXsystems, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

import Cython.Compiler.Options
Cython.Compiler.Options.annotate = True
from distutils.core import setup
from distutils.extension import Extension
from distutils.command.build_ext import build_ext
from Cython.Build import cythonize
from pathlib import Path
import subprocess
import shlex
import re


def find_exe(exe_name, path=None):
    """Find executable file by `which` command, else try to find in `path` argument.
    """
    try:
        result = Path(subprocess.check_output(['which', str(exe_name)], universal_newlines=True).strip())
    except subprocess.CalledProcessError:
        pass
    else:
        if result.exists():
            return result

    for dirname in path or ():
        result = Path(dirname) / exe_name
        if result.exists():
            return result

    raise FileNotFoundError(exe_name)


def find_dependencies(exe_name, lib_names):
    """Get dependency shared objects from `exe_name` by `ldd` command, then return shortest matches with `lib_names`.
    """
    result = {}

    for line in subprocess.check_output(['ldd', str(exe_name)], universal_newlines=True).splitlines():
        m = re.search(r'(\S+)\s+=>\s+(\S+)\s+\(0x[0-9A-Fa-f]+\)', line)
        if m:
            lib_name, lib_path = m.groups()
            for needed in lib_names:
                if needed in lib_name:
                    result.setdefault(needed, []).append(Path(lib_path))

    return {lib_name: sorted(lib_paths, key=lambda x: x.name.split('.')[0])[0] for lib_name, lib_paths in result.items()}


class build_ext(build_ext):
    """Fire `distribution.ext_modules.finalize_options`.
    """

    def finalize_options(self):
        for x in self.distribution.ext_modules:
            if getattr(x, 'finalize_options'):
                x.finalize_options(self)

        super().finalize_options()


class Extension(Extension):

    @classmethod
    def create(cls, *args, pkg_config=None, exe_name=None, search_path=(), lib_names=(), **kwargs):
        """Cython-0.25.2 doesn't support set additional parameter via __init__.
        """
        cls = type(cls.__name__, (cls, ), {})
        cls.pkg_config = pkg_config
        cls.exe_name = exe_name
        cls.search_path = search_path
        cls.lib_names = lib_names
        return cls(*args, **kwargs)

    def finalize_options(self, cmd):
        # usage: setup.py build_ext --include-dirs /path/to/includes --libraries lib1,lib2 --library-dirs /path/to/libs --rpath /path/to/libs install

        if not any([cmd.distribution.include_dirs, cmd.include_dirs]) and self.pkg_config:
            # get compiler flags from pkg-config.
            self.include_dirs.extend(
                x[2:] for x in shlex.split(subprocess.check_output(['pkg-config', '--cflags-only-I', self.pkg_config], universal_newlines=True))
            )

        if not any([cmd.library_dirs, cmd.libraries, cmd.rpath]) and self.lib_names:
            # ctypes.util.find_library uses ldconfig and ld. So try to find libraries from executable file.
            dependency = find_dependencies(find_exe(self.exe_name, self.search_path), lib_names=self.lib_names)

            library_dirs = list({str(x.parent) for x in dependency.values()})
            libraries = [':' + x.name for x in dependency.values()]

            self.library_dirs.extend(library_dirs)
            self.runtime_library_dirs.extend(library_dirs)
            self.libraries.extend(libraries)


if __name__ == '__main__':
    extensions = [
        Extension.create(
            "smbconf",
            ["src/smbconf.pyx"],
            extra_compile_args=["-g", "-O0"],
            pkg_config='samba-hostconfig',
            exe_name='smbd',
            search_path=('/sbin', '/usr/sbin', '/usr/local/sbin'),
            lib_names=('talloc', 'smbconf', 'smbd-base'),
        ),
    ]

    setup(
        name='smbconf',
        version='1.0',
        packages=[''],
        package_dir={'': 'src'},
        package_data={'': ['*.html', '*.c']},
        ext_modules=cythonize(extensions),
        cmdclass={'build_ext': build_ext},
    )
