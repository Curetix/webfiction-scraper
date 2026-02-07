import yaml from "js-yaml";
import { join, isAbsolute, basename } from "node:path";
import { readFileSync, existsSync } from "node:fs";
import { v5 as uuidv5 } from "uuid";
import {
  FictionConfigSchema,
  ClientConfigSchema,
  type FictionConfig,
  type ClientConfig,
  type ResolvedFictionConfig,
  type ResolvedFiles,
} from "./schema.ts";
import { BASE_DIR, DATA_DIR, CONFIGS_DIR, normalizeString, lowercaseClean } from "@/utils.ts";
import { ConfigValidationError } from "@/errors.ts";

const UUID_NAMESPACE = "6ba7b810-9dad-11d1-80b4-00c04fd430c8"; // DNS namespace

/**
 * Load the client configuration file (client.yaml) from the base data directory.
 */
export function loadClientConfig(): ClientConfig {
  const path = join(BASE_DIR, "client.yaml");

  if (!existsSync(path)) {
    return { patreonSessionCookie: null, configOverrides: {}, monitoredFictions: [] };
  }

  const raw = readFileSync(path, "utf-8");
  const parsed = yaml.load(raw) as Record<string, unknown>;

  // Convert camelCase keys from YAML (the YAML files use camelCase already)
  const result = ClientConfigSchema.safeParse(parsed);
  if (!result.success) {
    throw new ConfigValidationError(
      `Client config validation failed:\n${JSON.stringify(result.error.issues, null, 2)}`,
    );
  }

  return result.data;
}

/**
 * Deep merge two objects. Values from `source` override `target`.
 */
function deepMerge(
  target: Record<string, unknown>,
  source: Record<string, unknown>,
): Record<string, unknown> {
  const result = { ...target };
  for (const [key, value] of Object.entries(source)) {
    if (
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      target[key] &&
      typeof target[key] === "object" &&
      !Array.isArray(target[key])
    ) {
      result[key] = deepMerge(
        target[key] as Record<string, unknown>,
        value as Record<string, unknown>,
      );
    } else {
      result[key] = value;
    }
  }
  return result;
}

/**
 * Resolve the path for a config name (without extension).
 */
export function getFictionConfigPath(configName: string): string {
  return join(CONFIGS_DIR, `${configName}.yaml`);
}

/**
 * Load and validate a fiction configuration from a YAML file.
 * Applies client config overrides, generates identifier if missing, resolves all file paths.
 */
export function loadFictionConfig(
  configName: string,
  clientConfig: ClientConfig,
): ResolvedFictionConfig | null {
  let path: string | null = null;
  let resolvedConfigName = configName;

  if (existsSync(configName) && configName.endsWith(".yaml")) {
    path = configName;
    resolvedConfigName = basename(configName).replace(".yaml", "");
  } else {
    const p = getFictionConfigPath(configName);
    if (existsSync(p)) {
      path = p;
    }
  }

  if (!path) {
    console.error("Couldn't find config file!");
    return null;
  }

  if (!path.endsWith(".yaml")) {
    console.error("Invalid file extension, only .yaml is supported!");
    return null;
  }

  const raw = readFileSync(path, "utf-8");
  let parsed = yaml.load(raw) as Record<string, unknown>;

  // Apply client config overrides
  const overrides = clientConfig.configOverrides;
  const override = overrides?.[resolvedConfigName.toLowerCase()];
  if (override && typeof override === "object") {
    parsed = deepMerge(parsed, override as Record<string, unknown>);
  }

  // Validate against schema
  const result = FictionConfigSchema.safeParse(parsed);
  if (!result.success) {
    console.error(`\nValidation failed for config '${resolvedConfigName}':`);
    for (const issue of result.error.issues) {
      console.error(`  - ${issue.path.join(".")}: ${issue.message}`);
    }
    return null;
  }

  const config = result.data;
  const metadata = config.metadata;
  const title = normalizeString(metadata.title);

  // Auto-generate identifier if not set
  if (!metadata.identifier) {
    const identString = `${lowercaseClean(metadata.author)}-${lowercaseClean(metadata.title)}`;
    metadata.identifier = uuidv5(identString, UUID_NAMESPACE);
  }

  // Resolve file paths
  let workingFolder = config.files?.workingFolder;
  if (!workingFolder) {
    workingFolder = join(DATA_DIR, resolvedConfigName);
  } else if (!isAbsolute(workingFolder)) {
    workingFolder = join(DATA_DIR, workingFolder);
  }

  const cacheFolder = join(workingFolder, "cache");
  const bookFolder = join(workingFolder, "book");
  const manifestFile = join(workingFolder, "manifest.json");

  let epubFile = config.files?.epubFile;
  if (!epubFile) {
    epubFile = join(workingFolder, `${title}.epub`);
  } else if (!isAbsolute(epubFile)) {
    epubFile = join(workingFolder, epubFile);
  }

  let coverFile = config.files?.coverFile ?? "";
  if (!coverFile) {
    coverFile = join(workingFolder, "cover.jpg");
  } else {
    // Check if it's a URL
    try {
      const url = new URL(coverFile);
      if (url.protocol === "http:" || url.protocol === "https:") {
        // Keep as-is (URL)
      } else if (!isAbsolute(coverFile)) {
        coverFile = join(workingFolder, coverFile);
      }
    } catch {
      // Not a URL
      if (!isAbsolute(coverFile)) {
        coverFile = join(workingFolder, coverFile);
      }
    }
  }

  const resolvedFiles: ResolvedFiles = {
    workingFolder,
    cacheFolder,
    bookFolder,
    manifestFile,
    epubFile,
    coverFile,
    ebookFormats: config.files?.ebookFormats ?? [],
    copyBookTo: config.files?.copyBookTo ?? "",
  };

  return {
    ...config,
    files: resolvedFiles,
  };
}
