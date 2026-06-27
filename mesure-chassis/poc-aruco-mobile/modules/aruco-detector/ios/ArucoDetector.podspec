require 'json'

package = JSON.parse(File.read(File.join(__dir__, '..', 'package.json')))

Pod::Spec.new do |s|
  s.name           = 'ArucoDetector'
  s.version        = package['version']
  s.summary        = package['description']
  s.description    = package['description']
  s.author         = 'MesureChassis'
  s.homepage       = 'https://github.com/local/poc-aruco'
  s.license        = 'MIT'
  s.platforms      = { :ios => '15.1' }
  s.swift_version  = '5.9'
  s.source         = { :git => '' }

  s.static_framework = true
  s.requires_arc   = true

  s.dependency 'ExpoModulesCore'
  s.dependency 'VisionCamera'

  # OpenCV (vendored). Place opencv2.framework in ./Frameworks/ before prebuild.
  # ArUco moved into core in OpenCV 4.7+, so contrib is NOT required.
  s.vendored_frameworks = 'Frameworks/opencv2.framework'
  s.frameworks = 'AVFoundation', 'CoreMedia', 'CoreVideo', 'Accelerate'
  s.libraries  = 'c++'

  s.pod_target_xcconfig = {
    'DEFINES_MODULE'          => 'YES',
    'CLANG_CXX_LANGUAGE_STANDARD' => 'c++17',
    'GCC_PREPROCESSOR_DEFINITIONS' => 'OPENCV_DISABLE_DEPRECATED_DEPRECATION=1',
    'SWIFT_OBJC_INTEROP_MODE'  => 'objcxx'
  }

  s.source_files = '**/*.{h,m,mm,swift}'
  s.public_header_files = '**/*.h'
end
