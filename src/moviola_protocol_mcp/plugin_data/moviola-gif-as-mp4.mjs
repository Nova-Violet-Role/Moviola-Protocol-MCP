// moviola-gif-as-mp4.mjs -- the Moviola Protocol gif-as-video adapter
// for stock OpenCode, ECMAScript form (no build step, works with
// local models and any loader that takes plain .mjs plugins).
//
// Logic identical to moviola-gif-as-mp4.ts; see that file for the
// origin (the wireFilePart adapter in the Nova Violet OpenCode
// build) and the one deliberate widening (image/gif relabeled too).
//
// GIF bytes travel labeled as video/mp4 on the wire. Servers
// validate the mime allowlist but decode (sniff) content, so the
// label routes while the bytes rule. Opt out with
// OPENCODE_GIF_AS_VIDEO=0.

const relabel = (part) => {
  if (!part || part.type !== "file") return
  if (part.mime !== "video/gif" && part.mime !== "image/gif") return
  part.mime = "video/mp4"
  if (typeof part.url === "string") {
    part.url = part.url.replace(
      /^data:(video|image)\/gif;/,
      "data:video/mp4;",
    )
  }
}

export const MoviolaGifAsMp4 = async () => {
  return {
    "experimental.chat.messages.transform": async (_input, output) => {
      if (process.env.OPENCODE_GIF_AS_VIDEO === "0") return
      for (const message of output.messages) {
        for (const part of message.parts) {
          relabel(part)
        }
      }
    },
  }
}

export default MoviolaGifAsMp4
