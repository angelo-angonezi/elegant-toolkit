# config module

# Code destined to storing config
# global variables used in multiple scripts.

######################################################################
# imports

from os import environ
from cet.diagnostics.check_java import get_java_home
from cet.diagnostics.check_gpu import gpu_is_available
from cet.diagnostics.check_gpu import get_torch_device
from cet.diagnostics.check_java import java_home_is_valid

######################################################################
# defining global variables

# tunables (edit by hand)

# progress tracker // system usage
UPDATE_TIME = 0.1
MEMORY_LIMIT = 95
SHOW_USAGE = False

# image loading
JAVA_MEMORY = '4096m'

# detected state (probed once, at import time)

# gpu
GPU = gpu_is_available()
DEVICE = get_torch_device()

# java
JAVA_HOME = get_java_home()
JAVA_HOME_IS_VALID = java_home_is_valid(JAVA_HOME)

# checking whether java home is valid
if JAVA_HOME_IS_VALID:

    # setting JAVA_HOME env var (if not already set) so jpype/pims.bioformats find this
    # env's conda-forge openjdk install (see cet.setup.download_jdk) instead of falling
    # back to their own JVM auto-discovery
    environ.setdefault('JAVA_HOME', JAVA_HOME)

######################################################################
# end of current module
