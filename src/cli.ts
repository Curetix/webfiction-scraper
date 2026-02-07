#!/usr/bin/env bun
import { defineCommand, runMain } from "citty";
import { FictionScraperClient } from "@/client.ts";

// ---------------------------------------------------------------------------
// Subcommands
// ---------------------------------------------------------------------------

const runCommand = defineCommand({
  meta: {
    name: "run",
    description:
      "Run the scraper with the provided config name. Can be a path to a YAML file, a built-in config name, or a config inside the configs/ directory.",
  },
  args: {
    config: {
      type: "positional",
      description: "Config name or path to a YAML config file",
      required: true,
    },
    download: {
      type: "boolean",
      description: "Download chapters",
      default: true,
    },
    cleanDownload: {
      type: "boolean",
      description: "Clear existing downloaded chapters before downloading",
      default: false,
    },
    convert: {
      type: "boolean",
      description: "Convert chapters",
      default: true,
    },
    cleanConvert: {
      type: "boolean",
      description: "Clear existing converted chapters before converting",
      default: false,
    },
    bind: {
      type: "boolean",
      description: "Bind chapters into an EPUB eBook",
      default: true,
    },
    ebookConvert: {
      type: "boolean",
      description: "Create eBook formats specified in the config",
      default: true,
    },
  },
  async run({ args }) {
    const client = new FictionScraperClient();
    await client.run(args.config, {
      download: args.download,
      cleanDownload: args.cleanDownload,
      convert: args.convert,
      cleanConvert: args.cleanConvert,
      bind: args.bind,
      ebookConvert: args.ebookConvert,
    });
  },
});

const listCommand = defineCommand({
  meta: {
    name: "list",
    description: "List all detected fiction configs",
  },
  args: {
    remote: {
      type: "boolean",
      description: "List configs from the remote repository",
      alias: "r",
      default: false,
    },
  },
  async run({ args }) {
    const configs = await FictionScraperClient.listFictionConfigs(args.remote);

    if (args.remote && !configs) {
      console.log("Could not get repository contents.");
    } else if (!configs || configs.length === 0) {
      console.log("No configs available.");
    } else {
      console.log("Available configs:");
      for (const c of configs) {
        console.log(`  ${c}`);
      }
    }
  },
});

const downloadCommand = defineCommand({
  meta: {
    name: "download",
    description: "Download a config from the remote repository",
  },
  args: {
    config: {
      type: "positional",
      description: "Name of the config to download",
      required: false,
    },
    all: {
      type: "boolean",
      description: "Download all available remote configs",
      alias: "a",
      default: false,
    },
    overwrite: {
      type: "boolean",
      description: "Overwrite configs that already exist locally",
      alias: "o",
      default: false,
    },
  },
  async run({ args }) {
    const client = new FictionScraperClient();

    if (!args.config && !args.all) {
      console.log(
        "Either the config name argument or the --all option is required.",
      );
      return;
    }

    if (args.all) {
      const configs = await FictionScraperClient.listFictionConfigs(true);
      if (!configs) {
        console.error("Could not fetch remote configs.");
        return;
      }

      let downloaded = 0;
      for (const c of configs) {
        const success = await client.downloadFictionConfig(c, args.overwrite);
        if (success) {
          downloaded++;
        } else {
          console.error(`Downloading config ${c} was not successful.`);
        }
      }
      console.log(`Downloaded ${downloaded} configs!`);
    } else if (args.config) {
      const success = await client.downloadFictionConfig(
        args.config,
        args.overwrite,
      );
      if (!success) {
        console.log("Download was not successful.");
        return;
      }
      console.log(`Config ${args.config} was downloaded!`);
    }
  },
});

const generateCommand = defineCommand({
  meta: {
    name: "generate",
    description:
      "Generate a config file from a supported site URL (RoyalRoad, FictionPress)",
  },
  args: {
    url: {
      type: "positional",
      description:
        "URL of the fiction overview page or a chapter (used as startUrl)",
      required: true,
    },
    name: {
      type: "string",
      description: "Custom name for the config file",
      alias: "n",
    },
  },
  async run({ args }) {
    await FictionScraperClient.generateFictionConfig(
      args.url,
      args.name,
    );
  },
});

const pathsCommand = defineCommand({
  meta: {
    name: "paths",
    description: "Print all paths used by the scraper",
  },
  run() {
    FictionScraperClient.printPaths();
  },
});

const cleanCommand = defineCommand({
  meta: {
    name: "clean",
    description:
      "Delete files in the data directory to clean up disk space. Specify folder selection and what to delete.",
  },
  args: {
    allFolders: {
      type: "boolean",
      description: "Select all config folders",
      default: false,
    },
    config: {
      type: "string",
      description: "Select a specific config folder",
      alias: "c",
    },
    orphanFolders: {
      type: "boolean",
      description:
        "Select config folders without a corresponding config file",
      default: false,
    },
    everything: {
      type: "boolean",
      description: "Delete the entire folder",
      alias: "e",
      default: false,
    },
    downloads: {
      type: "boolean",
      description: "Delete downloaded chapters AND converted chapters",
      alias: "d",
      default: false,
    },
    converted: {
      type: "boolean",
      description: "Delete converted chapters",
      default: false,
    },
    books: {
      type: "boolean",
      description: "Delete books",
      alias: "b",
      default: false,
    },
    misc: {
      type: "boolean",
      description:
        "Delete files that do not match other filters (e.g. downloaded covers)",
      alias: "m",
      default: false,
    },
    dryRun: {
      type: "boolean",
      description: "Do not perform any file system operations",
      default: false,
    },
  },
  run({ args }) {
    const client = new FictionScraperClient();
    client.cleanSpace({
      allFolders: args.allFolders,
      orphanFolders: args.orphanFolders,
      configFolders: args.config ? [args.config] : [],
      everything: args.everything,
      downloads: args.downloads,
      converted: args.converted,
      books: args.books,
      misc: args.misc,
      dryRun: args.dryRun,
    });
  },
});

const interactiveCommand = defineCommand({
  meta: {
    name: "interactive",
    description: "Start the scraper interactively with a menu",
  },
  async run() {
    // Dynamic import to avoid loading @inquirer/prompts unless needed
    const { select, checkbox, confirm, input } = await import(
      "@inquirer/prompts"
    );
    const { loadFictionConfig } = await import("@/config/loader.ts");

    const client = new FictionScraperClient();

    const runInteractive = async () => {
      const configs =
        (await FictionScraperClient.listFictionConfigs(false)) ?? [];

      type Choice = { name: string; value: string; disabled?: string };
      const configChoices: Choice[] = [];

      for (const configName of configs) {
        try {
          const config = loadFictionConfig(configName, client.clientConfig);
          if (config) {
            configChoices.push({
              name: config.metadata.title,
              value: `config:${configName}`,
            });
          }
        } catch (error) {
          console.error(
            `Error loading config '${configName}': ${error instanceof Error ? error.message : error}`,
          );
        }
      }

      configChoices.sort((a, b) => a.name.localeCompare(b.name));

      const allChoices = [
        { name: "Download config(s)", value: "download" },
        { name: "Generate new config", value: "generate" },
        // separator
        { name: "────────────────────", value: "_sep", disabled: "" },
        ...(configChoices.length > 0
          ? configChoices
          : [{ name: "None", value: "_none", disabled: "No configs found" }]),
      ];

      const selected = await select({
        message: "What do you want to do or which config do you want to run?",
        choices: allChoices,
      });

      if (!selected || selected === "_sep" || selected === "_none") return;

      if (selected === "download") {
        const remoteConfigs =
          (await FictionScraperClient.listFictionConfigs(true)) ?? [];

        const choices = [
          { name: `All (${remoteConfigs.length}) configs`, value: "all" },
          ...remoteConfigs.map((c) => ({
            name: c,
            value: `config:${c}`,
          })),
        ];

        const toDownload = await checkbox({
          message: "Which configs do you want to download?",
          choices,
        });

        if (!toDownload || toDownload.length === 0) return;

        if (toDownload.includes("all")) {
          for (const c of remoteConfigs) {
            await client.downloadFictionConfig(c);
          }
        } else {
          for (const c of toDownload) {
            const name = c.replace("config:", "");
            await client.downloadFictionConfig(name);
          }
        }
      } else if (selected === "generate") {
        const url = await input({
          message:
            "What's the URL of the web fiction or the first chapter?",
        });
        const name = await input({
          message:
            "What do you want to name the config? (Optional, press Enter for default)",
        });

        await FictionScraperClient.generateFictionConfig(
          url,
          name || undefined,
        );
      } else if (selected.startsWith("config:")) {
        const configName = selected.replace("config:", "");

        const tasks = await checkbox({
          message: "Which tasks do you want to run?",
          choices: [
            {
              name: "Download chapters",
              value: "download",
              checked: true,
            },
            {
              name: "Clean download chapters",
              value: "cleanDownload",
              checked: false,
            },
            {
              name: "Convert chapters",
              value: "convert",
              checked: true,
            },
            {
              name: "Clean convert chapters",
              value: "cleanConvert",
              checked: false,
            },
            {
              name: "Bind chapters into eBook",
              value: "bind",
              checked: true,
            },
            {
              name: "Create eBook formats specified in the config",
              value: "format",
              checked: false,
            },
          ],
        });

        if (!tasks || tasks.length === 0) return;

        await client.run(configName, {
          download: tasks.includes("download"),
          cleanDownload: tasks.includes("cleanDownload"),
          convert: tasks.includes("convert"),
          cleanConvert: tasks.includes("cleanConvert"),
          bind: tasks.includes("bind"),
          ebookConvert: tasks.includes("format"),
        });
      }

      const returnToMenu = await confirm({
        message: "Do you want to return to the main menu?",
      });
      if (returnToMenu) {
        await runInteractive();
      }
    };

    await runInteractive();
  },
});

// ---------------------------------------------------------------------------
// Main command
// ---------------------------------------------------------------------------

const main = defineCommand({
  meta: {
    name: "webfiction-scraper",
    version: "2.0.0",
    description: "Download web fiction and convert it to EPUB e-books",
  },
  subCommands: {
    run: runCommand,
    interactive: interactiveCommand,
    list: listCommand,
    download: downloadCommand,
    generate: generateCommand,
    paths: pathsCommand,
    clean: cleanCommand,
  },
});

runMain(main);
