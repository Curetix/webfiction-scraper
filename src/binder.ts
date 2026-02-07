import { join, basename } from "node:path";
import { readFileSync, existsSync, writeFileSync } from "node:fs";
import { Manifest } from "@/manifest.ts";
import { DC_KEYS } from "@/config/schema.ts";
import type { ResolvedFictionConfig } from "@/config/schema.ts";
import { buildEpub, type EpubBuilderOptions } from "@/epub/builder.ts";
import type { EpubMetadata } from "@/epub/templates.ts";

/**
 * Binds converted XHTML chapter files into an EPUB e-book.
 */
export class Binder {
  private config: ResolvedFictionConfig;
  public manifest: Manifest;

  constructor(config: ResolvedFictionConfig) {
    this.config = config;
    this.manifest = new Manifest(config.files.manifestFile);
  }

  /** Build the EPUB from converted chapters. */
  async bindBook(): Promise<void> {
    const metadata: EpubMetadata = {
      identifier: this.config.metadata.identifier ?? "",
      title: this.config.metadata.title,
      language: this.config.metadata.language,
      author: this.config.metadata.author,
    };

    // Separate DC metadata from custom metadata
    const extraDcMetadata: Record<string, string> = {};
    const extraMeta: Record<string, string> = {};

    for (const [key, value] of Object.entries(this.config.metadata)) {
      if (
        key === "title" ||
        key === "author" ||
        key === "language" ||
        key === "identifier" ||
        key === "publisher"
      ) {
        continue; // Already handled or handled separately
      }
      if ((DC_KEYS as readonly string[]).includes(key)) {
        extraDcMetadata[key] = String(value);
      } else {
        extraMeta[key] = String(value);
      }
    }

    // Add publisher to DC metadata
    if (this.config.metadata.publisher) {
      extraDcMetadata["publisher"] = this.config.metadata.publisher;
    }

    // Handle cover image
    let coverImage: EpubBuilderOptions["coverImage"] = null;
    const coverFile = this.config.files.coverFile;

    if (coverFile) {
      let localCoverPath = coverFile;

      // If cover is a URL, download it
      try {
        const url = new URL(coverFile);
        if (url.protocol === "http:" || url.protocol === "https:") {
          const fileName = basename(url.pathname);
          localCoverPath = join(this.config.files.workingFolder, fileName);

          if (!existsSync(localCoverPath)) {
            console.log("Downloading cover image...");
            const response = await fetch(coverFile);
            if (response.ok) {
              const buffer = Buffer.from(await response.arrayBuffer());
              writeFileSync(localCoverPath, buffer);
            }
          }
        }
      } catch {
        // Not a URL, treat as local path
      }

      if (existsSync(localCoverPath)) {
        const data = new Uint8Array(readFileSync(localCoverPath));
        coverImage = {
          fileName: basename(localCoverPath),
          data,
        };
      }
    }

    // Collect converted chapters
    const chapters: EpubBuilderOptions["chapters"] = [];
    const bookFolder = this.config.files.bookFolder;

    for (const entry of this.manifest.entries) {
      if (!entry.converted) continue;

      const fileName = basename(entry.file);
      const filePath = join(bookFolder, fileName);

      if (existsSync(filePath)) {
        const content = new Uint8Array(readFileSync(filePath));
        chapters.push({
          fileName,
          title: entry.title,
          content,
        });
      }
    }

    // Build EPUB
    const epubData = buildEpub({
      metadata,
      chapters,
      coverImage,
      stylesheet: this.config.style ?? "",
      extraDcMetadata,
      extraMeta,
    });

    // Write EPUB file
    writeFileSync(this.config.files.epubFile, epubData);
    console.log("Created EPUB!");
  }
}
