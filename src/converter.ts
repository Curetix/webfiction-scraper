import * as cheerio from "cheerio";
import { join } from "node:path";
import { readFileSync, writeFileSync, existsSync, rmSync, mkdirSync } from "node:fs";
import { Manifest } from "@/manifest.ts";
import { CHAPTER_DOC } from "@/config/schema.ts";
import type { ResolvedFictionConfig, ManifestEntry } from "@/config/schema.ts";
import { ElementNotFoundException } from "@/errors.ts";
import { applyChapterFixes } from "@/chapter-fixes.ts";
import { unwrapToplevelDivs } from "@/chapter-fixes.ts";

/**
 * Converts cached raw HTML chapter files into clean XHTML for inclusion in EPUBs.
 */
export class Converter {
  private files: ResolvedFictionConfig["files"];
  private selectors: ResolvedFictionConfig["selectors"];
  private substitutions: ResolvedFictionConfig["substitutions"];
  private removeEmptyElements: boolean;
  private skipUrls: string[];
  private skipConversion: boolean;
  public manifest: Manifest;

  constructor(config: ResolvedFictionConfig) {
    this.files = config.files;
    this.selectors = config.selectors;
    this.substitutions = config.substitutions;
    this.removeEmptyElements = config.removeEmptyElements;
    this.skipUrls = config.skipUrls;
    this.skipConversion = config.skipConversion;
    this.manifest = new Manifest(config.files.manifestFile);
  }

  /**
   * Convert a single chapter's raw HTML into clean XHTML.
   */
  convert(doc: string, chapter: ManifestEntry): string {
    const title = chapter.title;
    const $ = cheerio.load(doc);

    const contentEl = $(this.selectors.contentElement).first();
    if (!contentEl.length) {
      throw new ElementNotFoundException(
        `Content element not found for chapter: ${title}`,
      );
    }

    if (!this.skipConversion) {
      // Apply URL-based chapter fixes
      applyChapterFixes(
        chapter.url,
        $,
        contentEl,
        this.selectors.contentElement,
      );

      // Handle content start element — remove siblings before a start marker
      if (this.selectors.contentStartElement) {
        const match = this.selectors.contentStartElement.find(
          (x) => x.chapterUrl === chapter.url,
        );
        if (match) {
          const startEl = contentEl.find(match.selector).first();
          if (startEl.length) {
            startEl.prevAll().remove();
          }
        }
      }

      // Find the last <p> element
      let lastPEl = contentEl
        .find(`${this.selectors.contentElement} > p:last-of-type`)
        .first();

      if (!lastPEl.length) {
        // RoyalRoad sometimes wraps content in a div
        if (chapter.url.includes("royalroad.com")) {
          unwrapToplevelDivs($, contentEl, this.selectors.contentElement);
          lastPEl = contentEl
            .find(`${this.selectors.contentElement} > p:last-of-type`)
            .first();
        }

        if (!lastPEl.length) {
          throw new ElementNotFoundException(
            `Last paragraph not found for chapter: ${title}`,
          );
        }
      }

      // Handle cut-off element
      const cutOff = this.selectors.cutOffElement;
      if (cutOff) {
        const selectors = Array.isArray(cutOff) ? cutOff : [cutOff];
        for (const sel of selectors) {
          const cutEl = contentEl.find(sel).first();
          if (cutEl.length) {
            const prev = cutEl.prev();
            if (prev.length) {
              lastPEl = prev;
            }
            break;
          }
        }
      }

      // Delete everything after the last element
      if (lastPEl.length) {
        lastPEl.nextAll().remove();
      }

      // Remove empty elements (except <hr>)
      if (this.removeEmptyElements) {
        contentEl.children().each((_, el) => {
          const $el = $(el);
          if (
            (el as unknown as { tagName: string }).tagName !== "hr" &&
            $el.text().trim() === ""
          ) {
            $el.remove();
          }
        });
      }

      // Apply CSS selector substitutions
      for (const sub of this.substitutions) {
        if (sub.selectorType !== "css") continue;
        if (sub.chapterUrl && sub.chapterUrl !== chapter.url) continue;

        const els = contentEl.find(sub.selector);

        if (els.length === 0 && sub.warn) {
          console.log(
            `Chapter '${title}': No matches for selector '${sub.selector}'. Please check if the config is up-to-date.`,
          );
        }

        els.each((_, el) => {
          if (sub.replaceWith) {
            $(el).replaceWith(sub.replaceWith);
          } else {
            $(el).remove();
          }
        });
      }
    }

    // Change the content element to <body> and add <h1> title
    (contentEl.get(0) as unknown as { tagName: string }).tagName = "body";
    contentEl.removeAttr("class");
    contentEl.prepend(`<h1>${this.escapeHtml(title)}</h1>`);

    // Build the output XHTML document
    const $doc = cheerio.load(CHAPTER_DOC, { xml: true });
    $doc("head").append(`<title>${this.escapeHtml(title)}</title>`);
    $doc("body").replaceWith(contentEl);

    // Serialize and apply text/regex substitutions
    let result = $doc.html();
    for (const sub of this.substitutions) {
      if (sub.selectorType === "text") {
        result = result.replaceAll(sub.selector, sub.replaceWith);
      } else if (sub.selectorType === "regex") {
        result = result.replace(new RegExp(sub.selector, "g"), sub.replaceWith);
      }
    }

    console.log(`Converted chapter: ${title}`);
    return result;
  }

  /** Escape HTML entities in text. */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  /** Convert a single file from cache → book folder. */
  convertFile(index: number, chapter: ManifestEntry): number {
    const inFile = join(this.files.cacheFolder, chapter.file);
    const outFile = join(this.files.bookFolder, chapter.file);

    if (!existsSync(inFile)) {
      throw new Error(`File ${inFile} not found`);
    }

    const doc = readFileSync(inFile, "utf-8");
    const converted = this.convert(doc, chapter);
    writeFileSync(outFile, converted, "utf-8");

    return index;
  }

  /**
   * Convert all unconverted chapters.
   * Uses Promise.all for concurrent processing.
   */
  async convertAll(): Promise<void> {
    const chaptersToConvert: Array<[number, ManifestEntry]> = [];

    for (let i = 0; i < this.manifest.length; i++) {
      const entry = this.manifest.entries[i]!;
      if (!entry.converted && !this.skipUrls.includes(entry.url)) {
        chaptersToConvert.push([i, entry]);
      }
    }

    // Process conversions — these are CPU-bound but fast with cheerio
    const convertedIndices: number[] = [];
    for (const [index, chapter] of chaptersToConvert) {
      try {
        const result = this.convertFile(index, chapter);
        convertedIndices.push(result);
      } catch (e) {
        console.error(
          `Failed to convert chapter ${chapter.title}: ${e instanceof Error ? e.message : e}`,
        );
      }
    }

    for (const i of convertedIndices) {
      this.manifest.markConverted(i);
    }
    this.manifest.save();

    console.log("Converted all chapters!");
  }

  /** Delete the book folder and reset conversion flags in manifest. */
  clean(): void {
    rmSync(this.files.bookFolder, { recursive: true, force: true });
    mkdirSync(this.files.bookFolder, { recursive: true });

    for (let i = 0; i < this.manifest.length; i++) {
      const entry = this.manifest.entries[i];
      if (entry) {
        entry.converted = false;
      }
    }
    this.manifest.save();
  }
}
