import * as cheerio from "cheerio";
import { join } from "node:path";
import { rmSync, mkdirSync, writeFileSync } from "node:fs";
import { Manifest } from "@/manifest.ts";
import { ElementNotFoundException } from "@/errors.ts";
import type { ResolvedFictionConfig, ManifestEntry } from "@/config/schema.ts";

export interface DownloadResult {
  url: string;
  title: string | null;
  content: Buffer | null;
  $: cheerio.CheerioAPI | null;
}

/**
 * Base sequential web crawler.
 * Follows next-chapter links one by one, saving raw HTML to a cache folder.
 */
export class Crawler {
  protected startUrl: string;
  protected endUrl: string;
  protected skipUrls: string[];
  protected selectors: ResolvedFictionConfig["selectors"];
  protected files: ResolvedFictionConfig["files"];
  public manifest: Manifest;

  constructor(config: ResolvedFictionConfig) {
    this.startUrl = config.startUrl;
    this.endUrl = config.endUrl;
    this.skipUrls = config.skipUrls;
    this.selectors = config.selectors;
    this.files = config.files;
    this.manifest = new Manifest(config.files.manifestFile);
  }

  /** Main download loop — resumes from last manifest entry or starts fresh. */
  async startDownload(): Promise<void> {
    let nextUrl: string | null;
    let index: number;

    if (this.manifest.length > 0) {
      const lastEntry = this.manifest.entries[this.manifest.length - 1];
      nextUrl = lastEntry?.url ?? this.startUrl;
      index = this.manifest.length - 1;
    } else {
      nextUrl = this.startUrl;
      index = 0;
    }

    while (nextUrl !== null) {
      let result: DownloadResult;
      try {
        result = await this.downloadChapter(nextUrl);
      } catch (e) {
        if (e instanceof ElementNotFoundException) {
          console.error(e.message);
          process.exit(1);
        }
        throw e;
      }

      if (!result.title && !result.content && !result.$) {
        return;
      }

      if (!this.skipUrls.includes(result.url)) {
        const fileName = this.saveChapter(result.content!, index);
        this.addChapterToManifest(index, result.url, result.title!, fileName);
        index++;
        console.log(`Downloaded chapter ${result.title}`);
      } else {
        console.log(`Skipped chapter ${result.title}`);
      }

      if (result.url === this.endUrl) {
        return;
      }

      nextUrl = this.findNextChapterUrl(result.url, result.$!);
    }
  }

  /** Download a single chapter page and extract its title. */
  async downloadChapter(url: string): Promise<DownloadResult> {
    const response = await fetch(url);
    const buffer = Buffer.from(await response.arrayBuffer());
    const $ = cheerio.load(buffer);

    const titleEl = $(this.selectors.titleElement).first();
    if (!titleEl.length) {
      throw new ElementNotFoundException(`Title element not found at ${url}`);
    }

    let title = titleEl
      .text()
      .trim()
      .replace(/\u00a0/g, " ")
      .replace(/ {2,}/g, " ");

    return { url: response.url, title, content: buffer, $ };
  }

  /** Save raw chapter HTML to the cache folder. */
  saveChapter(content: Buffer, index: number): string {
    const chapterFile = `chapter${String(index).padStart(3, "0")}.html`;
    writeFileSync(join(this.files.cacheFolder, chapterFile), content);
    return chapterFile;
  }

  /** Add or update a manifest entry and persist. */
  addChapterToManifest(
    index: number,
    url: string,
    title: string,
    fileName: string,
  ): void {
    const entry: ManifestEntry = {
      title,
      file: fileName,
      converted: false,
      url,
    };

    if (this.manifest.length - 1 === index) {
      this.manifest.setEntry(index, entry);
    } else {
      this.manifest.entries.push(entry);
    }

    this.manifest.save();
  }

  /** Find the URL of the next chapter by following the configured CSS selector. */
  findNextChapterUrl(
    currentUrl: string,
    $: cheerio.CheerioAPI,
  ): string | null {
    const nextEl = $(this.selectors.nextChapterElement).first();

    if (nextEl.length) {
      let nextUrl = nextEl.attr("href");
      if (!nextUrl) {
        console.log("Next chapter element found but has no href");
        return null;
      }

      if (!nextUrl.startsWith("http")) {
        const parsed = new URL(currentUrl);
        nextUrl = `${parsed.protocol}//${parsed.hostname}${nextUrl.startsWith("/") ? nextUrl : `/${nextUrl}`}`;
      }

      return nextUrl;
    }

    console.log("Next chapter element not found");
    return null;
  }

  /** Delete the cache folder and clear the manifest. */
  clean(): void {
    rmSync(this.files.cacheFolder, { recursive: true, force: true });
    mkdirSync(this.files.cacheFolder, { recursive: true });
    this.manifest.clear();
    this.manifest.save();
  }
}
