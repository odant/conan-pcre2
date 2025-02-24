from conans import ConanFile, CMake, tools
from conans.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file, rmdir
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version
import os

class PcreConan(ConanFile):
    name = "pcre2"
    version = "10.45+0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.pcre.org/"
    description = "Perl Compatible Regular Expressions"
    topics = ("regex", "regexp", "perl")
    license = "BSD-3-Clause"
    package_type = "library"
    settings = {
        "os": ["Windows", "Linux"],
        "compiler": ["Visual Studio", "gcc"],
        "build_type": ["Debug", "Release"],
        "arch": ["x86_64", "x86", "mips", "armv7"]
    }
    options = {
        "dll_sign": [False, True],
        "pcre2posix": [False, True],
        "shared": [True, False],
        "fPIC": [True, False],
        "build_pcre2_8": [True, False],
        "build_pcre2_16": [True, False],
        "build_pcre2_32": [True, False],
        "build_pcre2grep": [True, False],
        "with_zlib": [True, False],
        "with_bzip2": [True, False],
        "support_jit": [True, False],
        "grep_support_callout_fork": [True, False],
        "link_size": [2, 3, 4],
    }
    default_options = {
        "dll_sign": True,
        "pcre2posix": True,
        "shared": True,
        "fPIC": True,
        "build_pcre2_8": True,
        "build_pcre2_16": True,
        "build_pcre2_32": False,
        "build_pcre2grep": False,
        "with_zlib": False,
        "with_bzip2": False,
        "support_jit": True,
        "grep_support_callout_fork": True,
        "link_size": 2,
    }

    generators = "cmake"
    exports_sources = "src/*", "CMakeLists.txt", "FindPCRE2.cmake", "regex.h"
    no_copy_source = True
    build_policy = "missing"

    def configure(self):
        if not self.options.shared or self.settings.os != "Windows":
            self.options.rm_safe("dll_sign")
        if self.options.shared or self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")
        if not self.options.build_pcre2grep:
            self.options.rm_safe("with_zlib")
            self.options.rm_safe("with_bzip2")
            self.options.rm_safe("grep_support_callout_fork")
        if not self.options.build_pcre2_8 and not self.options.build_pcre2_16 and not self.options.build_pcre2_32:
            raise ConanInvalidConfiguration("At least one of build_pcre2_8, build_pcre2_16 or build_pcre2_32 must be enabled")
        if self.options.build_pcre2grep and not self.options.build_pcre2_8:
            raise ConanInvalidConfiguration("build_pcre2_8 must be enabled for the pcre2grep program")

    def build_requirements(self):
        if self.options.get_safe("dll_sign"):
            self.build_requires("windows_signtool/[>=1.2]@%s/stable" % self.user)

    def requirements(self):
        if self.options.get_safe("with_zlib"):
            self.requires("zlib/[>=1.2.11 <2]")
        if self.options.get_safe("with_bzip2"):
            self.requires("bzip2/1.0.8")

    def build(self):
        cmake = CMake(self)
        #
        if self.settings.os != "Windows":
            cmake.definitions["CMAKE_POSITION_INDEPENDENT_CODE:BOOL"] = "ON"
        
        cmake.definitions["BUILD_SHARED_LIBS:BOOL"] = self.options.shared
        cmake.definitions["BUILD_STATIC_LIBS:BOOL"] = not self.options.shared
        #
        cmake.definitions["PCRE2_BUILD_PCRE2_8:BOOL"] = self.options.build_pcre2_8
        cmake.definitions["PCRE2_BUILD_PCRE2_16:BOOL"] = self.options.build_pcre2_16
        cmake.definitions["PCRE2_BUILD_PCRE2_32:BOOL"] = self.options.build_pcre2_32
        
        cmake.definitions["PCRE2_EBCDIC:BOOL"] = "OFF"
        cmake.definitions["PCRE2_EBCDIC_NL25:BOOL"] = "OFF"
        
        cmake.definitions["PCRE2_SUPPORT_LIBZ:BOOL"] = self.options.get_safe("with_zlib", False)
        cmake.definitions["PCRE2_SUPPORT_LIBBZ2:BOOL"] = self.options.get_safe("with_bzip2", False)

        cmake.definitions["PCRE2_BUILD_PCRE2GREP:BOOL"] = self.options.build_pcre2grep
        cmake.definitions["PCRE2_BUILD_TESTS:BOOL"] = "OFF"
        
        cmake.definitions["PCRE2_SUPPORT_LIBEDIT:BOOL"] = "OFF"
        cmake.definitions["PCRE2_SUPPORT_LIBREADLINE:BOOL"] = "OFF"
        
        cmake.definitions["PCRE2_SUPPORT_JIT:BOOL"] = self.options.support_jit

        cmake.definitions["PCRE2_LINK_SIZE"] = self.options.link_size
        cmake.definitions["PCRE2GREP_SUPPORT_CALLOUT_FORK:BOOL"] = self.options.get_safe("grep_support_callout_fork", False)

        if is_msvc(self):
            cmake.definitions["PCRE2_STATIC_RUNTIME:BOOL"] = is_msvc_static_runtime(self)
            cmake.definitions["INSTALL_MSVC_PDB:BOOL"] = "ON"
        #
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "man"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        self.copy("FindPCRE2.cmake", src=".", dst=".")
        if self.options.get_safe("pcre2posix"):
            self.copy("regex.h", src=".", dst="include", keep_path=False)
        # Sign DLL
        if self.options.get_safe("dll_sign"):
            import windows_signtool
            pattern = os.path.join(self.package_folder, "bin", "*.dll")
            for fpath in glob.glob(pattern):
                fpath = fpath.replace("\\", "/")
                for alg in ["sha1", "sha256"]:
                    is_timestamp = True if self.settings.build_type == "Release" else False
                    cmd = windows_signtool.get_sign_command(fpath, digest_algorithm=alg, timestamp=is_timestamp)
                    self.output.info("Sign %s" % fpath)
                    self.run(cmd)
        
    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if not self.options.shared:
            self.cpp_info.defines.append("PCRE2_STATIC")
