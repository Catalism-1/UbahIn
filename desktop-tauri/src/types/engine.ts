export type EngineError = {
  code: string;
  message: string;
};

export type EngineHealth = {
  engine_version: string;
  python_available: boolean;
  pymupdf_available: boolean;
  pillow_available: boolean;
  pypdf_available: boolean;
  native_acceleration: string;
  platform: string;
};

export type EngineResponse<TData> = {
  id: string;
  ok: boolean;
  data?: TData;
  error?: EngineError;
};
