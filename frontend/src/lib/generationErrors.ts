import type { ImageResult } from "@/types";

export const IMAGE_SAFETY_ERROR_MESSAGE = "生成的图片存在安全风险，请尝试修改提示词或参考图！";
export const GENERATION_TASK_FAILURE_MESSAGE = "生图失败，请反馈给我们处理";
export const CREDIT_REFUNDED_SUFFIX = "（积分已返还）";

const IMAGE_SAFETY_ERROR_PATTERN = /image_unsafe|content blocked/i;

export function isImageSafetyError(rawMessage?: string) {
  return IMAGE_SAFETY_ERROR_PATTERN.test(String(rawMessage || "").trim());
}

export function formatGenerationErrorMessage(rawMessage?: string, fallback = "生成失败，请重试") {
  const detail = String(rawMessage || "").trim();
  if (!detail) return fallback;
  if (isImageSafetyError(detail)) {
    return IMAGE_SAFETY_ERROR_MESSAGE;
  }
  return detail;
}

function withCreditRefundedSuffix(message: string) {
  return message.endsWith(CREDIT_REFUNDED_SUFFIX) ? message : `${message}${CREDIT_REFUNDED_SUFFIX}`;
}

export function formatGenerationTaskFailureMessage(rawMessage?: string) {
  const detail = String(rawMessage || "").trim();
  const message = isImageSafetyError(detail) ? IMAGE_SAFETY_ERROR_MESSAGE : GENERATION_TASK_FAILURE_MESSAGE;
  return withCreditRefundedSuffix(message);
}

export function getPreferredGenerationErrorMessage(
  taskError?: string,
  imageError?: string,
  _fallback = "生成失败，请重试"
) {
  return formatGenerationTaskFailureMessage(imageError || taskError);
}

export function getTaskImageFailureMessage(
  task: { error_message?: string } | null | undefined,
  image: Pick<ImageResult, "error_message"> | null | undefined,
  fallback = "生成失败，请重试"
) {
  return getPreferredGenerationErrorMessage(task?.error_message, image?.error_message, fallback);
}
