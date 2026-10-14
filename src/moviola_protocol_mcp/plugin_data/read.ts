// read.ts -- the MASTER reading tool: replaces built-in `read` by name precedence
// (docs/custom-tools: "If a custom tool uses the same name as a built-in tool,
// the custom tool takes precedence").
//
// The replacement has NO offset/limit parameters at all: whole-file or whole
// directory, verbatim, every time. Reads land in REVERSE first (newest lines
// first: logs and ledgers grow downward, so the freshest fact reads first;
// original line numbers ride along so orientation never lost). Converged
// 2026-09-18 with LAW.TEI.2 (dtd/tei-cache.dtd: "The read order is reverse:
// next first, then findings newest-first... a run that read top-down and
// missed the binding reads again"): the DTD's principle is that a top-down
// cut loses the binding, so the only principled window is newest-first.
// `newest` was cut 2026-09-18: a window, however principled, is still a cut,
// and a cut source is how Erase.cs grew duplicate blocks behind blocked edits.
// Whole-file always; LAW.TEI.2 lives on as newest-first ORDER, never as a filter.
// offset/limit cut blindly from the top and do not exist here. Text is
// normalized to UTF-8 on the way in: BOM stripped, UTF-16 decoded, lone
// surrogates and CRLF normalized, and the notice says what was converted.
// Surveyed 2026-09-18 (dthuerck, Banshal-Yadav, vpoluyaktov, jellydn tool
// repos): nobody publishes a read replacement; the enhancements are our own.
// Tradeoff, stated: built-in image/PDF rendering is not replicated, except
// GIF which rides as a video/gif attachment (Moviola protocol).
import { tool } from "@opencode-ai/plugin";
import { statSync, readdirSync, readFileSync } from "node:fs";

function decode(buf: Buffer): { text: string; notices: string[] } {
  const notices: string[] = [];
  let text: string;
  if (buf.length >= 2 && buf[0] === 0xff && buf[1] === 0xfe) {
    text = buf.toString("utf16le");
    notices.push("decoded from UTF-16LE");
  } else if (buf.length >= 2 && buf[0] === 0xfe && buf[1] === 0xff) {
    const swapped = Buffer.alloc(buf.length);
    for (let i = 0; i + 1 < buf.length; i += 2) {
      swapped[i] = buf[i + 1];
      swapped[i + 1] = buf[i];
    }
    text = swapped.toString("utf16le");
    notices.push("decoded from UTF-16BE");
  } else {
    text = buf.toString("utf8");
    if (text.includes("�")) {
      text = buf.toString("latin1");
      notices.push("not valid UTF-8, read as Windows-1252");
    }
  }
  if (text.charCodeAt(0) === 0xfeff) {
    text = text.slice(1);
    notices.push("BOM stripped");
  }
  if (text.includes("\r")) {
    text = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
    notices.push("CRLF normalized to LF");
  }
  return { text, notices };
}

export default tool({
  description:
    "Read a file whole (verbatim UTF-8, newest lines first with original line numbers, no slicing) or list a directory. This is the only reading tool; offset/limit do not exist. GIF files are attached as video so motion survives.",
  args: {
    filePath: tool.schema.string().describe("Absolute path to the file or directory to read"),
    order: tool.schema.string().describe("'reverse' (default: newest first) or 'forward'").optional(),
  },
  async execute(args) {
    const p = args.filePath;
    // no denials: every file reads (operator order 2026-09-18).
    const reverse = (args.order ?? "reverse").toLowerCase() !== "forward";
    let st;
    try {
      st = statSync(p);
    } catch (err) {
      return `read: no such file or directory: ${p}`;
    }
    try {
      if (st.isDirectory()) {
        const entries = readdirSync(p, { withFileTypes: true });
        const lines = entries.map((e) => (e.isDirectory() ? e.name + "/" : e.name));
        lines.sort();
        return lines.join("\n") || "(empty directory)";
      }
      const buf = readFileSync(p);
      // Moviola protocol: gif bytes ride as video so motion survives; the
      // session relabels video/gif to video/mp4 on the wire. Same
      // OPENCODE_GIF_AS_VIDEO=0 opt-out as the built-in read.
      if (
        process.env.OPENCODE_GIF_AS_VIDEO !== "0" &&
        buf.length >= 4 &&
        buf[0] === 0x47 &&
        buf[1] === 0x49 &&
        buf[2] === 0x46 &&
        buf[3] === 0x38
      ) {
        const name = p.split(/[\\/]/).pop() || p;
        return {
          output: `read: video file, ${buf.length} bytes, attached as video/gif`,
          attachments: [
            {
              type: "file",
              mime: "video/gif",
              url: `data:video/gif;base64,${buf.toString("base64")}`,
              filename: name,
            },
          ],
        };
      }
      if (buf.includes(0) && !(buf.length >= 2 && ((buf[0] === 0xff && buf[1] === 0xfe) || (buf[0] === 0xfe && buf[1] === 0xff)))) {
        return `read: binary file, ${buf.length} bytes, not rendered`;
      }
      const { text, notices } = decode(buf);
      if (text === "") return "(empty file)";
      const lines = text.split("\n");
      if (lines.length > 0 && lines[lines.length - 1] === "") lines.pop();
      const width = String(lines.length).length;
      const numbered = lines.map((l, i) => `${String(i + 1).padStart(width, " ")}: ${l}`);
      if (reverse) numbered.reverse();
      const head = notices.length > 0 ? `[encoding: ${notices.join("; ")}]\n` : "";
      return head + numbered.join("\n");
    } catch (err) {
      return `read: ${(err as Error).message}`;
    }
  },
});
