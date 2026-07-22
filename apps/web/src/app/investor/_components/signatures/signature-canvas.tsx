'use client';

import { useCallback, useEffect, useRef } from 'react';

export interface SignatureCanvasProps {
  onChange: (dataUrl: string | null) => void;
  ariaLabel?: string;
}

export function SignatureCanvas({ onChange, ariaLabel = 'Draw your signature' }: SignatureCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);

  const getPoint = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    if ('touches' in e) {
      const touch = e.touches[0];
      if (!touch) return null;
      return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
    }
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }, []);

  const startDraw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    drawing.current = true;
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    const pt = getPoint(e);
    if (!ctx || !pt) return;
    ctx.beginPath();
    ctx.moveTo(pt.x, pt.y);
  }, [getPoint]);

  const draw = useCallback((e: React.MouseEvent | React.TouchEvent) => {
    if (!drawing.current) return;
    e.preventDefault();
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    const pt = getPoint(e);
    if (!ctx || !pt) return;
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.strokeStyle = '#1a1a2e';
    ctx.lineTo(pt.x, pt.y);
    ctx.stroke();
  }, [getPoint]);

  const endDraw = useCallback(() => {
    drawing.current = false;
    const canvas = canvasRef.current;
    if (canvas) onChange(canvas.toDataURL('image/png'));
  }, [onChange]);

  const clear = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    onChange(null);
  }, [onChange]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = canvas.offsetWidth * 2;
    canvas.height = canvas.offsetHeight * 2;
    const ctx = canvas.getContext('2d');
    if (ctx) ctx.scale(2, 2);
  }, []);

  return (
    <div className="inv-sig__canvas-wrap">
      <canvas
        ref={canvasRef}
        className="inv-sig__canvas"
        aria-label={ariaLabel}
        onMouseDown={startDraw}
        onMouseMove={draw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
        onTouchStart={startDraw}
        onTouchMove={draw}
        onTouchEnd={endDraw}
      />
      <button type="button" className="inv-docs__btn inv-docs__btn--ghost" onClick={clear}>
        Clear
      </button>
      <p className="inv-sig__canvas-alt">
        Keyboard alternative: use typed signature option in the previous step.
      </p>
    </div>
  );
}
