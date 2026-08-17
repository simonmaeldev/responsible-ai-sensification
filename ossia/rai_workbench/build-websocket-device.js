const fs = require("node:fs");
const path = require("node:path");

const workbenchDir = __dirname;
const adapter = fs.readFileSync(
  path.join(workbenchDir, "websocket-adapter.js"),
  "utf8",
).trim();
const template = fs.readFileSync(
  path.join(workbenchDir, "websocket-device.template.qml"),
  "utf8",
);
const marker = "// @@ADAPTER@@";

if (!template.includes(marker)) {
  throw new Error(`Missing ${marker} in websocket-device.template.qml`);
}

const generated = template.replace(marker, adapter);
fs.writeFileSync(
  path.join(workbenchDir, "websocket-device.qml"),
  generated,
  "utf8",
);
