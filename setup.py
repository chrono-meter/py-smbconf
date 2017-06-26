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
from Cython.Build import cythonize
from pathlib import Path
import subprocess


def find_file(pattern):
    root = Path('/usr')  # list(Path.cwd().parents)[-1]
    for result in root.rglob(pattern):
        return result
    raise RuntimeError('"%s" is not found. Please run "apt install samba-dev" or "yum install samba-devel", else install Samba from source.' % (pattern, ))


include_dir = find_file('smbconf.h').parent
libsmbd_base = find_file('libsmbd-base*.so*')  # The correct package name is "samba-lib".

try:
    subprocess.check_call('/sbin/ldconfig -p | grep libsmbd-base', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except subprocess.CalledProcessError:
    raise RuntimeError('"libsmbd-base" is not found in ldconfig. Example solution: 1. find the correct path of "libsmbd-base*.so*". 2. add the path into "/etc/ld.so.conf.d/samba.conf". 3. run "sudo ldconfig".')


extensions = [
    Extension(
        "smbconf",
        ["src/smbconf.pyx"],
        include_dirs=[
            str(include_dir),
        ],
        libraries=[
            "talloc",
            "smbconf",
            # libsmbd_base.name.split('.')[0][3:],  # apt: smbd-base, rpm: smbd-base-samba4
        ],
        extra_compile_args=["-g", "-O0"],
        extra_link_args=[
            "-L" + str(libsmbd_base.parent),
            "-Wl,-rpath",
            "-Wl," + str(libsmbd_base.parent),
            # "-ltalloc",
            # "-lsmbconf",
            # "-lsmbd-base-samba4",
            "-l:" + libsmbd_base.name,  # apt: /usr/lib/x86_64-linux-gnu/samba/libsmbd-base.so.0, rpm: /usr/lib64/samba/libsmbd-base-samba4.so
        ],
    ),
]


setup(
    name='smbconf',
    version='1.0',
    packages=[''],
    package_dir={'': 'src'},
    package_data={'': ['*.html', '*.c']},
    ext_modules=cythonize(extensions)
)
