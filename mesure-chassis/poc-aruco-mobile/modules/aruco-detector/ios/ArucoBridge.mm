#import "ArucoBridge.h"

#import <opencv2/opencv.hpp>
#import <opencv2/objdetect.hpp>          // OpenCV >= 4.7: ArUco lives here
#import <opencv2/objdetect/aruco_detector.hpp>
#import <opencv2/objdetect/aruco_dictionary.hpp>

#import <CoreVideo/CoreVideo.h>
#import <Accelerate/Accelerate.h>

using namespace cv;

static cv::aruco::ArucoDetector *g_detector = nullptr;
static dispatch_once_t g_detectorOnce;

static cv::aruco::ArucoDetector *sharedDetector()
{
  dispatch_once(&g_detectorOnce, ^{
    cv::aruco::Dictionary dict = cv::aruco::getPredefinedDictionary(cv::aruco::DICT_4X4_50);
    cv::aruco::DetectorParameters params;
    // Slightly relaxed defaults work well for printed 50mm tags @ 1-2m
    params.adaptiveThreshWinSizeMin = 5;
    params.adaptiveThreshWinSizeMax = 35;
    params.adaptiveThreshWinSizeStep = 10;
    params.minMarkerPerimeterRate = 0.02;
    params.maxMarkerPerimeterRate = 4.0;
    params.cornerRefinementMethod = cv::aruco::CORNER_REFINE_SUBPIX;
    g_detector = new cv::aruco::ArucoDetector(dict, params);
  });
  return g_detector;
}

/// Converts a YUV (NV12/420f) or BGRA CVPixelBuffer to a single-channel
/// grayscale cv::Mat without copying when possible.
static bool pixelBufferToGray(CVPixelBufferRef pixelBuffer, cv::Mat &outGray)
{
  OSType fmt = CVPixelBufferGetPixelFormatType(pixelBuffer);
  CVPixelBufferLockBaseAddress(pixelBuffer, kCVPixelBufferLock_ReadOnly);

  bool ok = false;

  if (fmt == kCVPixelFormatType_420YpCbCr8BiPlanarFullRange ||
      fmt == kCVPixelFormatType_420YpCbCr8BiPlanarVideoRange) {
    // Plane 0 is luma (Y) – already grayscale.
    void *base = CVPixelBufferGetBaseAddressOfPlane(pixelBuffer, 0);
    size_t width  = CVPixelBufferGetWidthOfPlane(pixelBuffer, 0);
    size_t height = CVPixelBufferGetHeightOfPlane(pixelBuffer, 0);
    size_t stride = CVPixelBufferGetBytesPerRowOfPlane(pixelBuffer, 0);
    cv::Mat yPlane((int)height, (int)width, CV_8UC1, base, stride);
    outGray = yPlane.clone();   // detach from the locked buffer
    ok = !outGray.empty();
  } else if (fmt == kCVPixelFormatType_32BGRA) {
    void *base = CVPixelBufferGetBaseAddress(pixelBuffer);
    size_t width  = CVPixelBufferGetWidth(pixelBuffer);
    size_t height = CVPixelBufferGetHeight(pixelBuffer);
    size_t stride = CVPixelBufferGetBytesPerRow(pixelBuffer);
    cv::Mat bgra((int)height, (int)width, CV_8UC4, base, stride);
    cv::cvtColor(bgra, outGray, cv::COLOR_BGRA2GRAY);
    ok = !outGray.empty();
  }

  CVPixelBufferUnlockBaseAddress(pixelBuffer, kCVPixelBufferLock_ReadOnly);
  return ok;
}

@implementation ArucoBridge

+ (nullable NSDictionary *)detectMarkers:(CVPixelBufferRef)pixelBuffer
{
  if (pixelBuffer == NULL) return nil;

  cv::Mat gray;
  if (!pixelBufferToGray(pixelBuffer, gray)) {
    return @{
      @"markers": @[],
      @"frameWidth":  @(CVPixelBufferGetWidth(pixelBuffer)),
      @"frameHeight": @(CVPixelBufferGetHeight(pixelBuffer)),
    };
  }

  cv::aruco::ArucoDetector *det = sharedDetector();

  std::vector<std::vector<cv::Point2f>> markerCorners;
  std::vector<int> markerIds;
  std::vector<std::vector<cv::Point2f>> rejected;

  try {
    det->detectMarkers(gray, markerCorners, markerIds, rejected);
  } catch (cv::Exception &e) {
    NSLog(@"[ArucoBridge] OpenCV exception: %s", e.what());
    return @{
      @"markers": @[],
      @"frameWidth":  @(gray.cols),
      @"frameHeight": @(gray.rows),
    };
  }

  NSMutableArray *markers = [NSMutableArray arrayWithCapacity:markerIds.size()];
  for (size_t i = 0; i < markerIds.size(); i++) {
    NSMutableArray *corners = [NSMutableArray arrayWithCapacity:4];
    const auto &c = markerCorners[i];
    for (const auto &p : c) {
      [corners addObject:@{ @"x": @(p.x), @"y": @(p.y) }];
    }
    [markers addObject:@{
      @"id":      @(markerIds[i]),
      @"corners": corners,
    }];
  }

  return @{
    @"markers":     markers,
    @"frameWidth":  @(gray.cols),
    @"frameHeight": @(gray.rows),
  };
}

@end
