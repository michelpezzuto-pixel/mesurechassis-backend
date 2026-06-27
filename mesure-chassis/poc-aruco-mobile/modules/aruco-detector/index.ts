// Re-export the JS surface of the local module.
// The actual frame processor is invoked through VisionCameraProxy in
// src/lib/aruco-frame-processor.ts; this file exists so the native iOS code
// in ios/ gets picked up by `expo prebuild`.
export const ARUCO_DETECTOR_VERSION = '0.1.0';
export const ARUCO_DICTIONARY = 'DICT_4X4_50';
