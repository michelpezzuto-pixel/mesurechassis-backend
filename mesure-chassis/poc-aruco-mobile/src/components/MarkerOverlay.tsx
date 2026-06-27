import React, { useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Polygon, Text as SvgText, Rect } from 'react-native-svg';

import type { Marker } from '../lib/aruco-frame-processor';

type Props = {
  markers: Marker[];
  frameWidth: number;
  frameHeight: number;
  viewWidth: number;
  viewHeight: number;
};

/**
 * Draws ArUco bounding boxes + IDs over the camera preview.
 *
 * Vision-Camera v4 renders the preview in "cover" mode by default, meaning the
 * frame is scaled to fill the view (with center-crop). We replicate this
 * mapping here so the polygons align with what the user sees on screen.
 */
export default function MarkerOverlay({
  markers,
  frameWidth,
  frameHeight,
  viewWidth,
  viewHeight,
}: Props) {
  const { scale, offsetX, offsetY } = useMemo(() => {
    if (
      frameWidth === 0 ||
      frameHeight === 0 ||
      viewWidth === 0 ||
      viewHeight === 0
    ) {
      return { scale: 1, offsetX: 0, offsetY: 0 };
    }
    // Frames from iOS back camera are landscape (e.g. 1920x1080) but the view
    // is portrait. The preview applies a 90° rotation internally; we therefore
    // swap frame dimensions before computing the "cover" scale.
    const fw = frameHeight; // after virtual rotation
    const fh = frameWidth;
    const sx = viewWidth / fw;
    const sy = viewHeight / fh;
    const s = Math.max(sx, sy); // cover
    return {
      scale: s,
      offsetX: (viewWidth - fw * s) / 2,
      offsetY: (viewHeight - fh * s) / 2,
    };
  }, [frameWidth, frameHeight, viewWidth, viewHeight]);

  const transform = (x: number, y: number) => {
    // Apply 90° CW rotation: (x, y) in landscape frame -> (frameHeight - y, x)
    // in the virtually-rotated portrait frame.
    const rx = frameHeight - y;
    const ry = x;
    return {
      x: rx * scale + offsetX,
      y: ry * scale + offsetY,
    };
  };

  if (viewWidth === 0 || viewHeight === 0) return null;

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Svg width={viewWidth} height={viewHeight}>
        {markers.map((m, i) => {
          const pts = m.corners.map((c) => {
            const t = transform(c.x, c.y);
            return `${t.x},${t.y}`;
          });
          const cx =
            m.corners.reduce((s, c) => s + transform(c.x, c.y).x, 0) /
            m.corners.length;
          const cy =
            m.corners.reduce((s, c) => s + transform(c.x, c.y).y, 0) /
            m.corners.length;
          return (
            <React.Fragment key={`${m.id}-${i}`}>
              <Polygon
                points={pts.join(' ')}
                fill="rgba(34,211,238,0.15)"
                stroke="#22d3ee"
                strokeWidth={3}
              />
              <Rect
                x={cx - 22}
                y={cy - 14}
                width={44}
                height={26}
                rx={6}
                ry={6}
                fill="rgba(0,0,0,0.75)"
              />
              <SvgText
                x={cx}
                y={cy + 5}
                fill="#22d3ee"
                fontSize={16}
                fontWeight="bold"
                textAnchor="middle"
              >
                {`#${m.id}`}
              </SvgText>
            </React.Fragment>
          );
        })}
      </Svg>
    </View>
  );
}
