import ExpoModulesCore

/// Minimal Expo module placeholder.
///
/// All useful work happens in `ArucoFrameProcessorPlugin` (registered with
/// VisionCamera at load-time via `+load` in the Objective-C glue file).
/// This module exists so Expo's autolinking picks up the iOS folder during
/// `expo prebuild` and embeds the native sources + OpenCV framework.
public class ArucoDetectorModule: Module {
  public func definition() -> ModuleDefinition {
    Name("ArucoDetector")

    Constants([
      "VERSION": "0.1.0",
      "DICTIONARY": "DICT_4X4_50",
    ])

    Function("isAvailable") { () -> Bool in
      return true
    }
  }
}
