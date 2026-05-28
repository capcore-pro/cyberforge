import type { ManagedProjectRecord } from "@shared/types";

export interface ApiResp<T> {
  ok: boolean;
  status: number;
  data?: T;
  error?: unknown;
}

async function api<T>(path: string, init?: RequestInit): Promise<ApiResp<T>> {
  try {
    const r = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    });
    const text = await r.text();
    let data: unknown = undefined;
    try {
      data = text ? JSON.parse(text) : undefined;
    } catch {
      data = text;
    }
    if (!r.ok) return { ok: false, status: r.status, error: data };
    return { ok: true, status: r.status, data: data as T };
  } catch (error) {
    return { ok: false, status: 0, error };
  }
}

export async function listEcommerce() {
  return api<ManagedProjectRecord[]>("/api/managed-projects/ecommerce");
}

export async function createEcommerce(prompt: string, slug?: string) {
  return api<{ project: ManagedProjectRecord } | any>("/api/managed-projects/ecommerce", {
    method: "POST",
    body: JSON.stringify({ prompt, slug }),
  });
}

export async function updateEcommerce(projectId: string, prompt: string) {
  return api<any>(`/api/managed-projects/ecommerce/${projectId}/update`, {
    method: "POST",
    body: JSON.stringify({ prompt }),
  });
}

export async function deleteEcommerce(projectId: string) {
  return api<any>(`/api/managed-projects/ecommerce/${projectId}/delete`, {
    method: "POST",
    body: JSON.stringify({ hard_delete: false }),
  });
}

export async function hardDeleteEcommerce(projectId: string) {
  return api<any>(`/api/managed-projects/ecommerce/${projectId}/delete`, {
    method: "POST",
    body: JSON.stringify({ hard_delete: true }),
  });
}

// Admin products (CyberForge only)
export async function adminListProducts(slug: string) {
  return api<any[]>(`/api/admin/ecommerce/${encodeURIComponent(slug)}/products`);
}

export async function adminCreateProduct(slug: string, product: any) {
  return api<any>(`/api/admin/ecommerce/${encodeURIComponent(slug)}/products`, {
    method: "POST",
    body: JSON.stringify(product),
  });
}

export async function adminPatchProduct(slug: string, productId: string, patch: any) {
  return api<any>(
    `/api/admin/ecommerce/${encodeURIComponent(slug)}/products/${encodeURIComponent(productId)}`,
    { method: "PATCH", body: JSON.stringify(patch) },
  );
}

export async function adminDeleteProduct(slug: string, productId: string) {
  return api<any>(
    `/api/admin/ecommerce/${encodeURIComponent(slug)}/products/${encodeURIComponent(productId)}`,
    { method: "DELETE" },
  );
}

