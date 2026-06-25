import client from "./client";
import type { CreativeTemplate, TemplateListResponse, TemplateTag } from "@/types";

export interface TemplatePayload {
  prompt: string;
  model: string;
  reference_images: string[];
  num_images: number;
  size: string;
  resolution: string;
  custom_size: string;
  result_image: string;
  sort_order: number;
  tag_names: string[];
}

export interface TemplateTagPayload {
  name: string;
  parent_id?: number | null;
  sort_order?: number;
}

export interface TemplateListParams {
  page?: number;
  pageSize?: number;
  tagId?: number;
  parentId?: number;
}

export function listTemplates(params: TemplateListParams = {}): Promise<TemplateListResponse> {
  const { page = 1, pageSize = 20, tagId, parentId } = params;
  const query: Record<string, unknown> = {
    page,
    page_size: pageSize,
  };
  if (tagId) query.tag_id = tagId;
  if (parentId) query.parent_id = parentId;
  return client.get("/templates", { params: query });
}

export function listTemplateTags(): Promise<TemplateTag[]> {
  return client.get("/templates/tags");
}

export function createTemplateTag(data: TemplateTagPayload): Promise<TemplateTag> {
  return client.post("/templates/tags", data);
}

export function updateTemplateTag(tagId: number, data: TemplateTagPayload): Promise<TemplateTag> {
  return client.put(`/templates/tags/${tagId}`, data);
}

export function deleteTemplateTag(tagId: number): Promise<void> {
  return client.delete(`/templates/tags/${tagId}`);
}

export function getTemplateDetail(templateId: number): Promise<CreativeTemplate> {
  return client.get(`/templates/${templateId}`);
}

export function listAdminTemplates(): Promise<CreativeTemplate[]> {
  return client.get("/templates/admin/list");
}

export function createTemplate(data: TemplatePayload): Promise<CreativeTemplate> {
  return client.post("/templates", data);
}

export function updateTemplate(templateId: number, data: TemplatePayload): Promise<CreativeTemplate> {
  return client.put(`/templates/${templateId}`, data);
}

export function deleteTemplate(templateId: number): Promise<void> {
  return client.delete(`/templates/${templateId}`);
}
