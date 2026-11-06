const formats = {
  stamp: { label: "94×50 stamp", w: 94, h: 50 },
  button: { label: "88×31 button", w: 88, h: 31 },
  button32: { label: "88×32 button", w: 88, h: 32 },
  blinkie: { label: "150×20 blinkie", w: 150, h: 20 },
};
const patterns = ["solid", "gradient →", "gradient ↓", "stripes", "checker", "scanlines", "dots", "grid", "diagonal", "plaid", "noise", "polka", "sunburst", "halftone", "glitter", "stars"];
const borders = ["none", "solid", "double", "raised bevel", "sunken bevel", "dashed", "dotted", "postage", "inset line", "pixel corners", "shadow frame", "neon frame"];
const presets = [
  ["Candy chrome", "gradient →", "#ff7fc8", "#fff3fb", "raised bevel", "#ff4fa8"], ["Webring blue", "stripes", "#1464c4", "#8ed7ff", "double", "#061b4a"],
  ["Guestbook green", "checker", "#4eaa65", "#c8f58b", "sunken bevel", "#194c2b"], ["Night mode", "scanlines", "#17152e", "#6d5cff", "solid", "#b7a9ff"],
  ["Rainbow rave", "gradient ↓", "#ff4f9a", "#57e7ff", "double", "#6d1e8f"], ["Pixel lemon", "dots", "#ffe66d", "#fffbd8", "raised bevel", "#a86b00"],
  ["Goth doll", "checker", "#25152f", "#e84b9b", "sunken bevel", "#f6b6df"], ["Aqua fan", "stripes", "#0b7285", "#8ff3e5", "solid", "#043b4a"],
  ["Starry webring", "stars", "#11133d", "#ffe66d", "double", "#ff73c8"], ["Candy scroll", "gradient →", "#ff4fa8", "#ffd0ec", "raised bevel", "#7a1857"],
  ["Cyber scan", "scanlines", "#071b2d", "#49e7ff", "solid", "#49e7ff"], ["Glitter diary", "glitter", "#6c2c91", "#fff0a8", "sunken bevel", "#311047"],
  ["Windows 98", "grid", "#b8c8d8", "#f4f8ff", "raised bevel", "#486070"], ["Y2K chrome", "diagonal", "#d6f7ff", "#ff8de1", "double", "#245d8a"],
  ["Bubble tea", "polka", "#ffb4d8", "#fff0a8", "sunken bevel", "#b54478"], ["Red alert", "halftone", "#8f102b", "#ffcfda", "solid", "#4a0617"],
  ["Faux denim", "plaid", "#24527a", "#8ac6d1", "raised bevel", "#102d47"], ["Candy hearts", "polka", "#ff5c8a", "#ffd1e0", "double", "#9c1748"],
  ["Cyber grid", "grid", "#041b2d", "#00f5d4", "solid", "#00a896"], ["Vaporwave", "sunburst", "#5b2a86", "#ff6ec7", "sunken bevel", "#25103f"],
  ["Pixel sunset", "diagonal", "#ff6b35", "#ffd166", "raised bevel", "#913817"], ["Haunted web", "halftone", "#17121f", "#a855f7", "double", "#5b21b6"],
  ["Space dust", "noise", "#09111f", "#8be9fd", "solid", "#315b80"], ["Limewire", "plaid", "#b7f34a", "#193b2b", "sunken bevel", "#507f22"],
  ["Postage pink", "polka", "#fff0f7", "#ff72b6", "postage", "#bd2d77"], ["Pixel museum", "grid", "#e8e1cf", "#5e574b", "pixel corners", "#332e28"],
  ["Neon shrine", "scanlines", "#101226", "#ff4fd8", "neon frame", "#55e7ff"], ["Soft shadow", "gradient ↓", "#d7efff", "#ffffff", "shadow frame", "#315d82"],
  ["Inset label", "halftone", "#f6c8a8", "#9e3f48", "inset line", "#6b222b"], ["Dotted diary", "dots", "#fffbd8", "#e8a93a", "dotted", "#a56700"],
];
const $ = (id) => document.getElementById(id);
const preview = $("preview"), ctx = preview.getContext("2d");
let formatKey = "stamp", frame = 0;

function fillPattern(g, w, h, type, base, ink, tick) {
  g.fillStyle = base; g.fillRect(0, 0, w, h); if (type === "solid") return; g.fillStyle = ink;
  if (type === "gradient →" || type === "gradient ↓") { const gradient = type.endsWith("→") ? g.createLinearGradient(0, 0, w, 0) : g.createLinearGradient(0, 0, 0, h); gradient.addColorStop(0, base); gradient.addColorStop(1, ink); g.fillStyle = gradient; g.fillRect(0, 0, w, h); return; }
  if (type === "stripes" || type === "diagonal") { g.save(); if (type === "diagonal") { g.rotate(-Math.PI / 4); g.translate(-w, 0); } for (let x = -h; x < w + h; x += type === "diagonal" ? 12 : 8) g.fillRect(x + (tick % 8), 0, type === "diagonal" ? 3 : 4, h * 2); g.restore(); }
  else if (type === "checker") { for (let y = 0; y < h; y += 5) for (let x = 0; x < w; x += 5) if ((x / 5 + y / 5) % 2) g.fillRect(x, y, 5, 5); }
  else if (type === "scanlines") for (let y = tick % 4; y < h; y += 4) g.fillRect(0, y, w, 1);
  else if (type === "dots") for (let y = 2; y < h; y += 6) for (let x = 2; x < w; x += 6) g.fillRect(x, y, 1, 1);
  else if (type === "grid") { for (let x = 0; x < w; x += 8) g.fillRect(x, 0, 1, h); for (let y = 0; y < h; y += 8) g.fillRect(0, y, w, 1); }
  else if (type === "plaid") { for (let x = 0; x < w; x += 12) g.fillRect(x, 0, 2, h); for (let y = 0; y < h; y += 8) g.fillRect(0, y, w, 2); }
  else if (type === "polka") for (let y = 5; y < h + 8; y += 12) for (let x = 5; x < w + 8; x += 12) { g.beginPath(); g.arc(x, y, 2.8, 0, Math.PI * 2); g.fill(); }
  else if (type === "halftone") for (let y = 2; y < h; y += 6) for (let x = 2; x < w; x += 6) { g.beginPath(); g.arc(x, y, 1.8, 0, Math.PI * 2); g.fill(); }
  else if (type === "sunburst") { const cx = w / 2, cy = h / 2; for (let i = 0; i < 12; i += 2) { g.beginPath(); g.moveTo(cx, cy); g.arc(cx, cy, Math.max(w, h), (i + tick) * Math.PI / 6, (i + 1) * Math.PI / 6); g.closePath(); g.fill(); } }
  else if (type === "noise" || type === "glitter") { const count = type === "noise" ? w * h / 8 : w * h / 18; for (let i = 0; i < count; i++) { g.globalAlpha = type === "noise" ? .22 : .55; g.fillRect(Math.random() * w, Math.random() * h, 1, 1); } g.globalAlpha = 1; }
  else if (type === "stars") for (let i = 0; i < Math.max(4, w * h / 90); i++) { const x = (i * 37) % w, y = (i * 19) % h; g.fillRect(x, y, ((i + tick) % 3) ? 1 : 2, ((i + tick) % 3) ? 1 : 2); }
}

function drawBorder(g, w, h, type, color) {
  if (type === "none") return; g.strokeStyle = color; g.lineWidth = 1; g.setLineDash([]);
  if (type === "dashed" || type === "postage") g.setLineDash(type === "dashed" ? [5, 3] : [2, 2]); if (type === "dotted") g.setLineDash([1, 3]);
  if (type === "inset line") { g.strokeRect(2, 2, w - 4, h - 4); return; }
  if (type === "shadow frame") { g.strokeStyle = "rgba(0,0,0,.7)"; g.strokeRect(2, 2, w - 1, h - 1); g.strokeStyle = color; g.strokeRect(0, 0, w - 3, h - 3); return; }
  if (type === "neon frame") { g.strokeStyle = "#101020"; g.strokeRect(0, 0, w - 1, h - 1); g.strokeStyle = color; g.strokeRect(1, 1, w - 3, h - 3); return; }
  if (type === "pixel corners") { const c = Math.min(5, Math.max(2, Math.floor(Math.min(w, h) / 5))); [[0,0,c,0],[0,0,0,c],[w-1,0,w-1-c,0],[w-1,0,w-1,c],[0,h-1,c,h-1],[0,h-1,0,h-1-c],[w-1,h-1,w-1-c,h-1],[w-1,h-1,w-1,h-1-c]].forEach(p => { g.beginPath(); g.moveTo(p[0], p[1]); g.lineTo(p[2], p[3]); g.stroke(); }); return; }
  g.strokeRect(0, 0, w - 1, h - 1); if (type === "double") g.strokeRect(2, 2, w - 5, h - 5); if (type === "raised bevel" || type === "sunken bevel") { g.strokeStyle = type === "raised bevel" ? "white" : "#444"; g.strokeRect(1, 1, w - 3, h - 3); } g.setLineDash([]);
}

function draw() {
  const f = formats[formatKey]; preview.width = f.w; preview.height = f.h; ctx.clearRect(0, 0, f.w, f.h);
  fillPattern(ctx, f.w, f.h, $("pattern").value, $("background").value, $("pattern-color").value, frame); drawBorder(ctx, f.w, f.h, $("border").value, $("border-color").value);
  const caption = $("caption").value.trim(); if (caption) { const size = Math.min(Number($("text-size").value) || 11, Math.max(5, f.h - 2)); ctx.font = `bold ${size}px monospace`; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillStyle = $("text-color").value; if ($("glow").checked) { ctx.shadowColor = $("text-color").value; ctx.shadowBlur = 3; } ctx.fillText(caption, f.w / 2, f.h / 2); ctx.shadowBlur = 0; }
  $("size-readout").textContent = `${f.w} × ${f.h} px`; $("title-size").textContent = `${f.w} × ${f.h}`; $("footer-format").textContent = f.label; $("frame-readout").textContent = $("animate").checked ? "ANIMATED PREVIEW" : "STATIC FRAME";
  $("layer-pattern").textContent = $("pattern").value; $("layer-caption").textContent = caption || "(none)"; $("layer-width").value = f.w; $("layer-height").value = f.h;
}
function loadPreset(index) { const p = presets[index]; if (!p) return; $("preset").value = index; $("background").value = p[2]; $("pattern-color").value = p[3]; $("border").value = p[4]; $("border-color").value = p[5]; $("pattern").value = p[1]; $("preset-note").textContent = `${p[1]} texture / ${p[4]} border / editable in the controls below.`; draw(); }
function rebuildPresetCards() { $("preset-note").textContent = `${presets.length} looks / backgrounds + borders included.`; }
patterns.forEach(value => $("pattern").add(new Option(value, value))); borders.forEach(value => $("border").add(new Option(value, value))); presets.forEach((p, i) => $("preset").add(new Option(p[0], i)));
$("format").addEventListener("change", () => { formatKey = $("format").value; draw(); });
["background", "pattern-color", "border", "border-color", "caption", "text-color", "text-size", "pattern", "animate", "glow"].forEach(id => $(id).addEventListener("input", draw));
$("preset").addEventListener("change", () => loadPreset(Number($("preset").value))); $("export-button").addEventListener("click", () => { const link = document.createElement("a"); link.download = `stampforge-${formatKey}.png`; link.href = preview.toDataURL("image/png"); link.click(); });
document.querySelectorAll(".tab").forEach((tab, index) => tab.addEventListener("click", () => { document.querySelectorAll(".tab").forEach((item, i) => { item.classList.toggle("is-active", i === index); item.setAttribute("aria-selected", i === index); }); document.querySelectorAll(".tab-pane").forEach((pane, i) => { pane.hidden = i !== index; }); }));
rebuildPresetCards(); loadPreset(0); setInterval(() => { if ($("animate").checked) { frame++; draw(); } }, 140);
