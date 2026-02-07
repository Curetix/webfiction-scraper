import * as cheerio from "cheerio";
import { ConfigGenerator } from "./generator.ts";
import { InvalidPageException } from "@/errors.ts";

const CHAPTER_PATTERN =
  /(?:https?:\/\/)?www\.fictionpress\.com\/s\/\d+\/\d+\/.+/;

/**
 * Auto-generates a fiction config from a FictionPress URL.
 */
export class FictionPressGenerator extends ConfigGenerator {
  protected override getSelectors(): Record<string, string> {
    return {
      titleElement: "select#chap_select option[selected]",
      contentElement: "#storytext",
      nextChapterElement: 'button.btn:contains("Next")',
    };
  }

  protected override async getMetadata(): Promise<Record<string, string>> {
    const startUrl = this.config.startUrl;

    const response = await fetch(startUrl);
    const html = await response.text();
    const $ = cheerio.load(html);

    if (!CHAPTER_PATTERN.test(startUrl)) {
      throw new InvalidPageException(
        "URL does not match a FictionPress chapter page",
      );
    }

    const coverSrc = $("#img_large img").attr("src");
    if (coverSrc) {
      this.config.files = { coverFile: coverSrc };
    }

    return {
      title: $("#profile_top b.xcontrast_txt").text().trim(),
      author: $("#profile_top a.xcontrast_txt").text().trim(),
      description: $("#profile_top div.xcontrast_txt").text().trim(),
    };
  }
}
