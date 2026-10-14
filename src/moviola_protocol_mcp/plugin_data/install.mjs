#!/usr/bin/env node
// install.mjs -- install the Moviola gif-as-mp4 plugin into OpenCode.
//
// Usage:
//   node install.mjs [target-config-dir] [--ts] [--no-read-tool] [--force]
//   npx moviola-protocol-mcp-opencode-plugin [same flags]  (after npm publish)
//
// Default target: ~/.config/opencode (or %USERPROFILE%\.config\opencode).
// Copies the plugin (.mjs, or .ts with --ts) into <target>/plugins/
// and, unless --no-read-tool, the portable read tool into
// <target>/tools/read.ts. An existing read.ts with different content
// is never overwritten without --force.

import { copyFileSync, existsSync, mkdirSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const argv = process.argv.slice(2)
const flags = new Set(argv.filter((a) => a.startsWith("--")))
const positional = argv.filter((a) => !a.startsWith("--"))
const target = positional[0] ?? join(homedir(), ".config", "opencode")
const useTs = flags.has("--ts")
const force = flags.has("--force")

const identical = (a, b) =>
  existsSync(b) && readFileSync(a).equals(readFileSync(b))

const written = []
const pluginName = useTs ? "moviola-gif-as-mp4.ts" : "moviola-gif-as-mp4.mjs"
const pluginsDir = join(target, "plugins")
mkdirSync(pluginsDir, { recursive: true })
const pluginDest = join(pluginsDir, pluginName)
copyFileSync(join(here, pluginName), pluginDest)
written.push(pluginDest)

if (!flags.has("--no-read-tool")) {
  const toolsDir = join(target, "tools")
  mkdirSync(toolsDir, { recursive: true })
  const readSrc = join(here, "read.ts")
  const readDest = join(toolsDir, "read.ts")
  if (existsSync(readDest) && !identical(readSrc, readDest) && !force) {
    console.log(
      "SKIP tools/read.ts: a different read tool already exists " +
        `(pass --force to replace): ${readDest}`,
    )
  } else {
    copyFileSync(readSrc, readDest)
    written.push(readDest)
  }
}

for (const path of written) console.log(`WROTE ${path}`)
console.log(
  "Done. Restart OpenCode; GIFs now ride to models as video/mp4 " +
    "(OPENCODE_GIF_AS_VIDEO=0 opts out).",
)
