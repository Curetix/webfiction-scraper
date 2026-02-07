import type { ManifestEntry } from "@/config/schema.ts";
import { existsSync } from "node:fs";

/**
 * JSON-backed chapter tracking list.
 * Each entry records a chapter's title, file path, conversion status, and source URL.
 */
export class Manifest {
  public entries: ManifestEntry[] = [];

  constructor(public readonly path: string) {
    this.load();
  }

  /** Load manifest entries from the JSON file on disk. */
  load(): void {
    if (!existsSync(this.path)) return;
    try {
      const raw = JSON.parse(
        require("node:fs").readFileSync(this.path, "utf-8"),
      );
      if (Array.isArray(raw)) {
        this.entries = raw as ManifestEntry[];
      }
    } catch {
      console.error(
        "Manifest could not be loaded. You might need to use the --clean-download flag.",
      );
    }
  }

  /** Persist the manifest to disk as a JSON file. */
  save(): void {
    require("node:fs").writeFileSync(
      this.path,
      JSON.stringify(this.entries, null, 2),
      "utf-8",
    );
  }

  /** Get an entry by index. */
  getEntry(index: number): ManifestEntry | undefined {
    return this.entries[index];
  }

  /** Find an entry by its source URL. */
  findByUrl(url: string): ManifestEntry | undefined {
    return this.entries.find((e) => e.url === url);
  }

  /** Mark a chapter as converted by its index. */
  markConverted(index: number): void {
    const entry = this.entries[index];
    if (entry) {
      entry.converted = true;
    }
  }

  /** Add or update an entry. */
  setEntry(index: number, entry: ManifestEntry): void {
    this.entries[index] = entry;
  }

  /** Number of entries. */
  get length(): number {
    return this.entries.length;
  }

  /** Clear all entries. */
  clear(): void {
    this.entries = [];
  }
}
