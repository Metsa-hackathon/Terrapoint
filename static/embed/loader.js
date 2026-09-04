(function () {
  "use strict";
  const frames = Array.from(document.querySelectorAll("iframe[data-terrapoint-forest]"));
  const registry = new Map();

  frames.forEach(function (frame) {
    const source = new URL(frame.src, document.baseURI);
    registry.set(frame, source.origin);
  });

  window.addEventListener("message", function (event) {
    if (!event.data || event.data.type !== "terrapoint:forest-resize") return;
    frames.forEach(function (frame) {
      if (event.source !== frame.contentWindow || event.origin !== registry.get(frame)) return;
      const requested = Number(event.data.height);
      if (!Number.isFinite(requested)) return;
      frame.style.height = Math.max(480, Math.min(6000, Math.ceil(requested))) + "px";
    });
  });
}());
