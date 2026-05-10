function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${name}. ` +
        `Set it in .env.local for local dev or in Vercel project settings.`,
    );
  }
  return value;
}

export const env = {
  get phorestUsername(): string {
    return required("PHOREST_USERNAME");
  },
  get phorestPassword(): string {
    return required("PHOREST_PASSWORD");
  },
  get phorestBusinessId(): string {
    return required("PHOREST_BUSINESS_ID");
  },
  get phorestBaseUrl(): string {
    return (
      process.env.PHOREST_BASE_URL ??
      "https://platform.phorest.com/third-party-api-server"
    );
  },
  get phorestBranchId(): string | undefined {
    return process.env.PHOREST_BRANCH_ID || undefined;
  },
  get appPassword(): string | undefined {
    return process.env.APP_PASSWORD || undefined;
  },
};
