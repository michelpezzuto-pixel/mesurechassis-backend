#import <VisionCamera/FrameProcessorPlugin.h>
#import <VisionCamera/FrameProcessorPluginRegistry.h>

// Forward-declare the Swift class exposed to Obj-C
@class ArucoFrameProcessorPlugin;

// Pull in the auto-generated Swift header so we can reference the Swift class.
#if __has_include("ArucoDetector-Swift.h")
#import "ArucoDetector-Swift.h"
#else
@interface ArucoFrameProcessorPlugin : FrameProcessorPlugin
- (instancetype _Nonnull)initWithProxy:(VisionCameraProxyHolder * _Nonnull)proxy
                           withOptions:(NSDictionary * _Nullable)options;
@end
#endif

/// Registers the `detectAruco` frame processor with VisionCamera at app launch.
@interface ArucoFrameProcessorPluginLoader : NSObject
@end

@implementation ArucoFrameProcessorPluginLoader

+ (void)load
{
  [FrameProcessorPluginRegistry addFrameProcessorPlugin:@"detectAruco"
                                        withInitializer:^FrameProcessorPlugin * _Nonnull(VisionCameraProxyHolder * _Nonnull proxy, NSDictionary * _Nullable options) {
    return [[ArucoFrameProcessorPlugin alloc] initWithProxy:proxy withOptions:options];
  }];
}

@end
