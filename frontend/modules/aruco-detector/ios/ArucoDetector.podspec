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

  # OpenCV (auto-downloaded by CocoaPods at install time, so we don't ship
  # the 549 MB framework with our source tree).
  # ArUco moved into core in OpenCV 4.7+, so `opencv_contrib` is NOT required.
  #
  # IMPORTANT: we deliberately DO NOT use `s.vendored_frameworks` here.
  # Combining `s.static_framework = true` + `s.vendored_frameworks` makes
  # CocoaPods re-export *all* headers of the vendored framework as PUBLIC
  # headers of the consuming static framework — and OpenCV has multiple
  # nested headers with identical basenames (e.g. core/types_c.h AND
  # imgproc/types_c.h, *.legacy/constants_c.h in 4 sub-modules, *.hal/
  # interface.h in 3 sub-modules) which collide on the flat output
  # `ArucoDetector.framework/Headers/` directory and break the iOS archive
  # with "Multiple commands produce" errors.
  #
  # Instead we keep opencv2.framework on disk via `preserve_paths` and link
  # to it manually via FRAMEWORK_SEARCH_PATHS + -framework opencv2. OpenCV
  # ships its own module map, so `#import <opencv2/opencv.hpp>` from
  # ArucoBridge.mm still resolves correctly without us having to merge or
  # copy any of its headers.
  s.preserve_paths = 'Frameworks/opencv2.framework'
  s.frameworks     = 'AVFoundation', 'CoreMedia', 'CoreVideo', 'Accelerate'
  s.libraries      = 'c++'

  s.xcconfig = {
    'FRAMEWORK_SEARCH_PATHS' => '"$(PODS_TARGET_SRCROOT)/Frameworks" $(inherited)',
    'OTHER_LDFLAGS'          => '-framework opencv2 $(inherited)',
    'HEADER_SEARCH_PATHS'    => '"$(PODS_TARGET_SRCROOT)/Frameworks/opencv2.framework/Headers" $(inherited)',
  }

  # Fetch opencv2.framework once if it's not already vendored. Runs during
  # `pod install` (i.e. on the EAS build server, not on dev machines / web
  # preview deployments — that's intentional, it keeps the deployable small).
  s.prepare_command = <<-CMD
    set -e
    FW_DIR="$(pwd)/Frameworks/opencv2.framework"
    if [ ! -d "$FW_DIR" ]; then
      echo "[ArucoDetector] Downloading opencv2.framework 4.10.0 (~155 MB compressed)..."
      mkdir -p "$(pwd)/Frameworks"
      TMP_ZIP="$(mktemp -t opencv.XXXXXX.zip)"
      curl -L --fail --silent --show-error \\
        -o "$TMP_ZIP" \\
        "https://github.com/opencv/opencv/releases/download/4.10.0/opencv-4.10.0-ios-framework.zip"
      unzip -q "$TMP_ZIP" -d "$(pwd)/Frameworks"
      rm -f "$TMP_ZIP"
      echo "[ArucoDetector] opencv2.framework installed."
    else
      echo "[ArucoDetector] opencv2.framework already present, skipping download."
    fi
  CMD

  s.pod_target_xcconfig = {
    'DEFINES_MODULE'          => 'YES',
    'CLANG_CXX_LANGUAGE_STANDARD' => 'c++17',
    'GCC_PREPROCESSOR_DEFINITIONS' => 'OPENCV_DISABLE_DEPRECATED_DEPRECATION=1',
    'SWIFT_OBJC_INTEROP_MODE'  => 'objcxx'
  }

  # IMPORTANT: do NOT use `**/*` recursive globs here — that would pull in
  # the hundreds of nested OpenCV headers from Frameworks/opencv2.framework
  # (e.g. imgcodecs/legacy/constants_c.h, photo/legacy/constants_c.h, ...)
  # which collide on a flat output `Headers/` directory and break the build
  # with "Multiple commands produce" errors. OpenCV's headers are already
  # exposed through `s.vendored_frameworks` and its own module map.
  s.source_files = '*.{h,m,mm,swift}'
  s.public_header_files = 'ArucoBridge.h'
end
