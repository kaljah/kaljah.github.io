declare module "papaparse" {
  export interface ParseMeta {
    delimiter: string;
    linebreak: string;
    aborted: boolean;
    fields?: string[];
    truncated: boolean;
    cursor: number;
  }

  export interface ParseError {
    type: string;
    code: string;
    message: string;
    row: number;
    index: number;
  }

  export interface ParseResult<T = any> {
    data: T[];
    errors: ParseError[];
    meta: ParseMeta;
  }

  export interface ParseConfig<T = any> {
    delimiter?: string;
    newline?: string;
    quoteChar?: string;
    escapeChar?: string;
    header?: boolean;
    transformHeader?: (header: string, index: number) => string;
    dynamicTyping?: boolean;
    preview?: number;
    encoding?: string;
    worker?: boolean;
    comments?: boolean | string;
    step?: (results: ParseResult<T>, parser: any) => void;
    complete?: (results: ParseResult<T>, file?: any) => void;
    error?: (error: ParseError, file?: any) => void;
    download?: boolean;
    downloadRequestHeaders?: { [headerName: string]: string };
    skipEmptyLines?: boolean | "greedy";
    fastMode?: boolean;
    beforeFirstChunk?: (chunk: string) => string | void;
    withCredentials?: boolean;
    delimitersToGuess?: string[];
  }

  export function parse<T = any>(file: File | string, config?: ParseConfig<T>): ParseResult<T>;
  export function unparse(data: any[] | any, config?: any): string;

  const papa: {
    parse: typeof parse;
    unparse: typeof unparse;
  };

  export default papa;
}
