import { env } from "./env";

/**
 * Minimal Phorest third-party API client.
 *
 * Auth: HTTP Basic with the API username/password issued to the business.
 * Base: https://platform.phorest.com/third-party-api-server/api/business/{businessId}/
 * OpenAPI: https://platform.phorest.com/third-party-api-server/v3/api-docs
 */

function basicAuthHeader(username: string, password: string): string {
  const token = Buffer.from(`${username}:${password}`).toString("base64");
  return `Basic ${token}`;
}

export interface PhorestPage<T> {
  content: T[];
  totalElements?: number;
  totalPages?: number;
  number?: number;
  size?: number;
}

interface PhorestHalResponse<T> {
  _embedded?: Record<string, T[]>;
  page?: {
    size: number;
    totalElements: number;
    totalPages: number;
    number: number;
  };
}

export interface PhorestBranch {
  branchId: string;
  name: string;
}

export interface PhorestClient {
  clientId: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  mobile?: string;
  createdDate?: string;
}

export interface PhorestAppointment {
  appointmentId: string;
  startTime: string;
  endTime?: string;
  staffId?: string;
  staffName?: string;
  serviceId?: string;
  serviceName?: string;
  clientId?: string;
  clientName?: string;
  price?: number;
  state?: string;
}

export interface PhorestSale {
  saleId: string;
  date: string;
  total: number;
  staffId?: string;
  staffName?: string;
  clientId?: string;
  clientName?: string;
  paymentMethod?: string;
}

class PhorestClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: string,
  ) {
    super(message);
    this.name = "PhorestClientError";
  }
}

export class Phorest {
  private readonly baseUrl: string;
  private readonly authHeader: string;

  constructor(opts?: {
    username?: string;
    password?: string;
    businessId?: string;
    baseUrl?: string;
  }) {
    const username = opts?.username ?? env.phorestUsername;
    const password = opts?.password ?? env.phorestPassword;
    const businessId = opts?.businessId ?? env.phorestBusinessId;
    const baseUrl = (opts?.baseUrl ?? env.phorestBaseUrl).replace(/\/$/, "");
    this.baseUrl = `${baseUrl}/api/business/${encodeURIComponent(businessId)}`;
    this.authHeader = basicAuthHeader(username, password);
  }

  private async request<T>(
    path: string,
    init?: RequestInit,
  ): Promise<T> {
    const url = path.startsWith("http")
      ? path
      : `${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const res = await fetch(url, {
      ...init,
      headers: {
        Authorization: this.authHeader,
        Accept: "application/json",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      throw new PhorestClientError(
        `Phorest ${init?.method ?? "GET"} ${path} failed: ${res.status} ${res.statusText}`,
        res.status,
        body,
      );
    }
    return (await res.json()) as T;
  }

  private collectEmbedded<T>(json: PhorestHalResponse<T>): T[] {
    const embedded = json._embedded;
    if (!embedded) return [];
    const firstKey = Object.keys(embedded)[0];
    return firstKey ? (embedded[firstKey] ?? []) : [];
  }

  async listBranches(): Promise<PhorestBranch[]> {
    const json = await this.request<PhorestHalResponse<PhorestBranch>>(
      "/branch?size=100",
    );
    return this.collectEmbedded(json);
  }

  async listClients(params?: {
    page?: number;
    size?: number;
    branchId?: string;
  }): Promise<PhorestPage<PhorestClient>> {
    const qs = new URLSearchParams();
    qs.set("page", String(params?.page ?? 0));
    qs.set("size", String(params?.size ?? 50));
    if (params?.branchId) qs.set("branchId", params.branchId);
    const json = await this.request<PhorestHalResponse<PhorestClient>>(
      `/client?${qs.toString()}`,
    );
    return {
      content: this.collectEmbedded(json),
      totalElements: json.page?.totalElements,
      totalPages: json.page?.totalPages,
      number: json.page?.number,
      size: json.page?.size,
    };
  }

  async listAppointments(params: {
    branchId: string;
    from: string; // ISO date (YYYY-MM-DD)
    to: string; // ISO date (YYYY-MM-DD)
    page?: number;
    size?: number;
  }): Promise<PhorestPage<PhorestAppointment>> {
    const qs = new URLSearchParams();
    qs.set("branchId", params.branchId);
    qs.set("from_start_date", params.from);
    qs.set("to_start_date", params.to);
    qs.set("page", String(params.page ?? 0));
    qs.set("size", String(params.size ?? 100));
    const json = await this.request<PhorestHalResponse<PhorestAppointment>>(
      `/appointment?${qs.toString()}`,
    );
    return {
      content: this.collectEmbedded(json),
      totalElements: json.page?.totalElements,
      totalPages: json.page?.totalPages,
      number: json.page?.number,
      size: json.page?.size,
    };
  }

  async listSales(params: {
    branchId: string;
    from: string;
    to: string;
    page?: number;
    size?: number;
  }): Promise<PhorestPage<PhorestSale>> {
    const qs = new URLSearchParams();
    qs.set("branchId", params.branchId);
    qs.set("from_date", params.from);
    qs.set("to_date", params.to);
    qs.set("page", String(params.page ?? 0));
    qs.set("size", String(params.size ?? 100));
    const json = await this.request<PhorestHalResponse<PhorestSale>>(
      `/sale?${qs.toString()}`,
    );
    return {
      content: this.collectEmbedded(json),
      totalElements: json.page?.totalElements,
      totalPages: json.page?.totalPages,
      number: json.page?.number,
      size: json.page?.size,
    };
  }
}

export { PhorestClientError };
