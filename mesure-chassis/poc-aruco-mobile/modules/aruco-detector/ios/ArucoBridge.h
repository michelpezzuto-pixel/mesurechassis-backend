#import <Foundation/Foundation.h>
#import <CoreVideo/CoreVideo.h>

NS_ASSUME_NONNULL_BEGIN

/// Obj-C++ bridge between Swift (VisionCamera plugin) and OpenCV C++.
///
/// Exposed as plain Objective-C so it can be called from Swift without
/// dragging C++ headers into the Swift compilation units.
@interface ArucoBridge : NSObject

/// Detects ArUco DICT_4X4_50 markers in the given pixel buffer.
///
/// Returns a dictionary shaped like:
/// @code
/// {
///   "markers": [
///     { "id": @0, "corners": [ {"x":1,"y":2}, ...4 pts ] },
///     ...
///   ],
///   "frameWidth":  <NSNumber>,
///   "frameHeight": <NSNumber>
/// }
/// @endcode
/// Corners are returned in the original camera image coordinate system
/// (top-left origin), so the JS overlay can re-project them.
+ (nullable NSDictionary *)detectMarkers:(CVPixelBufferRef)pixelBuffer;

@end

NS_ASSUME_NONNULL_END
