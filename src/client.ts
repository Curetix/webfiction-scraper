import yaml from "js-yaml";
import { join, basename, dirname } from "node:path";
import {
  existsSync,
  readdirSync,
  rmSync,
  writeFileSync,
  mkdirSync,
  readFileSync,
  statSync,
  copyFileSync,
} from "node:fs";

import { Crawler } from "@/crawler/crawler.ts";
import { WanderingInnPatreonCrawler } from "@/crawler/wandering-inn.ts";
import { Converter } from "@/converter.ts";
import { Binder } from "@/binder.ts";
import { RoyalRoadConfigGenerator } from "@/generator/royalroad.ts";
import { FictionPressGenerator } from "@/generator/fiction-press.ts";
import { Manifest } from "@/manifest.ts";
import {
  FictionConfigSchema,
  type ClientConfig,
  type ResolvedFictionConfig,
} from "@/config/schema.ts";
import {
  loadClientConfig,
  loadFictionConfig,
  getFictionConfigPath,
} from "@/config/loader.ts";
import {
  BASE_DIR,
  DATA_DIR,
  CONFIGS_DIR,
  normalizeString,
  ensureDir,
} from "@/utils.ts";

const SEPARATOR = "-".repeat(30) + "\n";

/** Valid filename characters pattern */
const VALID_FILENAME_RE = /[^a-zA-Z0-9\-_ ]/g;

/**
 * Main orchestrator for the Web Fiction Scraper.
 * Manages config loading, task dispatching, and file management.
 */
export class FictionScraperClient {
  public clientConfig: ClientConfig;

  constructor() {
    this.initDirectories();
    this.clientConfig = loadClientConfig();
  }

  /** Create required data directories. */
  private initDirectories(): void {
    ensureDir(DATA_DIR);
    ensureDir(CONFIGS_DIR);
  }

  /** Print application paths. */
  static printPaths(): void {
    console.log(`Base: ${BASE_DIR}`);
    console.log(`Client config: ${join(BASE_DIR, "client.yaml")}`);
    console.log(`Fiction configs: ${CONFIGS_DIR}`);
    console.log(`Data (downloads, books): ${DATA_DIR}`);
  }

  /** Download and cache the fiction config JSON schema from GitHub. */
  static async getFictionConfigSchema(): Promise<unknown | null> {
    const filePath = join(BASE_DIR, "fiction_config.schema.json");
    if (!existsSync(filePath)) {
      const response = await fetch(
        "https://raw.githubusercontent.com/Curetix/webfiction-scraper-configs/main/schema/fiction_config.schema.json",
      );
      if (response.ok) {
        const text = await response.text();
        writeFileSync(filePath, text, "utf-8");
        return JSON.parse(text);
      }
      return null;
    }
    return JSON.parse(readFileSync(filePath, "utf-8"));
  }

  /**
   * Run the scraper pipeline with the given config and task flags.
   */
  async run(
    configName: string,
    options: {
      download?: boolean;
      cleanDownload?: boolean;
      convert?: boolean;
      cleanConvert?: boolean;
      bind?: boolean;
      ebookConvert?: boolean;
    },
  ): Promise<void> {
    const {
      download = false,
      cleanDownload = false,
      convert = false,
      cleanConvert = false,
      bind = false,
      ebookConvert = false,
    } = options;

    const config = loadFictionConfig(configName, this.clientConfig);

    if (!config) {
      console.error("Invalid config file!");
      process.exit(1);
    }

    // Ensure working directories exist
    ensureDir(config.files.workingFolder);
    ensureDir(config.files.cacheFolder);
    ensureDir(config.files.bookFolder);

    // Show official book notice
    const officialUrl = config.officialBookUrl;
    if (officialUrl) {
      console.log(
        `The author ${config.metadata.author} has published an official book for ${config.metadata.title}!`,
      );
      console.log(
        "If you want to support their work, consider purchasing it here:",
      );
      if (typeof officialUrl === "string") {
        console.log(` ${officialUrl}`);
      } else if (Array.isArray(officialUrl)) {
        for (const u of officialUrl) {
          console.log(` - ${u}`);
        }
      }
    }

    // Download
    if (download || cleanDownload) {
      console.log("Downloading chapters...");

      let crawler: Crawler;
      if (config.crawlerModule === "WanderingInnPatreonCrawler") {
        crawler = new WanderingInnPatreonCrawler(
          config,
          this.clientConfig.patreonSessionCookie,
        );
      } else {
        crawler = new Crawler(config);
      }

      if (cleanDownload) {
        crawler.clean();
      }
      await crawler.startDownload();
    }

    // Convert
    if (convert || cleanConvert || cleanDownload) {
      console.log(SEPARATOR + "Converting chapters...");
      const converter = new Converter(config);
      if (cleanDownload || cleanConvert) {
        converter.clean();
      }
      await converter.convertAll();
    }

    // Bind
    if (bind) {
      console.log(SEPARATOR + "Binding chapters into eBook...");
      const binder = new Binder(config);
      await binder.bindBook();
    }

    // Ebook convert (via Calibre's ebook-convert CLI)
    if (ebookConvert && config.files.ebookFormats.length > 0) {
      console.log(SEPARATOR + "Creating other eBook formats...");
      for (const format of config.files.ebookFormats) {
        console.log(`Converting epub into ${format}`);
        const outFile = config.files.epubFile.replace(".epub", `.${format}`);
        const proc = Bun.spawnSync(["ebook-convert", config.files.epubFile, outFile]);
        if (!proc.success) {
          console.error(
            `ebook-convert failed: ${proc.stderr.toString()}`,
          );
        }
      }
    }

    // Copy files
    if (config.files.copyBookTo) {
      console.log(SEPARATOR + "Copying files...");
      const formats = ["epub", ...config.files.ebookFormats];
      for (const format of formats) {
        const source = config.files.epubFile.replace(".epub", `.${format}`);
        const target = config.files.copyBookTo.replace(".epub", `.${format}`);
        if (existsSync(source)) {
          const targetDir = dirname(target);
          if (existsSync(targetDir)) {
            copyFileSync(source, target);
            console.log(`Copied ${basename(source)} to ${targetDir}`);
          } else {
            console.error(
              "Couldn't copy eBook to specified path, directory not found!",
            );
          }
        } else {
          console.error(`${source} not found!`);
        }
      }
    }
  }

  /**
   * Generate a fiction config from a supported site URL.
   */
  static async generateFictionConfig(
    url: string,
    name?: string,
  ): Promise<string> {
    let fullUrl = url;
    if (!fullUrl.startsWith("http")) {
      fullUrl = "https://" + fullUrl;
    }

    const parsed = new URL(fullUrl);
    const domain = parsed.hostname;

    let generator;
    if (domain === "royalroad.com" || domain === "www.royalroad.com") {
      console.log("Detected Royal Road URL!");
      generator = new RoyalRoadConfigGenerator(fullUrl);
    } else if (
      domain === "fictionpress.com" ||
      domain === "www.fictionpress.com"
    ) {
      console.log("Detected FictionPress URL!");
      generator = new FictionPressGenerator(fullUrl);
    } else {
      console.error("Invalid URL or site not supported!");
      process.exit(1);
    }

    const config = await generator.generate();

    if (!name) {
      name = config.metadata["title"] ?? "unknown";
    }

    // Validate generated config
    const validation = FictionConfigSchema.safeParse(config);
    if (!validation.success) {
      console.warn("Warning: generated config has validation issues:");
      for (const issue of validation.error.issues) {
        console.warn(`  - ${issue.path.join(".")}: ${issue.message}`);
      }
    }

    // Save config
    const safeFileName = name.replace(VALID_FILENAME_RE, "");
    const configPath = join(CONFIGS_DIR, `${safeFileName}.yaml`);
    const yamlStr = yaml.dump(config, { lineWidth: 120, quotingType: '"' });
    writeFileSync(configPath, yamlStr, "utf-8");

    console.log(
      `Config for "${config.metadata["title"]}" successfully generated and saved!`,
    );

    return name;
  }

  /**
   * List available fiction configs (local or remote from GitHub).
   */
  static async listFictionConfigs(remote = false): Promise<string[] | null> {
    if (remote) {
      const response = await fetch(
        "https://api.github.com/repos/curetix/webfiction-scraper-configs/contents/configs",
      );

      if (response.ok) {
        const json = (await response.json()) as Array<{ name: string }>;
        return json
          .filter((c) => c.name.endsWith(".yaml"))
          .map((c) => c.name.replace(".yaml", ""));
      }
      return null;
    }

    if (existsSync(CONFIGS_DIR)) {
      return readdirSync(CONFIGS_DIR)
        .filter((f) => f.endsWith(".yaml"))
        .map((f) => f.replace(".yaml", ""));
    }
    return null;
  }

  /**
   * Download a fiction config from the GitHub configs repository.
   */
  async downloadFictionConfig(
    name: string,
    overwrite = false,
  ): Promise<string | null> {
    const filePath = getFictionConfigPath(name);
    const fileExists = existsSync(filePath);

    if (fileExists && !overwrite) {
      console.log(
        `The file ${filePath} already exists in the configs folder. Skipping download.`,
      );
      return null;
    } else if (fileExists && overwrite) {
      console.log(
        `The file ${filePath} already exists in the configs folder and will be overwritten.`,
      );
    }

    const response = await fetch(
      `https://raw.githubusercontent.com/Curetix/webfiction-scraper-configs/main/configs/${name}.yaml`,
    );

    if (response.ok) {
      const content = await response.text();
      writeFileSync(filePath, content, "utf-8");
      return filePath;
    }

    console.error(`Failed to download config '${name}'`);
    return null;
  }

  /**
   * Clean up disk space by removing cached/converted/book files.
   */
  cleanSpace(options: {
    allFolders?: boolean;
    orphanFolders?: boolean;
    configFolders?: string[];
    everything?: boolean;
    downloads?: boolean;
    converted?: boolean;
    books?: boolean;
    misc?: boolean;
    dryRun?: boolean;
  }): void {
    const {
      allFolders = false,
      orphanFolders = false,
      configFolders = [],
      everything = false,
      downloads = false,
      converted = false,
      books = false,
      misc = false,
      dryRun = false,
    } = options;

    let configs: string[] | null = null;
    if (orphanFolders) {
      // We need the synchronous version here
      if (existsSync(CONFIGS_DIR)) {
        configs = readdirSync(CONFIGS_DIR)
          .filter((f) => f.endsWith(".yaml"))
          .map((f) => f.replace(".yaml", ""));
      }
      if (configs === null) {
        console.log(
          "Could not load fiction configs files, stopping because orphanFolders was passed.",
        );
        return;
      }
    }

    if (!existsSync(DATA_DIR)) return;

    const removeFn = (filePath: string) => {
      if (!dryRun) {
        console.log(`Deleting file ${filePath}`);
        rmSync(filePath, { force: true });
      } else {
        console.log(`Skipped deleting file ${filePath}`);
      }
    };

    const rmtreeFn = (dirPath: string) => {
      if (!dryRun) {
        console.log(`Deleting folder ${dirPath}`);
        rmSync(dirPath, { recursive: true, force: true });
      } else {
        console.log(`Skipped deleting folder ${dirPath}`);
      }
    };

    for (const f of readdirSync(DATA_DIR)) {
      const path = join(DATA_DIR, f);
      if (!statSync(path).isDirectory()) continue;

      if (!allFolders && !orphanFolders && !configFolders.includes(f))
        continue;
      if (orphanFolders && configs?.includes(f)) continue;

      if (everything) {
        rmtreeFn(path);
        continue;
      }

      for (const cf of readdirSync(path)) {
        const cfPath = join(path, cf);

        if (downloads && cf === "cache") {
          rmtreeFn(cfPath);
        } else if ((downloads || converted) && cf === "book") {
          rmtreeFn(cfPath);
        } else if (
          (books && cf.endsWith(".epub")) ||
          (misc && cf !== "manifest.json")
        ) {
          if (statSync(cfPath).isFile()) {
            removeFn(cfPath);
          } else if (statSync(cfPath).isDirectory()) {
            rmtreeFn(cfPath);
          }
        } else if (cf === "manifest.json") {
          if (downloads) {
            removeFn(cfPath);
          } else if (converted) {
            const manifest = new Manifest(cfPath);
            for (let i = 0; i < manifest.length; i++) {
              const entry = manifest.entries[i];
              if (entry) {
                entry.converted = false;
              }
            }
            manifest.save();
          }
        }
      }

      // Remove empty directories
      try {
        if (readdirSync(path).length === 0) {
          rmtreeFn(path);
        }
      } catch {
        // Directory may have been removed already
      }
    }
  }
}
