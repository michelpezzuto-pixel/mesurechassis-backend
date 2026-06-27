import { VisionCameraProxy, type Frame } from 'react-native-vision-camera';

export type Corner = { x: number; y: number };
export type Marker = {
  id: number;
  corners: Corner[]; // 4 corners (TL, TR, BR, BL in image coords)
};
export type ArucoResult = {
  markers: Marker[];
  frameWidth: number;
  frameHeight: number;
};

const plugin = VisionCameraProxy.initFrameProcessorPlugin('detectAruco', {});

/**
 * Worklet-safe wrapper around the native ArUco frame processor plugin.
 * Detects DICT_4X4_50 markers in the given camera frame.
 */
export function detectAruco(frame: Frame): ArucoResult {
  'worklet';
  if (plugin == null) {
    throw new Error(
      '[poc-aruco] Native plugin "detectAruco" not found. Rebuild the dev client.',
    );
  }
  const raw = plugin.call(frame) as
    | undefined
    | {
        markers?: { id: number; corners: { x: number; y: number }[] }[];
        frameWidth?: number;
        frameHeight?: number;
      };
  return {
    markers: raw?.markers ?? [],
    frameWidth: raw?.frameWidth ?? frame.width,
    frameHeight: raw?.frameHeight ?? frame.height,
  };
}
