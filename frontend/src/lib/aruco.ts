/**
 * ArUco detection wrapper — WEB / fallback stub.
 *
 * The real iOS implementation lives in `aruco.ios.ts` and is auto-selected by
 * Metro when bundling for iOS. This stub simply prevents bundle errors on web
 * and Android (where the native VisionCamera plugin isn't available).
 */
export type Corner = { x: number; y: number };
export type Marker = { id: number; corners: Corner[] };
export type ArucoResult = {
  markers: Marker[];
  frameWidth: number;
  frameHeight: number;
};

export const ARUCO_AVAILABLE = false;

// @ts-ignore - on non-iOS we never reach this code; the frame processor in
// scan-aruco.ios.tsx is only mounted on iOS.
export function detectAruco(_frame: unknown): ArucoResult {
  return { markers: [], frameWidth: 0, frameHeight: 0 };
}
