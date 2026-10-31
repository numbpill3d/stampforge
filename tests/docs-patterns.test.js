const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync("docs/app.js", "utf8");
const purePrefix = source.slice(0, source.indexOf("function drawBorder"));
const sandbox = {
  document: { getElementById: () => ({ getContext: () => ({}) }) },
};
vm.runInNewContext(
  `${purePrefix}\nglobalThis.patternApi = { patterns, presets, fillPattern };`,
  sandbox,
);

const { patterns, presets, fillPattern } = sandbox.patternApi;

function recordingContext() {
  const fills = [];
  return {
    fills,
    fillStyle: "",
    globalAlpha: 1,
    fillRect: (...args) => fills.push(args),
  };
}

test("every preset texture is available in the texture selector", () => {
  const missing = presets.map((preset) => preset[1]).filter((name) => !patterns.includes(name));
  assert.equal(missing.length, 0, `missing textures: ${missing.join(", ")}`);
});

test("scanlines and dots render visible pattern marks", () => {
  for (const pattern of ["scanlines", "dots"]) {
    const context = recordingContext();
    fillPattern(context, 24, 16, pattern, "#000", "#fff", 0);
    assert.ok(context.fills.length > 1, `${pattern} should draw over the background`);
  }
});
