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
  s.vendored_frameworks = 'Frameworks/opencv2.framework'
  s.frameworks = 'AVFoundation', 'CoreMedia', 'CoreVideo', 'Accelerate'
  s.libraries  = 'c++'

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

  s.source_files = '**/*.{h,m,mm,swift}'
  s.public_header_files = '**/*.h'
end
