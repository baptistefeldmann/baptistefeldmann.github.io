(() => {
  const root = document.documentElement;

  /* ---------- Thème clair / sombre ---------- */
  const storedTheme = () => {
    try { return localStorage.getItem('theme'); } catch (e) { return null; }
  };

  document.querySelector('.theme-toggle')?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch (e) { /* stockage indisponible */ }
    redrawAll();
  });

  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (storedTheme()) return;
    root.dataset.theme = e.matches ? 'dark' : 'light';
    redrawAll();
  });

  /* ---------- Relief procédural (bruit de valeur fractal) ---------- */
  function makeField(seed, scale) {
    const hash = (x, y) => {
      let h = seed ^ Math.imul(x, 374761393) ^ Math.imul(y, 668265263);
      h = Math.imul(h ^ (h >>> 13), 1274126177);
      h ^= h >>> 16;
      return (h >>> 0) / 4294967296;
    };
    const smooth = (t) => t * t * (3 - 2 * t);
    const noise = (x, y) => {
      const ix = Math.floor(x), iy = Math.floor(y);
      const fx = smooth(x - ix), fy = smooth(y - iy);
      const a = hash(ix, iy), b = hash(ix + 1, iy);
      const c = hash(ix, iy + 1), d = hash(ix + 1, iy + 1);
      return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
    };
    return (px, py) => {
      let x = px / scale, y = py / scale, amp = 1, sum = 0, norm = 0;
      for (let o = 0; o < 4; o++) {
        sum += amp * noise(x, y);
        norm += amp;
        amp *= 0.5;
        x = x * 2.03 + 17.3;
        y = y * 2.03 + 5.7;
      }
      return sum / norm;
    };
  }

  /* ---------- Courbes de niveau (marching squares) ---------- */
  // Arêtes : 0 = haut, 1 = droite, 2 = bas, 3 = gauche
  const SEGMENTS = [
    [], [3, 2], [2, 1], [3, 1], [0, 1], [3, 0, 2, 1], [0, 2], [3, 0],
    [3, 0], [0, 2], [0, 1, 3, 2], [0, 1], [3, 1], [2, 1], [3, 2], [],
  ];

  function march(ctx, g, cols, rows, stride, cell, L) {
    for (let j = 0; j < rows; j++) {
      const y0 = j * cell;
      for (let i = 0; i < cols; i++) {
        const k = j * stride + i;
        const a = g[k], b = g[k + 1], c = g[k + stride + 1], d = g[k + stride];
        const idx = ((a > L) << 3) | ((b > L) << 2) | ((c > L) << 1) | (d > L);
        if (idx === 0 || idx === 15) continue;
        const x0 = i * cell;
        const pt = (e) => {
          switch (e) {
            case 0: return [x0 + ((L - a) / (b - a)) * cell, y0];
            case 1: return [x0 + cell, y0 + ((L - b) / (c - b)) * cell];
            case 2: return [x0 + ((L - d) / (c - d)) * cell, y0 + cell];
            default: return [x0, y0 + ((L - a) / (d - a)) * cell];
          }
        };
        const s = SEGMENTS[idx];
        for (let n = 0; n < s.length; n += 2) {
          const p = pt(s[n]), q = pt(s[n + 1]);
          ctx.moveTo(p[0], p[1]);
          ctx.lineTo(q[0], q[1]);
        }
      }
    }
  }

  const hexToRgb = (hex) => {
    const m = hex.replace('#', '');
    return [0, 2, 4].map((i) => parseInt(m.slice(i, i + 2), 16));
  };

  function draw(canvas) {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const ctx = canvas.getContext('2d');
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    const seed = Number(canvas.dataset.seed) || 1;
    const scale = Number(canvas.dataset.scale) || 300;
    const cell = Number(canvas.dataset.cell) || 7;
    const nLevels = Number(canvas.dataset.levels) || 18;
    const field = makeField(seed, scale);

    const cols = Math.ceil(w / cell), rows = Math.ceil(h / cell), stride = cols + 1;
    const grid = new Float32Array(stride * (rows + 1));
    let min = Infinity, max = -Infinity;
    for (let j = 0; j <= rows; j++) {
      for (let i = 0; i <= cols; i++) {
        const v = field(i * cell, j * cell);
        grid[j * stride + i] = v;
        if (v < min) min = v;
        if (v > max) max = v;
      }
    }
    const range = max - min || 1;
    const waterLevel = min + range * 0.14;

    const css = getComputedStyle(root);
    const contourColor = css.getPropertyValue('--contour').trim();
    const waterColor = css.getPropertyValue('--water').trim();

    // Plans d'eau : image basse résolution lissée à l'agrandissement
    const off = document.createElement('canvas');
    off.width = stride;
    off.height = rows + 1;
    const octx = off.getContext('2d');
    const img = octx.createImageData(stride, rows + 1);
    const [wr, wg, wb] = hexToRgb(waterColor);
    for (let k = 0; k < grid.length; k++) {
      if (grid[k] < waterLevel) {
        img.data[k * 4] = wr;
        img.data[k * 4 + 1] = wg;
        img.data[k * 4 + 2] = wb;
        img.data[k * 4 + 3] = 46;
      }
    }
    octx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(off, -cell / 2, -cell / 2, stride * cell, (rows + 1) * cell);

    // Courbes de niveau (maîtresse toutes les 5)
    ctx.lineCap = ctx.lineJoin = 'round';
    ctx.strokeStyle = contourColor;
    for (let l = 1; l <= nLevels; l++) {
      const L = min + (range * l) / (nLevels + 1);
      if (L < waterLevel) continue;
      const major = l % 5 === 0;
      ctx.beginPath();
      march(ctx, grid, cols, rows, stride, cell, L);
      ctx.globalAlpha = major ? 0.85 : 0.42;
      ctx.lineWidth = major ? 1.3 : 0.7;
      ctx.stroke();
    }

    // Trait de côte
    ctx.beginPath();
    march(ctx, grid, cols, rows, stride, cell, waterLevel);
    ctx.strokeStyle = waterColor;
    ctx.globalAlpha = 0.75;
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.globalAlpha = 1;

    canvas._topo = { field, min, range };
  }

  const canvases = [...document.querySelectorAll('canvas.topo')];
  const pending = new Set();
  function schedule(c) {
    if (pending.has(c)) return;
    pending.add(c);
    requestAnimationFrame(() => { pending.delete(c); draw(c); });
  }
  function redrawAll() { canvases.forEach(schedule); }

  const ro = new ResizeObserver((entries) => entries.forEach((e) => schedule(e.target)));
  canvases.forEach((c) => ro.observe(c));
  document.fonts?.ready.then(redrawAll);

  /* ---------- Lecture des coordonnées sous le curseur ---------- */
  const hero = document.querySelector('.hero');
  if (hero) {
    const topo = hero.querySelector('canvas.topo');
    const out = (k) => hero.querySelector(`[data-readout="${k}"]`);
    const lat = out('lat'), lon = out('lon'), alt = out('alt');
    const en = root.lang === 'en';
    const west = en ? 'W' : 'O', altLabel = en ? 'Elev.' : 'Alt.';
    hero.addEventListener('pointermove', (e) => {
      const r = topo.getBoundingClientRect();
      const x = e.clientX - r.left, y = e.clientY - r.top;
      lat.textContent = `${(48.16 - (y / r.height) * 0.09).toFixed(4)}° N`;
      lon.textContent = `${(1.76 - (x / r.width) * 0.16).toFixed(4)}° ${west}`;
      const t = topo._topo;
      if (t) alt.textContent = `${altLabel} ${Math.round(20 + ((t.field(x, y) - t.min) / t.range) * 240)} m`;
    });
  }

  /* ---------- Filtre des publications par couche ---------- */
  const layers = [...document.querySelectorAll('input[data-layer]')];
  if (layers.length) {
    const pubs = [...document.querySelectorAll('.pub')];
    document.querySelectorAll('[data-count]').forEach((el) => {
      el.textContent = pubs.filter((p) => p.dataset.type === el.dataset.count).length;
    });
    const update = () => {
      const on = new Set(layers.filter((l) => l.checked).map((l) => l.dataset.layer));
      pubs.forEach((p) => { p.hidden = !on.has(p.dataset.type); });
    };
    layers.forEach((l) => l.addEventListener('change', update));
  }

  /* ---------- Année du pied de page ---------- */
  document.querySelectorAll('[data-year]').forEach((el) => { el.textContent = new Date().getFullYear(); });
})();
