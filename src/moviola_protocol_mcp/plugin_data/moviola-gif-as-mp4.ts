// moviola-gif-as-mp4.ts -- the Moviola Protocol gif-as-video adapter
// for stock OpenCode, as an installable plugin.
//
// Origin: implemented inside the OpenCode source tree
// (packages/opencode/src/session/message-v2.ts, the wireFilePart
// adapter) in the Nova Violet build at D:\OPENCODE-SRC. This plugin
// reproduces that wire step for any OpenCode version:
//
//   GIF bytes travel labeled as video/mp4 on the wire. Servers
//   validate the mime allowlist but decode (sniff) content, so the
//   label routes while the bytes rule. Stored session parts keep
//   their original mime; only the lowered wire copy is relabeled.
//
// One deliberate widening versus the in-source wire step: the source
// relabels video/gif only, because its patched read tool already
// produced video/gif. Stock OpenCode produces image/gif, so this
// plugin relabels both. Pair it with the bundled read tool
// (plugin_data/read.ts, installed as a custom tool) to reproduce the
// full in-source behaviour: read attaches GIF as video/gif, this
// plugin renames it to video/mp4 on the wire, motion survives.
//
// Opt out with OPENCODE_GIF_AS_VIDEO=0 (same switch as the source).

import type { Plugin } from "@opencode-ai/plugin"

type PartLike = {
  type?: string
  mime?: string
  url?: string
}

const relabel = (part: PartLike): void => {
  if (part.type !== "file") return
  if (part.mime !== "video/gif" && part.mime !== "image/gif") return
  part.mime = "video/mp4"
  if (typeof part.url === "string") {
    part.url = part.url.replace(
      /^data:(video|image)\/gif;/,
      "data:video/mp4;",
    )
  }
}

export const MoviolaGifAsMp4: Plugin = async () => {
  return {
    "experimental.chat.messages.transform": async (_input, output) => {
      if (process.env.OPENCODE_GIF_AS_VIDEO === "0") return
      for (const message of output.messages) {
        for (const part of message.parts) {
          relabel(part as PartLike)
        }
      }
    },
  }
}

export default MoviolaGifAsMp4
