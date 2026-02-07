export class ElementNotFoundException extends Error {
  constructor(message?: string) {
    super(message ?? "Element not found");
    this.name = "ElementNotFoundException";
  }
}

export class InvalidPageException extends Error {
  constructor(message?: string) {
    super(message ?? "Invalid page");
    this.name = "InvalidPageException";
  }
}

export class ConfigValidationError extends Error {
  constructor(message?: string) {
    super(message ?? "Config validation failed");
    this.name = "ConfigValidationError";
  }
}

export class NetworkError extends Error {
  constructor(
    message?: string,
    public statusCode?: number,
  ) {
    super(message ?? "Network request failed");
    this.name = "NetworkError";
  }
}
