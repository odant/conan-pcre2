from conans import ConanFile, CMake
from conans.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get, replace_in_file, rmdir
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.scm import Version
import os

def get_safe(options, name):
    try:
        return getattr(options, name, None)
    except ConanException:
        return None

class PcreConan(ConanFile):
    name = "pcre2"
    version = "10.42+0"
    license = "PCRE2 License https://www.pcre.org/licence.txt"
    description = "PCRE2 is a library of functions to support regular expressions whose syntax and semantics are as close as possible to those of the Perl 5 language."
    url = "https://github.com/odant/conan-pcre"
    settings = {
        "os": ["Windows", "Linux"],
        "compiler": ["Visual Studio", "gcc"],
        "build_type": ["Debug", "Release"],
        "arch": ["x86_64", "x86", "mips", "armv7"]
    }
    options = {
        "pcre2posix": [False, True]
    }
    default_options = "pcre2posix=True"
    generators = "cmake"
    exports_sources = "src/*", "CMakeLists.txt", "FindPCRE2.cmake", "regex.h"
    no_copy_source = True
    build_policy = "missing"

    def configure(self):
        # Pure C library
        del self.settings.compiler.libcxx

    def build(self):
        cmake = CMake(self)
        #
        if self.settings.os != "Windows":
            cmake.definitions["CMAKE_POSITION_INDEPENDENT_CODE:BOOL"] = "ON"
        cmake.definitions["BUILD_SHARED_LIBS:BOOL"] = "OFF"
        #
        cmake.definitions["PCRE2_BUILD_PCRE8:BOOL"] = "ON"
        cmake.definitions["PCRE2_BUILD_PCRE16:BOOL"] = "OFF"
        cmake.definitions["PCRE2_BUILD_PCRE32:BOOL"] = "OFF"
        cmake.definitions["PCRE2_EBCDIC:BOOL"] = "OFF"
        cmake.definitions["PCRE2_EBCDIC_NL25:BOOL"] = "OFF"
        
        cmake.definitions["PCRE2_BUILD_PCRE2GREP:BOOL"] = "OFF"
        cmake.definitions["PCRE2_BUILD_TESTS:BOOL"] = "OFF"
        
        cmake.definitions["PCRE2_SUPPORT_LIBZ:BOOL"] = "OFF"
        cmake.definitions["PCRE2_SUPPORT_LIBBZ2:BOOL"] = "OFF"
        cmake.definitions["PCRE2_SUPPORT_LIBEDIT:BOOL"] = "OFF"
        cmake.definitions["PCRE2_SUPPORT_LIBREADLINE:BOOL"] = "OFF"

        if self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            cmake.definitions["PCRE2_STATIC_RUNTIME:BOOL"] = "OFF"
        #
        cmake.configure()
        cmake.build()

    def package(self):
        self.copy("FindPCRE2.cmake", src=".", dst=".")
        self.copy("*pcre2.h", dst="include", keep_path=False)
        self.copy("*pcre2-8*.lib", dst="lib", keep_path=False)
        self.copy("*pcre2-8*.pdb", dst="bin", keep_path=False)
        self.copy("*pcre2-8*.a", dst="lib", keep_path=False)
        if get_safe(self.options, "pcre2posix"):
            self.copy("pcre2posix.h", src="./src/src", dst="include", keep_path=False)
            self.copy("regex.h", src=".", dst="include", keep_path=False)
            self.copy("*pcre2-posix*.lib", dst="lib", keep_path=False)
            self.copy("*pcre2-posix*.pdb", dst="bin", keep_path=False)
            self.copy("*pcre2-posix*.a", dst="lib", keep_path=False)
        
    def package_info(self):
        self.cpp_info.libs = [self._lib_name("pcre2-8")]
        if get_safe(self.options, "pcre2posix"):
            self.cpp_info.libs = [self._lib_name("pcre2-8"), self._lib_name("pcre2-posix")]
        if self.settings.os == "Windows":
            self.cpp_info.defines.append("PCRE2_STATIC")

    def _lib_name(self, name):
        libname = name
        if Version(self.version) >= "10.38" and is_msvc(self):
            libname += "-static"
        if self.settings.os == "Windows":
            if self.settings.build_type == "Debug":
                libname += "d"
        return libname
