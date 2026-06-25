import { useRef } from 'react';

interface ResizeHandleProps {
  /** Called with the horizontal pixel delta as the user drags. */
  onResize: (deltaX: number) => void;
  /** Double-click to reset to the default width. */
  onReset?: () => void;
  onDragStart?: () => void;
  onDragEnd?: () => void;
}

/** A thin vertical drag handle for resizing an adjacent panel (VS Code style). */
export function ResizeHandle({ onResize, onReset, onDragStart, onDragEnd }: ResizeHandleProps) {
  const lastX = useRef(0);
  const dragging = useRef(false);

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    dragging.current = true;
    lastX.current = e.clientX;
    e.currentTarget.setPointerCapture(e.pointerId);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    onDragStart?.();
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    const dx = e.clientX - lastX.current;
    if (dx !== 0) {
      lastX.current = e.clientX;
      onResize(dx);
    }
  };

  const endDrag = (e: React.PointerEvent<HTMLDivElement>) => {
    if (!dragging.current) return;
    dragging.current = false;
    try {
      e.currentTarget.releasePointerCapture(e.pointerId);
    } catch {
      /* pointer already released */
    }
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    onDragEnd?.();
  };

  return (
    <div
      className="resize-handle"
      role="separator"
      aria-orientation="vertical"
      title="Drag to resize · double-click to reset"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onDoubleClick={onReset}
    />
  );
}
