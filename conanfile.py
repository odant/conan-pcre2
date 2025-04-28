from conan import ConanFile, tools
from conan.errors import ConanException
import os, glob

class PcreConan(ConanFile):
    name = "pcre2"
    version = "10.45+0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.pcre.org/"
    description = "Perl Compatible Regular Expressions"
    topics = ("regex", "regexp", "perl")
    license = "BSD-3-Clause"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "ninja": [True, False],
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
        "ninja": True,
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

    exports_sources = "src/*", "regex.h"
    no_copy_source = True
    build_policy = "missing"
    python_requires = "windows_signtool/[>=1.2]@odant/stable"
    
    def layout(self):
        tools.cmake.cmake_layout(self, src_folder="src")

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
        if self.options.ninja:
            self.build_requires("ninja/[>=1.12.1]")

    def requirements(self):
        if self.options.get_safe("with_zlib"):
            self.requires("zlib/[>=1.3.11<2]@odant/stable")
        if self.options.get_safe("with_bzip2"):
            self.requires("bzip2/1.0.8")
            
    def generate(self):
        benv = tools.env.VirtualBuildEnv(self)
        benv.generate()
        renv = tools.env.VirtualRunEnv(self)
        renv.generate()
        if tools.microsoft.is_msvc(self):
            vc = tools.microsoft.VCVars(self)
            vc.generate()
        deps = tools.cmake.CMakeDeps(self)    
        deps.generate()
        cmakeGenerator = "Ninja" if self.options.ninja else None
        tc = tools.cmake.CMakeToolchain(self, generator=cmakeGenerator)
        if self.settings.os != "Windows":
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        #
        tc.variables["PCRE2_BUILD_PCRE2_8"] = self.options.build_pcre2_8
        tc.variables["PCRE2_BUILD_PCRE2_16"] = self.options.build_pcre2_16
        tc.variables["PCRE2_BUILD_PCRE2_32"] = self.options.build_pcre2_32
        
        tc.variables["PCRE2_EBCDIC"] = "OFF"
        tc.variables["PCRE2_EBCDIC_NL25"] = "OFF"
        
        tc.variables["PCRE2_SUPPORT_LIBZ"] = self.options.get_safe("with_zlib", False)
        tc.variables["PCRE2_SUPPORT_LIBBZ2"] = self.options.get_safe("with_bzip2", False)

        tc.variables["PCRE2_BUILD_PCRE2GREP"] = self.options.build_pcre2grep
        tc.variables["PCRE2_BUILD_TESTS"] = "OFF"
        
        tc.variables["PCRE2_SUPPORT_LIBEDIT"] = "OFF"
        tc.variables["PCRE2_SUPPORT_LIBREADLINE"] = "OFF"
        
        tc.variables["PCRE2_SUPPORT_JIT"] = self.options.support_jit

        tc.variables["PCRE2_LINK_SIZE"] = self.options.link_size
        tc.variables["PCRE2GREP_SUPPORT_CALLOUT_FORK"] = self.options.get_safe("grep_support_callout_fork", False)

        if tools.microsoft.is_msvc(self):
            tc.variables["PCRE2_STATIC_RUNTIME"] = tools.microsoft.is_msvc_static_runtime(self)
            tc.variables["INSTALL_MSVC_PDB"] = "ON"
        tc.generate()

    def build(self):
        cmake = tools.cmake.CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = tools.cmake.CMake(self)
        cmake.install()
        tools.files.rmdir(self, os.path.join(self.package_folder, "cmake"))
        tools.files.rmdir(self, os.path.join(self.package_folder, "man"))
        tools.files.rmdir(self, os.path.join(self.package_folder, "share"))
        tools.files.rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.files.rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        if self.options.get_safe("pcre2posix"):
            tools.files.copy(self, "regex.h", src=self.export_sources_folder, dst=os.path.join(self.package_folder, "include"), keep_path=False)
        # Sign DLL
        if self.options.get_safe("dll_sign"):
            self.python_requires["windows_signtool"].module.sign(self, [os.path.join(self.package_folder, "bin", "*.dll")])
        
    def _lib_name(self, name):
        libname = name
        if tools.scm.Version(self.version) >= "10.38" and tools.microsoft.is_msvc(self) and not self.options.shared:
            libname += "-static"
        if self.settings.os == "Windows":
            if self.settings.build_type == "Debug":
                libname += "d"
            if self.settings.compiler == "gcc" and self.options.shared:
                libname += ".dll"
        return libname

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "PCRE2")
        self.cpp_info.set_property("pkg_config_name", "libpcre2")
        self.cpp_info.set_property("cmake_target_name", "PCRE2::PCRE2")
        if self.options.build_pcre2_8:
            # pcre2-8
            self.cpp_info.components["pcre2-8"].set_property("cmake_target_name", "PCRE2::8BIT")
            self.cpp_info.components["pcre2-8"].set_property("pkg_config_name", "libpcre2-8")
            self.cpp_info.components["pcre2-8"].libs = [self._lib_name("pcre2-8")]
            if not self.options.shared:
                self.cpp_info.components["pcre2-8"].defines.append("PCRE2_STATIC")
            # pcre2-posix
            self.cpp_info.components["pcre2-posix"].set_property("cmake_target_name", "PCRE2::POSIX")
            self.cpp_info.components["pcre2-posix"].set_property("pkg_config_name", "libpcre2-posix")
            self.cpp_info.components["pcre2-posix"].libs = [self._lib_name("pcre2-posix")]
            self.cpp_info.components["pcre2-posix"].requires = ["pcre2-8"]
            if tools.scm.Version(self.version) >= "10.43" and tools.microsoft.is_msvc(self) and self.options.shared:
                self.cpp_info.components["pcre2-posix"].defines.append("PCRE2POSIX_SHARED=1")

        # pcre2-16
        if self.options.build_pcre2_16:
            self.cpp_info.components["pcre2-16"].set_property("cmake_target_name", "PCRE2::16BIT")
            self.cpp_info.components["pcre2-16"].set_property("pkg_config_name", "libpcre2-16")
            self.cpp_info.components["pcre2-16"].libs = [self._lib_name("pcre2-16")]
            if not self.options.shared:
                self.cpp_info.components["pcre2-16"].defines.append("PCRE2_STATIC")
        
        # pcre2-32
        if self.options.build_pcre2_32:
            self.cpp_info.components["pcre2-32"].set_property("cmake_target_name", "PCRE2::32BIT")
            self.cpp_info.components["pcre2-32"].set_property("pkg_config_name", "libpcre2-32")
            self.cpp_info.components["pcre2-32"].libs = [self._lib_name("pcre2-32")]
            if not self.options.shared:
                self.cpp_info.components["pcre2-32"].defines.append("PCRE2_STATIC")

        if self.options.build_pcre2grep:
            bin_path = os.path.join(self.package_folder, "bin")
            self.output.info(f"Appending PATH environment variable: {bin_path}")
            self.env_info.PATH.append(bin_path)
            # FIXME: This is a workaround to avoid ConanException. zlib and bzip2
            # are optional requirements of pcre2grep executable, not of any pcre2 lib.
            if self.options.with_zlib:
                self.cpp_info.components["pcre2-8"].requires.append("zlib::zlib")
            if self.options.with_bzip2:
                self.cpp_info.components["pcre2-8"].requires.append("bzip2::bzip2")

