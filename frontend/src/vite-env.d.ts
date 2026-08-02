/// <reference types="vite/client" />

declare const process: {
	env: {
		VITE_API_BASE_URL?: string;
		VITE_API_TIMEOUT_MS?: string;
	};
};

interface ImportMetaEnv {
	readonly VITE_API_BASE_URL?: string;
	readonly VITE_API_TIMEOUT_MS?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
