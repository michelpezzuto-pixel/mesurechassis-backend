import { VisionCameraProxy, type Frame } from 'react-native-vision-camera';

export type Corner = { x: number; y: number };
export type Marker = { id: number; corners: Corner[] };
export type ArucoResult = {
  markers: Marker[];
  frameWidth: number;
  frameHeight: number;
};

const plugin = VisionCameraProxy.initFrameProcessorPlugin('detectAruco', {});
export const ARUCO_AVAILABLE = plugin != null;

/**
 * Worklet-safe ArUco DICT_4X4_50 detector wrapper.
 * Returns marker IDs + corner coordinates (image-space, top-left origin).
 */
export function detectAruco(frame: Frame): ArucoResult {
  'worklet';
  if (plugin == null) {
    return { markers: [], frameWidth: frame.width, frameHeight: frame.height };
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
