import type { CheerioAPI, Cheerio } from "cheerio";
import type { AnyNode } from "domhandler";

// ---------------------------------------------------------------------------
// Fix function type
// ---------------------------------------------------------------------------

export type ChapterFixFn = (
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  contentElSelector: string,
) => void;

// ---------------------------------------------------------------------------
// Individual fix functions
// ---------------------------------------------------------------------------

/**
 * Some chapters have <div> elements instead of proper <p> paragraphs,
 * so rename all direct-child <div> tags to <p>.
 */
export function fixDivParagraphs(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  _contentElSelector: string,
): void {
  contentEl.children("div").each((_, el) => {
    (el as unknown as { tagName: string }).tagName = "p";
  });
}

/** Unwrap the first div element. */
export function unwrapDiv(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  _contentElSelector: string,
): void {
  const el = contentEl.find("div").first();
  if (el.length) {
    $(el).children().unwrap();
  }
}

/** Unwrap the first article element. */
export function unwrapArticle(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  _contentElSelector: string,
): void {
  const el = contentEl.find("article").first();
  if (el.length) {
    $(el).children().unwrap();
  }
}

/** Unwrap all divs at content element root level until <p> elements appear. */
export function unwrapToplevelDivs(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  contentElSelector: string,
): void {
  let div = contentEl.find(`${contentElSelector} > div`).first();
  while (
    div.length &&
    contentEl.find(`${contentElSelector} > p`).length === 0
  ) {
    $(div).children().unwrap();
    div = contentEl.find(`${contentElSelector} > div`).first();
  }
}

/** Unwrap all direct-child divs (no loop/check). */
export function unwrapToplevelDivsAlt(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  contentElSelector: string,
): void {
  contentEl.find(`${contentElSelector} > div`).each((_, el) => {
    $(el).children().unwrap();
  });
}

/** Unwrap top-level divs, then convert remaining divs to <p>. */
export function fixNestedDivParagraphs(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  contentElSelector: string,
): void {
  contentEl.find(`${contentElSelector} > div`).each((_, el) => {
    $(el).children().unwrap();
  });
  fixDivParagraphs($, contentEl, contentElSelector);
}

/** Unwrap blockquotes that include a div. */
export function fixBlockquoteAndDiv(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  contentElSelector: string,
): void {
  const bqDiv = contentEl.find("blockquote > div").first();
  if (bqDiv.length) {
    $(bqDiv).children().unwrap();
  }
  unwrapDiv($, contentEl, contentElSelector);
}

// ---------------------------------------------------------------------------
// Remove Royal Road anti-piracy hidden paragraphs
// ---------------------------------------------------------------------------

const RR_WARNING_PATTERN =
  /\.(\w+)\s*\{\s*\n?display:\s*none;\s*\n?speak:\s*never;\s*\n?\}/;

export function removePiracyParagraphs(
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  _contentElSelector: string,
): void {
  const html = $.html();
  const match = RR_WARNING_PATTERN.exec(html);
  if (match?.[1]) {
    contentEl.find(`.${match[1]}`).remove();
  }
}

// ---------------------------------------------------------------------------
// URL-prefix → fix function mapping
// ---------------------------------------------------------------------------

/**
 * Map of URL prefixes to chapter fix functions.
 * More-specific URLs are checked first (longer prefix wins).
 */
export const CHAPTER_FIXES: Array<[string, ChapterFixFn]> = [
  // Specific chapter fixes (must come before the generic RR prefix)
  [
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/494392/chapter-346-bride-and-groom",
    fixDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/541710/chapter-368-even-death-may-die",
    fixDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/551476/chapter-372-a-little-knowledge",
    fixDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/601164/chapter-389-taking-the-low-road",
    fixDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/605224/chapter-390-deep-politics",
    fixDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/14167/metaworld-chronicles/chapter/623067/chapter-396-bait-and-switch",
    fixDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/407352/22-the-waiting-maw",
    unwrapToplevelDivs,
  ],
  [
    "https://www.royalroad.com/fiction/26675/a-journey-of-black-and-red/chapter/426349/34-ring-breaker",
    fixNestedDivParagraphs,
  ],
  [
    "https://www.royalroad.com/fiction/36735/the-perfect-run/chapter/576217/8-past-fragment-len",
    fixBlockquoteAndDiv,
  ],
  [
    "https://www.royalroad.com/fiction/41033/kairos-a-greek-myth-litrpg/chapter/677603/26-the-wedding",
    unwrapToplevelDivsAlt,
  ],
  [
    "https://www.royalroad.com/fiction/47557/underland/chapter/775480/8-vernburg",
    unwrapToplevelDivs,
  ],
  // Generic RoyalRoad fix (applies to all RR chapters)
  ["https://www.royalroad.com/", removePiracyParagraphs],
];

/**
 * Apply all matching chapter fixes for a given URL.
 * Multiple fixes can match (e.g., a specific chapter fix + the generic RR fix).
 */
export function applyChapterFixes(
  chapterUrl: string,
  $: CheerioAPI,
  contentEl: Cheerio<AnyNode>,
  contentElSelector: string,
): void {
  for (const [urlPrefix, fix] of CHAPTER_FIXES) {
    if (chapterUrl.startsWith(urlPrefix)) {
      fix($, contentEl, contentElSelector);
    }
  }
}
