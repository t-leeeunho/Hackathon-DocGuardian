import { useEffect, useRef } from 'react';
import { useReducedMotion } from '../../hooks/useReducedMotion';

interface Particle {
  x: number;
  y: number;
  size: number;
  opacity: number;
  opacitySpeed: number;
  opacityMin: number;
  opacityMax: number;
  color: string;
  // Shooting star fields
  isShooting: boolean;
  shootDx: number;
  shootDy: number;
  shootProgress: number;
  shootDuration: number;
  shootCooldown: number;
}

const COLORS = [
  '#ffffff',
  '#ffffff',
  '#ffffff',
  '#c4b5fd', // soft purple
  '#93c5fd', // soft blue
  '#ffffff',
  '#e0e7ff',
];

function createParticle(width: number, height: number): Particle {
  const opacityMin = 0.05 + Math.random() * 0.15;
  const opacityMax = 0.5 + Math.random() * 0.4;
  return {
    x: Math.random() * width,
    y: Math.random() * height,
    size: 0.4 + Math.random() * 2.2,
    opacity: opacityMin + Math.random() * (opacityMax - opacityMin),
    opacitySpeed: 0.003 + Math.random() * 0.012,
    opacityMin,
    opacityMax,
    color: COLORS[Math.floor(Math.random() * COLORS.length)],
    isShooting: false,
    shootDx: 0,
    shootDy: 0,
    shootProgress: 0,
    shootDuration: 0,
    shootCooldown: Math.random() * 600,
  };
}

export function SparkleBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const reducedMotion = useReducedMotion();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const resize = () => {
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
      // Re-create particles on resize
      particlesRef.current = Array.from({ length: 200 }, () =>
        createParticle(canvas.width, canvas.height),
      );
    };

    resize();
    window.addEventListener('resize', resize);

    if (reducedMotion) {
      // Static star field only
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (const p of particlesRef.current) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = (p.opacityMin + p.opacityMax) / 2;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
      return () => window.removeEventListener('resize', resize);
    }

    let shootingStarTimer = 0;

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      shootingStarTimer++;

      for (const p of particlesRef.current) {
        // Opacity breathing
        p.opacity += p.opacitySpeed;
        if (p.opacity >= p.opacityMax) {
          p.opacity = p.opacityMax;
          p.opacitySpeed = -Math.abs(p.opacitySpeed);
        } else if (p.opacity <= p.opacityMin) {
          p.opacity = p.opacityMin;
          p.opacitySpeed = Math.abs(p.opacitySpeed);
        }

        // Shooting star logic
        if (!p.isShooting) {
          p.shootCooldown--;
          if (p.shootCooldown <= 0 && shootingStarTimer > 120 && Math.random() < 0.0008) {
            p.isShooting = true;
            const angle = (Math.random() * Math.PI) / 4 + Math.PI / 6;
            const speed = 6 + Math.random() * 10;
            p.shootDx = Math.cos(angle) * speed;
            p.shootDy = Math.sin(angle) * speed;
            p.shootProgress = 0;
            p.shootDuration = 30 + Math.random() * 30;
            shootingStarTimer = 0;
          }
        }

        if (p.isShooting) {
          p.shootProgress++;
          const tailX = p.x - p.shootDx * 4;
          const tailY = p.y - p.shootDy * 4;
          const grad = ctx.createLinearGradient(tailX, tailY, p.x, p.y);
          grad.addColorStop(0, 'rgba(255,255,255,0)');
          grad.addColorStop(1, `rgba(255,255,255,${p.opacity})`);
          ctx.beginPath();
          ctx.moveTo(tailX, tailY);
          ctx.lineTo(p.x, p.y);
          ctx.strokeStyle = grad;
          ctx.lineWidth = p.size * 0.8;
          ctx.stroke();

          p.x += p.shootDx;
          p.y += p.shootDy;

          if (p.shootProgress >= p.shootDuration || p.x > w + 50 || p.y > h + 50) {
            p.isShooting = false;
            p.x = Math.random() * w;
            p.y = Math.random() * h;
            p.shootCooldown = 200 + Math.random() * 400;
          }
        } else {
          // Regular star
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size / 2, 0, Math.PI * 2);
          ctx.fillStyle = p.color;
          ctx.globalAlpha = p.opacity;
          ctx.fill();
          ctx.globalAlpha = 1;
        }
      }

      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);

    return () => {
      cancelAnimationFrame(animRef.current);
      window.removeEventListener('resize', resize);
    };
  }, [reducedMotion]);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  );
}
