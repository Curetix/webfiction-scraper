import type { ResolvedFictionConfig } from "@/config/schema.ts";

// ---------------------------------------------------------------------------
// EPUB XML/XHTML template functions
// ---------------------------------------------------------------------------

export interface EpubMetadata {
  identifier: string;
  title: string;
  language: string;
  author: string;
  [key: string]: string;
}

export interface EpubChapter {
  fileName: string;
  title: string;
}

/**
 * container.xml — required META-INF file pointing to the OPF package document.
 */
export function containerXml(): string {
  return `<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`;
}

/**
 * content.opf — the EPUB package document with metadata, manifest, and spine.
 */
export function contentOpf(
  metadata: EpubMetadata,
  chapters: EpubChapter[],
  hasCover: boolean,
  coverFileName: string,
  extraDcMetadata: Record<string, string>,
  extraMeta: Record<string, string>,
): string {
  const dcLines: string[] = [];
  dcLines.push(
    `    <dc:identifier id="BookId">${escapeXml(metadata.identifier)}</dc:identifier>`,
  );
  dcLines.push(`    <dc:title>${escapeXml(metadata.title)}</dc:title>`);
  dcLines.push(`    <dc:language>${escapeXml(metadata.language)}</dc:language>`);
  dcLines.push(`    <dc:creator>${escapeXml(metadata.author)}</dc:creator>`);

  for (const [key, value] of Object.entries(extraDcMetadata)) {
    dcLines.push(`    <dc:${key}>${escapeXml(value)}</dc:${key}>`);
  }

  const metaLines: string[] = [];
  metaLines.push(
    `    <meta property="dcterms:modified">${new Date().toISOString().replace(/\.\d+Z$/, "Z")}</meta>`,
  );
  for (const [name, content] of Object.entries(extraMeta)) {
    metaLines.push(
      `    <meta name="${escapeXml(name)}" content="${escapeXml(content)}"/>`,
    );
  }

  const manifestLines: string[] = [];
  manifestLines.push(
    `    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>`,
  );
  manifestLines.push(
    `    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>`,
  );
  manifestLines.push(
    `    <item id="style" href="style.css" media-type="text/css"/>`,
  );

  if (hasCover) {
    const ext = coverFileName.split(".").pop()?.toLowerCase() ?? "jpg";
    const mediaType =
      ext === "png" ? "image/png" : ext === "gif" ? "image/gif" : "image/jpeg";
    manifestLines.push(
      `    <item id="cover-image" href="${escapeXml(coverFileName)}" media-type="${mediaType}" properties="cover-image"/>`,
    );
  }

  for (let i = 0; i < chapters.length; i++) {
    const ch = chapters[i]!;
    manifestLines.push(
      `    <item id="chapter${i}" href="${escapeXml(ch.fileName)}" media-type="application/xhtml+xml"/>`,
    );
  }

  const spineLines: string[] = [];
  for (let i = 0; i < chapters.length; i++) {
    spineLines.push(`    <itemref idref="chapter${i}"/>`);
  }

  return `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
${dcLines.join("\n")}
${metaLines.join("\n")}
  </metadata>
  <manifest>
${manifestLines.join("\n")}
  </manifest>
  <spine toc="ncx">
${spineLines.join("\n")}
  </spine>
</package>`;
}

/**
 * toc.ncx — NCX table of contents for EPUB 2 compatibility.
 */
export function tocNcx(
  identifier: string,
  title: string,
  chapters: EpubChapter[],
): string {
  const navPoints = chapters
    .map(
      (ch, i) => `    <navPoint id="navPoint-${i + 1}" playOrder="${i + 1}">
      <navLabel><text>${escapeXml(ch.title)}</text></navLabel>
      <content src="${escapeXml(ch.fileName)}"/>
    </navPoint>`,
    )
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="${escapeXml(identifier)}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>${escapeXml(title)}</text></docTitle>
  <navMap>
${navPoints}
  </navMap>
</ncx>`;
}

/**
 * nav.xhtml — EPUB 3 navigation document.
 */
export function navXhtml(title: string, chapters: EpubChapter[]): string {
  const listItems = chapters
    .map(
      (ch) =>
        `      <li><a href="${escapeXml(ch.fileName)}">${escapeXml(ch.title)}</a></li>`,
    )
    .join("\n");

  return `<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>${escapeXml(title)}</title>
</head>
<body>
  <nav epub:type="toc" id="toc">
    <h1>Table of Contents</h1>
    <ol>
${listItems}
    </ol>
  </nav>
</body>
</html>`;
}

/** Escape special XML characters. */
function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}
