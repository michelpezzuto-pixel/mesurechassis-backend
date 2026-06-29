import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Polygon, Rect, Text as SvgText } from 'react-native-svg';

import type { Marker } from '../lib/aruco';

type Props = {
  markers: Marker[];
  frameWidth: number;
  frameHeight: number;
  viewWidth: number;
  viewHeight: number;
};

/**
 * Cyan bounding boxes + IDs drawn over the camera preview.
 * iPhone back-camera frames arrive in landscape (e.g. 1920x1080); the preview
 * is rotated 90° to portrait and scaled "cover". We replicate that mapping
 * here so the polygons line up with what the user sees on screen.
 */
export default function MarkerOverlay({
  markers, frameWidth, frameHeight, viewWidth, viewHeight,
}: Props) {
  if (!viewWidth || !viewHeight) return null;

  // After virtual 90° rotation, the portrait frame dims are (frameHeight, frameWidth).
  const fw = frameHeight || 1;
  const fh = frameWidth || 1;
  const scale = Math.max(viewWidth / fw, viewHeight / fh);
  const offX = (viewWidth - fw * scale) / 2;
  const offY = (viewHeight - fh * scale) / 2;

  const project = (x: number, y: number) => ({
    x: (frameHeight - y) * scale + offX,
    y: x * scale + offY,
  });

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Svg width={viewWidth} height={viewHeight}>
        {markers.map((m, i) => {
          const pts = m.corners.map(c => {
            const p = project(c.x, c.y);
            return `${p.x},${p.y}`;
          });
          const cx = m.corners.reduce((s, c) => s + project(c.x, c.y).x, 0) / m.corners.length;
          const cy = m.corners.reduce((s, c) => s + project(c.x, c.y).y, 0) / m.corners.length;
          return (
            <React.Fragment key={`${m.id}-${i}`}>
              <Polygon
                points={pts.join(' ')}
                fill="rgba(34,211,238,0.18)"
                stroke="#22d3ee"
                strokeWidth={3}
              />
              <Rect x={cx - 24} y={cy - 14} width={48} height={28} rx={6} ry={6} fill="rgba(0,0,0,0.78)" />
              <SvgText x={cx} y={cy + 6} fill="#22d3ee" fontSize={17} fontWeight="bold" textAnchor="middle">
                {`#${m.id}`}
              </SvgText>
            </React.Fragment>
          );
        })}
      </Svg>
    </View>
  );
}
