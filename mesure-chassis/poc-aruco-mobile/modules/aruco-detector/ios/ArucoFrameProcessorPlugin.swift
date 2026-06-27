import Foundation
import VisionCamera
import AVFoundation
import CoreMedia

/// VisionCamera v4 frame processor plugin: detects ArUco DICT_4X4_50 markers
/// on every camera frame and returns their IDs + corners.
///
/// Heavy lifting (OpenCV C++) lives in `ArucoBridge.mm` to keep Swift clean.
@objc(ArucoFrameProcessorPlugin)
public class ArucoFrameProcessorPlugin: FrameProcessorPlugin {

  public override init(proxy: VisionCameraProxyHolder, options: [AnyHashable: Any]! = [:]) {
    super.init(proxy: proxy, options: options)
  }

  public override func callback(_ frame: Frame, withArguments arguments: [AnyHashable: Any]?) -> Any? {
    let buffer: CMSampleBuffer = frame.buffer

    guard let imageBuffer = CMSampleBufferGetImageBuffer(buffer) else {
      return [
        "markers": [Any](),
        "frameWidth": frame.width,
        "frameHeight": frame.height,
      ]
    }

    let result = ArucoBridge.detectMarkers(imageBuffer)

    return [
      "markers": result?["markers"] ?? [Any](),
      "frameWidth": result?["frameWidth"] ?? frame.width,
      "frameHeight": result?["frameHeight"] ?? frame.height,
    ]
  }
}
