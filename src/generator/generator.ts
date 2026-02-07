/**
 * Base config generator.
 * Subclasses override getMetadata() and getSelectors() to auto-generate
 * fiction config from a URL.
 */
export interface GeneratedConfig {
  startUrl: string;
  endUrl?: string;
  metadata: Record<string, string>;
  selectors: Record<string, string>;
  files?: Record<string, string>;
}

export abstract class ConfigGenerator {
  protected config: GeneratedConfig;

  constructor(startUrl: string, endUrl?: string) {
    this.config = {
      startUrl,
      ...(endUrl ? { endUrl } : {}),
      metadata: {},
      selectors: {},
    };
  }

  /** Generate the full config by fetching site data. */
  async generate(): Promise<GeneratedConfig> {
    this.config.metadata = await this.getMetadata();
    this.config.selectors = this.getSelectors();
    return this.config;
  }

  getConfig(): GeneratedConfig {
    return this.config;
  }

  /** Override in subclasses to scrape metadata from the fiction page. */
  protected async getMetadata(): Promise<Record<string, string>> {
    return {};
  }

  /** Override in subclasses to return site-specific CSS selectors. */
  protected getSelectors(): Record<string, string> {
    return {};
  }
}
