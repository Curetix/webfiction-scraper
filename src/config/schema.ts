import { z } from "zod/v4";

// ---------------------------------------------------------------------------
// Dublin Core metadata keys
// ---------------------------------------------------------------------------

export const OPTIONAL_DC_KEYS = [
  "contributor",
  "coverage",
  "creator",
  "date",
  "description",
  "format",
  "identifier",
  "language",
  "publisher",
  "relation",
  "rights",
  "source",
  "subject",
  "type",
] as const;

export const DC_KEYS = ["author", "title", ...OPTIONAL_DC_KEYS] as const;

// ---------------------------------------------------------------------------
// Fiction config schema
// ---------------------------------------------------------------------------

const SubstitutionSchema = z.object({
  selectorType: z.enum(["css", "regex", "text"]),
  selector: z.string(),
  chapterUrl: z.string().optional().default(""),
  replaceWith: z.string().optional().default(""),
  warn: z.boolean().optional().default(true),
});

const ContentStartElementSchema = z.object({
  chapterUrl: z.string(),
  selector: z.string(),
});

const SelectorsSchema = z.object({
  titleElement: z.string(),
  contentElement: z.string(),
  nextChapterElement: z.string(),
  contentStartElement: z.array(ContentStartElementSchema).nullable().optional().default(null),
  cutOffElement: z.union([z.string(), z.array(z.string())]).nullable().optional().default(null),
});

const FilesSchema = z
  .object({
    workingFolder: z.string().optional(),
    coverFile: z.string().optional(),
    epubFile: z.string().optional(),
    ebookFormats: z.array(z.string()).optional().default([]),
    copyBookTo: z.string().optional().default(""),
  })
  .optional()
  .default({ ebookFormats: [], copyBookTo: "" });

const MetadataSchema = z
  .object({
    title: z.string(),
    author: z.string(),
    language: z
      .string()
      .refine((s) => s.length === 2, "Language must be a 2-character code")
      .optional()
      .default("en"),
    publisher: z.string().optional().default("Web Fiction Scraper"),
  })
  .catchall(z.string());

export const FictionConfigSchema = z.object({
  officialBookUrl: z.union([z.string(), z.array(z.string())]).optional(),
  startUrl: z.string().refine((s) => s.startsWith("http"), "startUrl must begin with http"),
  endUrl: z
    .string()
    .optional()
    .default(""),
  skipUrls: z.array(z.string()).optional().default([]),
  crawlerModule: z.string().optional().default("Crawler"),
  metadata: MetadataSchema,
  files: FilesSchema,
  selectors: SelectorsSchema,
  skipConversion: z.boolean().optional().default(false),
  removeEmptyElements: z.boolean().optional().default(true),
  substitutions: z.array(SubstitutionSchema).optional().default([]),
  style: z.string().nullable().optional().default(null),
});

export type FictionConfig = z.infer<typeof FictionConfigSchema>;

// ---------------------------------------------------------------------------
// Resolved fiction config — after path resolution (internal use)
// ---------------------------------------------------------------------------

export interface ResolvedFiles {
  workingFolder: string;
  cacheFolder: string;
  bookFolder: string;
  manifestFile: string;
  epubFile: string;
  coverFile: string;
  ebookFormats: string[];
  copyBookTo: string;
}

export interface ResolvedFictionConfig extends Omit<FictionConfig, "files"> {
  files: ResolvedFiles;
}

// ---------------------------------------------------------------------------
// Client config schema
// ---------------------------------------------------------------------------

const MonitoredFictionSchema = z.object({
  rssFeedUrl: z.string().refine((s) => s.startsWith("http"), "RSS feed URL must begin with http"),
  configName: z.string(),
});

export const ClientConfigSchema = z.object({
  patreonSessionCookie: z.string().nullable().optional().default(null),
  configOverrides: z.record(z.string(), z.any()).optional().default({}),
  monitoredFictions: z.array(MonitoredFictionSchema).optional().default([]),
});

export type ClientConfig = z.infer<typeof ClientConfigSchema>;

// ---------------------------------------------------------------------------
// Manifest entry
// ---------------------------------------------------------------------------

export interface ManifestEntry {
  title: string;
  file: string;
  converted: boolean;
  url: string;
}

// ---------------------------------------------------------------------------
// XHTML chapter template
// ---------------------------------------------------------------------------

export const CHAPTER_DOC = `<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
<head>
<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" />
</head>
<body></body>
</html>
`;
