import * as cheerio from "cheerio";
import { ConfigGenerator } from "./generator.ts";
import {
  ElementNotFoundException,
  InvalidPageException,
} from "@/errors.ts";

const FICTION_PAGE_PATTERN =
  /(?:https?:\/\/)?www\.royalroad\.com\/fiction\/\d+\/.+/;
const CHAPTER_PATTERN =
  /(?:https?:\/\/)?www\.royalroad\.com\/fiction\/\d+\/.+\/chapter\/\d+\/.+/;

/**
 * Auto-generates a fiction config from a Royal Road URL.
 */
export class RoyalRoadConfigGenerator extends ConfigGenerator {
  protected override getSelectors(): Record<string, string> {
    return {
      titleElement: ".fic-header h1",
      contentElement: ".chapter-content",
      nextChapterElement: '.nav-buttons a:contains("Next Chapter")',
    };
  }

  protected override async getMetadata(): Promise<Record<string, string>> {
    let startUrl = this.config.startUrl;

    const response = await fetch(startUrl);
    let html = await response.text();
    let $ = cheerio.load(html);

    const btn = $(".fic-buttons a.btn-primary").first();
    if (!btn.length) {
      throw new ElementNotFoundException(
        "Fiction / chapter button not found",
      );
    }

    const fictionPageMatch = FICTION_PAGE_PATTERN.test(startUrl);
    const chapterPageMatch = CHAPTER_PATTERN.test(startUrl);

    if (fictionPageMatch && !chapterPageMatch) {
      // On the fiction overview page — get the first chapter URL
      startUrl = "https://www.royalroad.com" + (btn.attr("href") ?? "");
    } else if (chapterPageMatch) {
      // On a chapter page — navigate to the fiction overview
      const fictionUrl =
        "https://www.royalroad.com" + (btn.attr("href") ?? "");
      const fictionResponse = await fetch(fictionUrl);
      html = await fictionResponse.text();
      $ = cheerio.load(html);
    } else {
      throw new InvalidPageException(
        "URL does not match a Royal Road fiction or chapter page",
      );
    }

    // Extract cover image
    const coverSrc = $(".thumbnail").attr("src");
    if (coverSrc) {
      this.config.files = { coverFile: coverSrc };
    }

    // Update start URL
    this.config.startUrl = startUrl;

    return {
      title: $(".fic-header h1").text().trim(),
      author: $(".fic-header h4 a").text().trim(),
      description: $(".description .hidden-content").text().trim(),
    };
  }
}
