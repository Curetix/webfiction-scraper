import { zipSync, strToU8, type Zippable } from "fflate";
import {
  containerXml,
  contentOpf,
  tocNcx,
  navXhtml,
  type EpubMetadata,
  type EpubChapter,
} from "./templates.ts";

export interface EpubBuilderOptions {
  metadata: EpubMetadata;
  chapters: Array<EpubChapter & { content: Uint8Array }>;
  coverImage?: { fileName: string; data: Uint8Array } | null;
  stylesheet?: string;
  extraDcMetadata?: Record<string, string>;
  extraMeta?: Record<string, string>;
}

/**
 * Build an EPUB 3 archive as a Uint8Array (ZIP).
 *
 * Structure:
 *   mimetype                   (stored, uncompressed)
 *   META-INF/container.xml
 *   EPUB/content.opf
 *   EPUB/toc.ncx
 *   EPUB/nav.xhtml
 *   EPUB/style.css
 *   EPUB/<cover image>
 *   EPUB/<chapter files>
 */
export function buildEpub(options: EpubBuilderOptions): Uint8Array {
  const {
    metadata,
    chapters,
    coverImage,
    stylesheet = "",
    extraDcMetadata = {},
    extraMeta = {},
  } = options;

  const hasCover = !!coverImage;
  const coverFileName = coverImage?.fileName ?? "";

  const chapterList: EpubChapter[] = chapters.map((ch) => ({
    fileName: ch.fileName,
    title: ch.title,
  }));

  // Build the ZIP entries
  const files: Zippable = {};

  // mimetype must be first and stored uncompressed
  files["mimetype"] = [strToU8("application/epub+zip"), { level: 0 }];

  // META-INF
  files["META-INF/container.xml"] = strToU8(containerXml());

  // EPUB package files
  files["EPUB/content.opf"] = strToU8(
    contentOpf(
      metadata,
      chapterList,
      hasCover,
      coverFileName,
      extraDcMetadata,
      extraMeta,
    ),
  );

  files["EPUB/toc.ncx"] = strToU8(
    tocNcx(metadata.identifier, metadata.title, chapterList),
  );

  files["EPUB/nav.xhtml"] = strToU8(
    navXhtml(metadata.title, chapterList),
  );

  // Stylesheet
  const css = `@namespace epub "http://www.idpf.org/2007/ops";\n${stylesheet}`;
  files["EPUB/style.css"] = strToU8(css);

  // Cover image
  if (coverImage) {
    files[`EPUB/${coverImage.fileName}`] = coverImage.data;
  }

  // Chapter files
  for (const ch of chapters) {
    files[`EPUB/${ch.fileName}`] = ch.content;
  }

  return zipSync(files);
}
