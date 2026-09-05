"""Particle starfield — Canvas 2D animation for hero backgrounds."""


def _starfield_js(canvas_id: str) -> str:
    """Return a <script> that animates a Canvas 2D particle starfield."""
    return f"""
<script>
(function() {{
    var canvas = document.getElementById('{canvas_id}');
    if (!canvas) return;
    var ctx = canvas.getContext('2d');
    var w, h, particles = [], mouseX = -1000, mouseY = -1000, frame = 0;

    function resize() {{
        var rect = canvas.parentElement.getBoundingClientRect();
        w = canvas.width = rect.width;
        h = canvas.height = rect.height;
    }}
    resize();
    window.addEventListener('resize', resize);

    canvas.parentElement.addEventListener('mousemove', function(e) {{
        var rect = canvas.parentElement.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;
    }});
    canvas.parentElement.addEventListener('mouseleave', function() {{ mouseX = -1000; mouseY = -1000; }});

    var COUNT = Math.min(70, Math.floor(w * h / 15000));
    for (var i = 0; i < COUNT; i++) {{
        var isBright = Math.random() < 0.15;
        particles.push({{
            x: Math.random() * w, y: Math.random() * h,
            vx: (Math.random() - 0.5) * 0.25, vy: (Math.random() - 0.5) * 0.25,
            r: isBright ? 1.5 + Math.random() * 1.5 : 0.5 + Math.random() * 1,
            baseAlpha: isBright ? 0.6 + Math.random() * 0.4 : 0.15 + Math.random() * 0.35,
            twinkleSpeed: 0.005 + Math.random() * 0.015,
            twinklePhase: Math.random() * Math.PI * 2,
            color: isBright ? (Math.random() < 0.5 ? '#818cf8' : '#a5b4fc') : '#94a3b8',
            pulseSize: isBright ? 1 + Math.random() * 2 : 0
        }});
    }}

    function animate() {{
        ctx.clearRect(0, 0, w, h);
        frame++;
        for (var i = 0; i < particles.length; i++) {{
            var p = particles[i];
            p.x += p.vx; p.y += p.vy;
            var dx = p.x - mouseX, dy = p.y - mouseY;
            var dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 100 && dist > 0) {{
                var force = (100 - dist) / 100 * 0.6;
                p.vx += (dx / dist) * force; p.vy += (dy / dist) * force;
            }}
            p.vx *= 0.995; p.vy *= 0.995;
            if (p.x < -10) p.x = w + 10; if (p.x > w + 10) p.x = -10;
            if (p.y < -10) p.y = h + 10; if (p.y > h + 10) p.y = -10;
            var alpha = p.baseAlpha * (0.5 + 0.5 * Math.sin(frame * p.twinkleSpeed + p.twinklePhase));
            var drawR = p.r + p.pulseSize * Math.sin(frame * 0.02 + p.twinklePhase) * 0.5;
            ctx.beginPath(); ctx.arc(p.x, p.y, Math.max(drawR, 0.5), 0, Math.PI * 2);
            ctx.fillStyle = p.color; ctx.globalAlpha = alpha; ctx.fill();
            if (p.r > 1.2) {{
                ctx.beginPath(); ctx.arc(p.x, p.y, drawR * 3, 0, Math.PI * 2);
                var grd = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, drawR * 3);
                grd.addColorStop(0, p.color); grd.addColorStop(1, 'transparent');
                ctx.fillStyle = grd; ctx.globalAlpha = alpha * 0.12; ctx.fill();
            }}
        }}
        ctx.globalAlpha = 1;
        for (var i = 0; i < particles.length; i++) {{
            for (var j = i + 1; j < particles.length; j++) {{
                var dx = particles[i].x - particles[j].x;
                var dy = particles[i].y - particles[j].y;
                var dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 90) {{
                    ctx.beginPath(); ctx.moveTo(particles[i].x, particles[i].y);
                    ctx.lineTo(particles[j].x, particles[j].y);
                    ctx.strokeStyle = 'rgba(99,102,241,' + (0.07 * (1 - dist / 90)) + ')';
                    ctx.lineWidth = 0.5; ctx.stroke();
                }}
            }}
        }}
        ctx.globalAlpha = 1;
        requestAnimationFrame(animate);
    }}
    animate();
}})();
</script>
"""


def particle_starfield(container_id: str = "hero-starfield") -> str:
    """Return HTML for an embedded Canvas 2D particle starfield.

    The returned HTML includes a <canvas> element and a <script> that
    animates twinkling particles with mouse repulsion and connection lines.
    """
    canvas_id = f"canvas-{container_id}"
    return f"""
<canvas id="{canvas_id}" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:0;"></canvas>
{_starfield_js(canvas_id)}
"""


# ══════════════════════════════════════════════════════════════════════════════
# HTML COMPONENT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

