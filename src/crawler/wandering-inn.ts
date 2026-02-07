import * as cheerio from "cheerio";
import { input, confirm } from "@inquirer/prompts";
import { Crawler, type DownloadResult } from "./crawler.ts";
import { ElementNotFoundException } from "@/errors.ts";
import type { ResolvedFictionConfig } from "@/config/schema.ts";

/** Hardcoded Solstice multi-part chapter URL mappings (Volume 7 finale). */
const SOLSTICE_NEXT_URLS: Record<string, string> = {
  "https://wanderinginn.com/2020/12/23/solstice-pt-3/":
    "https://wanderinginn.com/2020/12/23/solstice-pt-4/",
  "https://wanderinginn.com/2020/12/23/solstice-pt-4/":
    "https://wanderinginn.com/2020/12/23/solstice-pt-5/",
  "https://wanderinginn.com/2020/12/23/solstice-pt-5/":
    "https://wanderinginn.com/2020/12/23/solstice-pt-6/",
  "https://wanderinginn.com/2020/12/23/solstice-pt-6/":
    "https://wanderinginn.com/2020/12/23/solstice-pt-7/",
  "https://wanderinginn.com/2020/12/23/solstice-pt-7/":
    "https://wanderinginn.com/2020/12/23/solstice-pt-8/",
  "https://wanderinginn.com/2020/12/23/solstice-pt-8/":
    "https://wanderinginn.com/2020/12/23/solstice-pt-9/",
};

const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36";

/**
 * Crawler specialized for The Wandering Inn.
 * Handles password-protected chapters (WordPress) and Patreon API lookups.
 */
export class WanderingInnPatreonCrawler extends Crawler {
  private patreonCookie: string | null;
  private cookies: Map<string, string> = new Map();

  constructor(config: ResolvedFictionConfig, patreonCookie?: string | null) {
    super(config);
    console.log("Using Wandering Inn Crawler");
    this.patreonCookie = patreonCookie ?? null;
  }

  /** Fetch recent posts from the Patreon API for The Wandering Inn campaign. */
  private async getPatreonPosts(): Promise<
    Array<{ attributes: Record<string, string> }> | null
  > {
    if (!this.patreonCookie) {
      console.log(
        "Patreon session not initialized! Please provide the cookie!",
      );
      return null;
    }

    const params = new URLSearchParams({
      "fields[post]":
        "content,published_at,patreon_url,post_type,title,url",
      "filter[campaign_id]": "568211",
      sort: "-published_at",
    });

    const response = await fetch(
      `https://www.patreon.com/api/posts?${params}`,
      {
        headers: {
          cookie: `session_id=${this.patreonCookie}`,
        },
      },
    );

    if (response.ok) {
      const json = (await response.json()) as {
        data?: Array<{ attributes: Record<string, string> }>;
      };
      return json.data ?? null;
    }

    return null;
  }

  /** Search Patreon posts to find the password for a protected chapter. */
  private async getPatreonPassword(
    chapterTitle: string,
    chapterUrl: string,
  ): Promise<string | null> {
    console.log("Trying to automatically find password on Patreon...");

    const posts = await this.getPatreonPosts();
    if (!posts) return null;

    // Try to find post by title match
    let foundPost = posts.find(
      (p) => (p.attributes["title"] ?? "").trim() === chapterTitle,
    );

    // Fall back to URL match in content
    if (!foundPost) {
      const urlWithoutScheme = chapterUrl.replace("https://", "");
      foundPost = posts.find((p) =>
        (p.attributes["content"] ?? "").includes(urlWithoutScheme),
      );
    }

    if (!foundPost) return null;

    const $ = cheerio.load(foundPost.attributes["content"] ?? "");
    const passwordEl = $('p:contains("Password:")').first();

    if (passwordEl.length) {
      console.log("Found a password! But does it work?");
      return passwordEl.next().text().trim() || null;
    }

    return null;
  }

  /** Perform a fetch with session cookies and user-agent header. */
  private async sessionFetch(url: string, init?: RequestInit): Promise<Response> {
    const cookieStr = Array.from(this.cookies.entries())
      .map(([k, v]) => `${k}=${v}`)
      .join("; ");

    return fetch(url, {
      ...init,
      headers: {
        "user-agent": USER_AGENT,
        ...(cookieStr ? { cookie: cookieStr } : {}),
        ...(init?.headers ?? {}),
      },
      redirect: "follow",
    });
  }

  /** Store cookies from a Set-Cookie response header. */
  private storeCookies(response: Response): void {
    const setCookies = response.headers.getSetCookie?.() ?? [];
    for (const sc of setCookies) {
      const [pair] = sc.split(";");
      if (pair) {
        const eqIdx = pair.indexOf("=");
        if (eqIdx > 0) {
          this.cookies.set(pair.slice(0, eqIdx), pair.slice(eqIdx + 1));
        }
      }
    }
  }

  override async downloadChapter(url: string): Promise<DownloadResult> {
    const response = await this.sessionFetch(url);
    this.storeCookies(response);

    if (!response.ok) {
      console.log(
        `Something went wrong! URL: ${response.url}, Status: ${response.status}`,
      );
      const retry = await confirm({
        message: "Do you want to enter another URL?",
      });
      if (retry) {
        const newUrl = await input({ message: "Enter the URL" });
        return this.downloadChapter(newUrl);
      }
      return { url: response.url, title: null, content: null, $: null };
    }

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
      .replace(/ {2,}/g, " ")
      .replace("Protected: ", "")
      .replace("Patron Early Access: ", "");

    // Check for password-protected chapter (WordPress)
    const passwordForm = $(".entry-content form[method=post]").first();
    if (passwordForm.length) {
      console.log(`Protected chapter ${title} reached!`);

      let password: string | null = null;

      const hasPassword = await confirm({
        message: "Do you have the latest Patreon password for this chapter?",
        default: true,
      });

      if (hasPassword) {
        password = await input({ message: "Enter the password" });
      } else {
        return { url: response.url, title: null, content: null, $: null };
      }

      if (password) {
        const formAction =
          passwordForm.attr("action") ??
          "https://wanderinginn.com/wp-login.php?action=postpass";

        const formData = new URLSearchParams({
          post_password: password,
          Submit: "Submit",
        });

        const postResponse = await this.sessionFetch(formAction, {
          method: "POST",
          body: formData.toString(),
          headers: {
            "content-type": "application/x-www-form-urlencoded",
            referer: response.url,
          },
        });
        this.storeCookies(postResponse);

        return this.downloadChapter(response.url);
      }
    }

    return { url: response.url, title, content: buffer, $ };
  }

  override findNextChapterUrl(
    currentUrl: string,
    $: cheerio.CheerioAPI,
  ): string | null {
    const solsticeNext = SOLSTICE_NEXT_URLS[currentUrl];
    if (solsticeNext) return solsticeNext;

    return super.findNextChapterUrl(currentUrl, $);
  }
}
