"use client";

import React, { useEffect, useRef } from "react";
import ReactDOM from "react-dom/client";

interface Props {
  map: google.maps.Map | null;
  position: { lat: number; lng: number };
  children: React.ReactNode;
  zIndex?: number;
}

export default function CustomHtmlMarker({ map, position, children, zIndex = 1 }: Props) {
  const overlayRef   = useRef<google.maps.OverlayView | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const rootRef      = useRef<ReactDOM.Root | null>(null);

  useEffect(() => {
    if (!map) return;

    const container = document.createElement("div");
    container.style.position = "absolute";
    container.style.zIndex   = String(zIndex);
    containerRef.current = container;

    class HtmlOverlay extends google.maps.OverlayView {
      onAdd() {
        this.getPanes()!.overlayMouseTarget.appendChild(container);
      }
      draw() {
        const proj = this.getProjection();
        if (!proj) return;
        const point = proj.fromLatLngToDivPixel(
          new google.maps.LatLng(position.lat, position.lng)
        );
        if (point) {
          container.style.left      = `${point.x}px`;
          container.style.top       = `${point.y}px`;
          container.style.transform = "translate(-50%, -50%)";
        }
      }
      onRemove() {
        container.remove();
      }
    }

    const overlay = new HtmlOverlay();
    overlay.setMap(map);
    overlayRef.current = overlay;

    const root = ReactDOM.createRoot(container);
    rootRef.current = root;
    root.render(<>{children}</>);

    return () => {
      root.unmount();
      overlay.setMap(null);
    };
  }, [map]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    rootRef.current?.render(<>{children}</>);
  }, [children]);

  useEffect(() => {
    overlayRef.current?.draw();
  }, [position.lat, position.lng]);

  return null;
}
