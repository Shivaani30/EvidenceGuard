import { useEffect, useRef, useState } from "react";

/** Lightweight CSS-3D forensic chamber: pointer/touch tilt + drag orbit. No WebGL needed. */
export function Hero3D() {
  const ref = useRef<HTMLDivElement>(null);
  const [rot, setRot] = useState({ x: -14, y: 42 });
  const drag = useRef<{ x: number; y: number; rx: number; ry: number } | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const move = (e: PointerEvent) => {
      if (drag.current) {
        setRot({ x: drag.current.rx - (e.clientY - drag.current.y) * 0.3, y: drag.current.ry + (e.clientX - drag.current.x) * 0.4 });
      } else if (!reduce) {
        const r = el.getBoundingClientRect();
        setRot({ x: -14 - ((e.clientY - r.top) / r.height - 0.5) * 14, y: 42 + ((e.clientX - r.left) / r.width - 0.5) * 24 });
      }
    };
    const up = () => (drag.current = null);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    return () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); };
  }, []);

  return (
    <div
      ref={ref}
      role="img"
      aria-label="A digital file separated into forensic layers — pixels, metadata, raw bytes and hash — with a scan plane passing through"
      className="relative mx-auto aspect-square w-full max-w-[460px] cursor-grab touch-none select-none active:cursor-grabbing"
      style={{ perspective: "1100px" }}
      onPointerDown={(e) => (drag.current = { x: e.clientX, y: e.clientY, rx: rot.x, ry: rot.y })}
    >
      <div className="absolute inset-[20%] rounded-full bg-primary/25 blur-3xl" />
      <div className="absolute inset-0 transition-transform duration-200 ease-out" style={{ transformStyle: "preserve-3d", transform: `rotateX(${rot.x}deg) rotateY(${rot.y}deg)` }}>
        {LAYERS.map((l, i) => (
          <div key={l.label} className="absolute left-1/2 top-1/2 -ml-[110px] -mt-[80px] h-[160px] w-[220px]"
            style={{ transform: `translateZ(${(i - 1.5) * 85}px)`, transformStyle: "preserve-3d" }}>
            <div className="relative size-full overflow-hidden rounded-sm border border-cyan/40 bg-background/50 backdrop-blur-[2px]">
              {l.body}
            </div>
            <span className="absolute -top-5 left-0 font-mono text-[10px] tracking-widest text-cyan/80">{String(i + 1).padStart(2, "0")} · {l.label}</span>
          </div>
        ))}
        {/* scan plane travelling through the layers */}
        <div className="anim-depth absolute left-1/2 top-1/2 -ml-[130px] -mt-[100px] h-[200px] w-[260px] border border-cyan/70 bg-cyan/10 glow" style={{ transformStyle: "preserve-3d" }} />
        {/* connecting threads */}
        {[[-110, -80], [110, -80], [-110, 80], [110, 80]].map(([x, y]) => (
          <div key={`${x}${y}`} className="absolute left-1/2 top-1/2 h-px w-[210px] origin-left bg-gradient-to-r from-cyan/0 via-cyan/50 to-cyan/0"
            style={{ transform: `translate3d(${x}px, ${y}px, -105px) rotateY(-90deg)` }} />
        ))}
      </div>
    </div>
  );
}

const HEX = "FF D8 FF E1 00 2A 45 78 69 66 00 00 4D 4D 00 2A 00 00 00 08 01 0F 00 02 00 00 00 06 00 00 00 9E 01 10 00 02 FF DB 00 43 00 08 06 06 07 06 05 08 07 07 07 09 09 08 0A 0C 14 0D 0C 0B 0B 0C 19 12";

const LAYERS = [
  { label: "SHA-256", body: (
    <div className="flex size-full flex-col justify-center gap-1 p-3 font-mono text-[10px] leading-tight text-success">
      <span>9f3a 71c0 be42 08d1</span><span>a6e9 33f7 5c21 d0b8</span><span>4e17 c9a2 f650 e21c</span>
      <span className="mt-1 text-[9px] text-muted-foreground">fingerprint · locked</span>
    </div>) },
  { label: "RAW BYTES", body: <p className="break-all p-2 font-mono text-[9px] leading-snug text-cyan/70">{HEX}</p> },
  { label: "METADATA", body: (
    <dl className="grid grid-cols-[auto_1fr] gap-x-2 p-3 font-mono text-[10px] text-muted-foreground">
      <dt>make</dt><dd className="text-foreground">—</dd><dt>software</dt><dd className="text-warning">edited?</dd>
      <dt>created</dt><dd className="text-foreground">2026:10:24</dd><dt>exif</dt><dd className="text-foreground">present</dd>
    </dl>) },
  { label: "PIXELS", body: (
    <div className="grid size-full grid-cols-11 grid-rows-8">
      {Array.from({ length: 88 }).map((_, i) => {
        const hot = (i % 11 > 6 && i % 11 < 10 && i > 22 && i < 66);
        return <div key={i} className={hot ? "bg-warning/70" : "bg-primary"} style={{ opacity: hot ? 0.4 + ((i * 7) % 5) / 10 : 0.12 + ((i * 13) % 9) / 22 }} />;
      })}
    </div>) },
];
