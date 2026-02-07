import envPaths from "env-paths";
import { join } from "node:path";
import { mkdirSync } from "node:fs";

const paths = envPaths("WebFictionScraper", { suffix: "" });

/** Base application data directory */
export const BASE_DIR = paths.data;

/** Directory where fiction working data is stored */
export const DATA_DIR = join(BASE_DIR, "data");

/** Directory where fiction config YAML files are stored */
export const CONFIGS_DIR = join(BASE_DIR, "configs");

/** Characters valid in filenames */
export const VALID_FILENAME_CHARS = /[a-zA-Z0-9\-_ ]/g;

/**
 * Keep only alphanumeric + spaces, strip edges, collapse double spaces.
 */
export function normalizeString(s: string): string {
  return s
    .replace(/[^a-zA-Z0-9 ]/g, "")
    .trim()
    .replace(/ {2,}/g, " ");
}

/**
 * Keep only alphanumeric, lowercase.
 */
export function lowercaseClean(s: string): string {
  return s.replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
}

/**
 * Ensure a directory exists, creating it recursively if needed.
 */
export function ensureDir(path: string): void {
  mkdirSync(path, { recursive: true });
}
